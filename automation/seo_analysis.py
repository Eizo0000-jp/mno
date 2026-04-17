"""
SEO分析・自動改善スクリプト
GA4とSearch Consoleからデータを取得し、Claude APIで分析して
ブログ記事のトピックを最適化する

必要な環境変数:
  GCP_SERVICE_ACCOUNT_JSON - サービスアカウントのJSONキー（文字列）
  GA4_PROPERTY_ID          - GA4プロパティID（数字のみ）
  ANTHROPIC_API_KEY        - Claude API Key
"""

import os
import json
import anthropic
from datetime import date, timedelta
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, Dimension, Metric, DateRange
)

REPO_ROOT = Path(__file__).parent.parent
SITE_URL = "https://mobile-friend.com/"
REFERRAL_URL = "https://r10.to/henTIE"


def get_credentials():
    """サービスアカウント認証情報を取得"""
    key_json = os.environ["GCP_SERVICE_ACCOUNT_JSON"]
    key_data = json.loads(key_json)
    scopes = [
        "https://www.googleapis.com/auth/analytics.readonly",
        "https://www.googleapis.com/auth/webmasters.readonly",
    ]
    return service_account.Credentials.from_service_account_info(key_data, scopes=scopes)


def get_ga4_data(credentials) -> dict:
    """GA4からアクセスデータを取得"""
    property_id = os.environ["GA4_PROPERTY_ID"]
    client = BetaAnalyticsDataClient(credentials=credentials)

    end_date = date.today()
    start_date = end_date - timedelta(days=28)

    # ページ別セッション数
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="pagePath")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
        ],
        date_ranges=[DateRange(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )],
        limit=20,
    )
    response = client.run_report(request)

    pages = []
    for row in response.rows:
        pages.append({
            "path": row.dimension_values[0].value,
            "sessions": int(row.metric_values[0].value),
            "bounce_rate": round(float(row.metric_values[1].value) * 100, 1),
            "avg_duration": round(float(row.metric_values[2].value)),
        })

    # 流入元
    source_request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions")],
        date_ranges=[DateRange(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )],
        limit=10,
    )
    source_response = client.run_report(source_request)
    sources = [
        {
            "channel": r.dimension_values[0].value,
            "sessions": int(r.metric_values[0].value)
        }
        for r in source_response.rows
    ]

    return {"pages": pages, "sources": sources, "period": f"{start_date} 〜 {end_date}"}


def get_search_console_data(credentials) -> dict:
    """Search Consoleから検索クエリデータを取得"""
    service = build("searchconsole", "v1", credentials=credentials)

    end_date = date.today() - timedelta(days=3)  # Search Consoleは3日遅延
    start_date = end_date - timedelta(days=28)

    # アクセス可能なサイト一覧から対象URLを特定
    sites_response = service.sites().list().execute()
    available_sites = [s["siteUrl"] for s in sites_response.get("siteEntry", [])]
    print(f"  利用可能なSearch Consoleプロパティ: {available_sites}")

    # SITE_URL に一致するものを探す（末尾スラッシュ有無・sc-domain形式も考慮）
    domain = "mobile-friend.com"
    candidates = [
        SITE_URL,
        SITE_URL.rstrip("/"),
        f"sc-domain:{domain}",
        f"http://{domain}/",
        f"http://{domain}",
    ]
    site_url = None
    for candidate in candidates:
        if candidate in available_sites:
            site_url = candidate
            break
    if site_url is None:
        # フォールバック: 利用可能な最初のサイト
        if available_sites:
            site_url = available_sites[0]
            print(f"  警告: {SITE_URL} が見つからないため {site_url} を使用します")
        else:
            raise RuntimeError("Search Consoleにアクセス可能なプロパティがありません。サービスアカウントの権限を確認してください。")

    print(f"  使用するプロパティ: {site_url}")

    response = service.searchanalytics().query(
        siteUrl=site_url,
        body={
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "dimensions": ["query"],
            "rowLimit": 30,
        }
    ).execute()

    queries = []
    for row in response.get("rows", []):
        queries.append({
            "query": row["keys"][0],
            "clicks": row.get("clicks", 0),
            "impressions": row.get("impressions", 0),
            "ctr": round(row.get("ctr", 0) * 100, 1),
            "position": round(row.get("position", 0), 1),
        })

    return {"queries": queries, "period": f"{start_date} 〜 {end_date}"}


def analyze_and_generate_topics(ga4_data: dict, sc_data: dict) -> str:
    """Claude APIでデータを分析し改善提案とトピックを生成"""
    client = anthropic.Anthropic()

    prompt = f"""楽天モバイル社員紹介キャンペーンサイト（mobile-friend.com）のSEOデータを分析し、
改善提案と次に書くべきブログ記事テーマを提案してください。

## GA4データ（過去28日）
期間: {ga4_data['period']}

### ページ別セッション数（上位）
{json.dumps(ga4_data['pages'][:10], ensure_ascii=False, indent=2)}

### 流入チャネル
{json.dumps(ga4_data['sources'], ensure_ascii=False, indent=2)}

## Search Consoleデータ（過去28日）
期間: {sc_data['period']}

### 検索クエリ（上位）
{json.dumps(sc_data['queries'][:20], ensure_ascii=False, indent=2)}

## 分析・提案の形式
以下の形式でMarkdownで出力してください：

### 📊 現状サマリー
- 主要な数値の読み取り

### 🔍 SEO改善ポイント
- 具体的な改善提案（3〜5点）

### 📝 次に書くべき記事テーマ（5本）
以下の形式で5本提案：
1. キーワード: 「...」/ タイトル案: 「...」/ 理由: ...
2. ...

### ⚠️ 注意点
- データから読み取れる課題
"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text.strip()


def save_report(report: str) -> Path:
    """分析レポートをファイルに保存"""
    reports_dir = REPO_ROOT / "seo_reports"
    reports_dir.mkdir(exist_ok=True)

    today = date.today().isoformat()
    filepath = reports_dir / f"{today}-seo-report.md"

    content = f"# SEO分析レポート {today}\n\n{report}\n"
    filepath.write_text(content, encoding="utf-8")
    print(f"レポート保存: {filepath.name}")
    return filepath


def update_topics(report: str) -> None:
    """分析結果を元にgenerate_article.pyのTOPICSを更新"""
    # レポートから提案テーマを抽出してログ出力（手動確認用）
    print("\n=== 提案された記事テーマ ===")
    lines = report.split("\n")
    in_topics = False
    for line in lines:
        if "次に書くべき記事テーマ" in line:
            in_topics = True
        elif in_topics and line.startswith("###"):
            break
        elif in_topics and line.strip():
            print(line)


def main() -> None:
    print("認証情報を取得中...")
    credentials = get_credentials()

    print("GA4データを取得中...")
    ga4_data = get_ga4_data(credentials)
    print(f"  ページデータ: {len(ga4_data['pages'])}件")

    print("Search Consoleデータを取得中...")
    sc_data = get_search_console_data(credentials)
    print(f"  クエリデータ: {len(sc_data['queries'])}件")

    print("Claude APIで分析中...")
    report = analyze_and_generate_topics(ga4_data, sc_data)

    filepath = save_report(report)
    update_topics(report)

    print("\n=== 分析レポート ===")
    print(report)


if __name__ == "__main__":
    main()
