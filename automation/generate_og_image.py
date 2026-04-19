"""
OGP画像生成スクリプト
og_template.html を Playwright でスクリーンショットして
assets/og-image.png (1200x630) を出力する
"""

from pathlib import Path
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).parent.parent
TEMPLATE = REPO_ROOT / "automation" / "og_template.html"
OUTPUT   = REPO_ROOT / "assets" / "og-image.png"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 630})
        page.goto(f"file:///{TEMPLATE.as_posix()}", wait_until="networkidle")
        page.wait_for_timeout(500)
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(OUTPUT), clip={"x": 0, "y": 0, "width": 1200, "height": 630})
        browser.close()
    print(f"OGP画像を生成しました: {OUTPUT}")


if __name__ == "__main__":
    main()
