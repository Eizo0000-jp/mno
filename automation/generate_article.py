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
    ("楽天モバイル 乗り換え メリット デメリット 徹底解説", "rakuten-mobile-merits-demerits"),
    ("スマホ代 月3000円台 節約 実現する方法", "smartphone-cost-3000yen"),
    ("楽天モバイル ドコモ au ソフトバンク 料金 比較", "rakuten-vs-major-carriers"),
    ("楽天ポイント スマホ代 二重取り 方法", "rakuten-point-double"),
    ("楽天モバイル 海外ローミング 設定 使い方", "rakuten-overseas-roaming"),
    ("楽天モバイル テザリング 速度 使い方", "rakuten-tethering-guide"),
    ("楽天モバイル 家族 全員 乗り換え 節約額", "rakuten-family-switch"),
    ("楽天モバイル 繋がらない 対策 エリア確認", "rakuten-connection-tips"),
    ("楽天モバイル MNP 乗り換え 手順 わかりやすく", "rakuten-mnp-step-by-step"),
    ("楽天経済圏 最大化 スマホ 活用術", "rakuten-ecosystem-maximize"),
    ("格安SIM 楽天モバイル 比較 どっちがお得", "rakuten-vs-mvno"),
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

要件:
- 最初の行を「title: 記事タイトル」の形式にする
- ## と ### の見出しで構造化する
- 文字数: 1200〜1800字
- 読者が実際に得をする具体的な情報・数字を入れる
- 自然な文章で、押しつけがましくない
- 記事の最後のセクションで、自然な流れで紹介リンクに誘導する
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
