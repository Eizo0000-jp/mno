"""
記事別OGP画像生成スクリプト

_posts/ の日本語記事（langプレフィックスなし）を走査し、
assets/ogp/{date}-{slug}.png が存在しなければ Playwright でスクリーンショットを生成する。
全言語版は同じ画像を共有するため、日本語版のタイトルと slug のみ使用する。
"""

import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).parent.parent
POSTS_DIR = REPO_ROOT / "_posts"
OGP_DIR = REPO_ROOT / "assets" / "ogp"

OGP_W = 1200
OGP_H = 630

OGP_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    width: {w}px;
    height: {h}px;
    background: #f4eede;
    font-family: "Noto Sans JP", "Hiragino Kaku Gothic ProN", "Meiryo", sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 56px 72px;
    overflow: hidden;
  }}
  .tag {{
    display: inline-block;
    font-size: 13px;
    font-weight: 700;
    color: #7f0019;
    letter-spacing: 3px;
    border: 2px solid #7f0019;
    padding: 6px 16px;
    width: fit-content;
  }}
  .title {{
    font-size: {font_size}px;
    font-weight: 700;
    color: #3c3c43;
    line-height: 1.55;
    margin: 32px 0;
    max-height: 320px;
    overflow: hidden;
  }}
  .footer {{
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    border-top: 2px solid #e0ceaa;
    padding-top: 20px;
  }}
  .site-name {{
    font-size: 15px;
    font-weight: 700;
    color: #6d6d72;
  }}
  .points {{
    font-size: 22px;
    font-weight: 700;
    color: #7f0019;
  }}
</style>
</head>
<body>
  <div>
    <div class="tag">楽天モバイル社員紹介</div>
    <div class="title">{title}</div>
  </div>
  <div class="footer">
    <span class="site-name">mobile-friend.com</span>
    <span class="points">社員紹介で最大14,000pt</span>
  </div>
</body>
</html>"""


def get_font_size(title: str) -> int:
    """タイトル長に応じてフォントサイズを調整"""
    length = len(title)
    if length <= 20:
        return 52
    elif length <= 35:
        return 44
    elif length <= 50:
        return 36
    else:
        return 30


def collect_ja_posts() -> list[dict]:
    """日本語版記事（langプレフィックスなし）を収集"""
    if not POSTS_DIR.exists():
        return []
    results = []
    for p in sorted(POSTS_DIR.glob("*.md")):
        stem = p.stem
        slug_part = stem.split("-", 3)[-1]
        if re.match(r"^(en|ko|zh-cn|zh-tw|tl|vi)-", slug_part):
            continue
        text = p.read_text(encoding="utf-8")
        title_match = re.search(r'^title:\s*"?(.+?)"?\s*$', text, re.MULTILINE)
        title = title_match.group(1) if title_match else slug_part
        date_prefix = stem[:10]
        img_name = f"{date_prefix}-{slug_part}.png"
        results.append({"title": title, "img_name": img_name, "stem": stem})
    return results


def generate_image(page, title: str, out_path: Path) -> None:
    font_size = get_font_size(title)
    html = OGP_HTML_TEMPLATE.format(
        w=OGP_W, h=OGP_H,
        title=title,
        font_size=font_size,
    )
    page.set_content(html)
    # Google Fontsが使えない環境でもシステムフォントにフォールバック
    page.wait_for_timeout(300)
    page.screenshot(path=str(out_path), clip={"x": 0, "y": 0, "width": OGP_W, "height": OGP_H})
    print(f"  生成: {out_path.name}")


def main() -> None:
    OGP_DIR.mkdir(parents=True, exist_ok=True)
    posts = collect_ja_posts()

    if not posts:
        print("記事が見つかりません")
        return

    # 未生成の画像のみ対象
    to_generate = [p for p in posts if not (OGP_DIR / p["img_name"]).exists()]
    if not to_generate:
        print(f"OGP画像はすべて生成済みです（{len(posts)}件）")
        return

    print(f"OGP画像を生成します: {len(to_generate)}件")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={"width": OGP_W, "height": OGP_H})
        page = context.new_page()
        for post in to_generate:
            out_path = OGP_DIR / post["img_name"]
            generate_image(page, post["title"], out_path)
        browser.close()
    print(f"\n完了: {len(to_generate)}件のOGP画像を生成しました")


if __name__ == "__main__":
    main()
