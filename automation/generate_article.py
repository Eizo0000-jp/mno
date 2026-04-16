"""
SEOブログ記事 自動生成スクリプト
Claude APIで楽天モバイル関連記事を生成し _posts/ に保存する
"""

import re
import random
from datetime import date
from pathlib import Path
import anthropic

REFERRAL_URL = "https://r10.to/henTIE"
REPO_ROOT = Path(__file__).parent.parent

TOPICS = [
    ("楽天モバイル 社員紹介キャンペーン 14000ポイント もらい方", "employee-referral-14000pt"),
    ("楽天モバイル 社員紹介 通常申込み 違い ポイント比較", "referral-vs-normal-points"),
    ("楽天モバイル 紹介リンク 申込み 手順 わかりやすく", "referral-link-how-to"),
    ("楽天ポイント 14000 使い道 お得な活用法", "rakuten-point-14000-usage"),
    ("楽天モバイル 社員紹介 よくある質問 まとめ", "employee-referral-faq"),
    ("楽天モバイル 乗り換え 社員紹介 タイミング いつがお得", "referral-best-timing"),
    ("楽天ポイント スマホ代 節約 二重取り 方法", "rakuten-point-double"),
    ("楽天モバイル ドコモ au ソフトバンク 料金 比較", "rakuten-vs-major-carriers"),
    ("楽天モバイル MNP 乗り換え 手順 わかりやすく", "rakuten-mnp-step-by-step"),
    ("楽天経済圏 最大化 スマホ 活用術", "rakuten-ecosystem-maximize"),
    ("楽天モバイル 家族 全員 乗り換え 節約額", "rakuten-family-switch"),
    ("楽天モバイル 口コミ 評判 実際に使ってみた", "rakuten-review-honest"),
]


def pick_unused_topic() -> tuple[str, str]:
    """まだ記事化していないトピックを選ぶ"""
    posts_dir = REPO_ROOT / "_posts"
    existing_slugs = {p.stem.split("-", 3)[-1] for p in posts_dir.glob("*.md")} if posts_dir.exists() else set()

    unused = [(kw, slug) for kw, slug in TOPICS if slug not in existing_slugs]
    if not unused:
        # 全部使い切ったらランダムに再利用
        unused = TOPICS

    return random.choice(unused)


def generate_article(keyword: str) -> tuple[str, str]:
    """Claude APIで記事を生成しタイトルと本文を返す"""
    client = anthropic.Anthropic()

    prompt = f"""SEOに最適化された日本語ブログ記事をMarkdown形式で作成してください。

メインキーワード: {keyword}
楽天モバイル社員紹介URL: {REFERRAL_URL}

前提知識:
- 楽天モバイルには社員紹介キャンペーンがある
- 社員紹介リンク経由で申し込むと、通常申込みより多くのポイントが付与される
- 最大で合計14,000ポイント獲得できる（社員紹介特典＋新規申込み特典＋その他）
- 料金は通常と同じ月3,278円（税込）、データ無制限

要件:
- 最初の行を「title: 記事タイトル」の形式にする
- ## と ### の見出しで構造化する
- 文字数: 1200〜1800字
- 「社員紹介経由だとポイントが多い」という価値を具体的な数字で伝える
- 自然な文章で、押しつけがましくない
- 記事の最後のセクションで紹介リンクへ自然に誘導する
- ハッシュタグや広告表記は不要

出力は記事本文のみ（説明文不要）。"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}]
    )

    content = message.content[0].text.strip()

    title_match = re.match(r"title:\s*(.+)", content)
    title = title_match.group(1).strip() if title_match else keyword
    body = re.sub(r"^title:.+\n+", "", content).strip()

    return title, body


def save_post(title: str, body: str, slug: str) -> Path:
    today = date.today()
    filename = f"{today.strftime('%Y-%m-%d')}-{slug}.md"
    posts_dir = REPO_ROOT / "_posts"
    posts_dir.mkdir(exist_ok=True)
    filepath = posts_dir / filename

    front_matter = (
        "---\n"
        f'title: "{title}"\n'
        f"date: {today.isoformat()}\n"
        f'description: "{title} について楽天社員が詳しく解説します。"\n'
        "---\n\n"
    )

    filepath.write_text(front_matter + body, encoding="utf-8")
    print(f"保存完了: {filepath.name}")
    return filepath


def main() -> None:
    keyword, slug = pick_unused_topic()
    print(f"テーマ: {keyword}")

    title, body = generate_article(keyword)
    print(f"タイトル: {title}")

    save_post(title, body, slug)


if __name__ == "__main__":
    main()
