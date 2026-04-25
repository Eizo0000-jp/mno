"""
note.com 自動投稿スクリプト
セッションクッキーでnote.comに認証し、Claude APIで生成した記事を投稿する

必要な環境変数:
  NOTE_SESSION_V5    - _note_session_v5 クッキーの値
  NOTE_GQL_AUTH_TOKEN - note_gql_auth_token クッキーの値
  ANTHROPIC_API_KEY  - Claude API Key
"""

import os
import re
import sys
import random
import tempfile
from pathlib import Path
import anthropic
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

LP_URL = "https://mobile-friend.com"

NOTE_TOPICS = [
    "楽天モバイルに乗り換えたら月々の支出が変わった話",
    "社員紹介キャンペーンで14,000ポイントもらえた件",
    "スマホ代を見直したらこうなった",
    "楽天モバイルの社員がおすすめする理由を正直に話す",
    "MNPで乗り換えた手順を全部まとめてみた",
    "楽天経済圏とスマホ代の節約を同時にやってみた",
    "家族全員で乗り換えたら年間いくら変わったか",
    "社員紹介と通常申込みの違いを比べてみた",
]


NOTE_COVER_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    width: 1280px;
    height: 670px;
    background: linear-gradient(135deg, #7f0019 0%, #b30024 60%, #f4eede 100%);
    font-family: "Noto Sans JP", "Hiragino Kaku Gothic ProN", "Meiryo", sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: flex-start;
    padding: 72px 96px;
    overflow: hidden;
  }}
  .tag {{
    font-size: 14px;
    font-weight: 700;
    color: #f4eede;
    letter-spacing: 3px;
    border: 2px solid #f4eede;
    padding: 6px 18px;
    margin-bottom: 36px;
    opacity: 0.9;
  }}
  .title {{
    font-size: {font_size}px;
    font-weight: 700;
    color: #ffffff;
    line-height: 1.6;
    max-width: 900px;
    text-shadow: 0 2px 8px rgba(0,0,0,0.25);
  }}
  .footer {{
    position: absolute;
    bottom: 52px;
    right: 96px;
    font-size: 16px;
    font-weight: 700;
    color: rgba(255,255,255,0.75);
    letter-spacing: 1px;
  }}
</style>
</head>
<body>
  <div class="tag">楽天モバイル 社員紹介</div>
  <div class="title">{title}</div>
  <div class="footer">mobile-friend.com</div>
</body>
</html>"""


def get_font_size(title: str) -> int:
    length = len(title)
    if length <= 20:
        return 54
    elif length <= 30:
        return 46
    elif length <= 40:
        return 38
    else:
        return 32


def generate_cover_image(title: str) -> Path:
    """note.com用カバー画像を一時ファイルとして生成し、そのパスを返す"""
    font_size = get_font_size(title)
    html = NOTE_COVER_TEMPLATE.format(title=title, font_size=font_size)

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 670})
        page = context.new_page()
        page.set_content(html)
        page.wait_for_timeout(300)
        page.screenshot(
            path=str(tmp_path),
            clip={"x": 0, "y": 0, "width": 1280, "height": 670}
        )
        browser.close()

    print(f"カバー画像生成完了: {tmp_path}")
    return tmp_path


def generate_article() -> tuple[str, str]:
    """Claude APIでnote風の体験談記事を生成"""
    client = anthropic.Anthropic()
    topic = random.choice(NOTE_TOPICS)

    prompt = f"""note.comに投稿する体験談ブログ記事を書いてください。

テーマ: {topic}
紹介LP URL: {LP_URL}

前提知識:
- 楽天モバイルの社員紹介キャンペーンはMNP（乗り換え）で最大14,000ポイント
- 新規申込みは11,000ポイント
- 通常キャンペーンより多くもらえる（通常は13,000ポイント）
- ポイントは紹介ログイン月の4ヶ月後から3ヶ月間に分割進呈
- 条件にRakuten Linkで10秒以上の通話が必要

要件:
- 一人称・体験談スタイル（「私は〜」「〜でした」）
- 文字数: 700〜1000字
- 読者に役立つ具体的な情報を含める
- 見出し(##)を3〜4個使って構造化する
- 最後のセクションで{LP_URL} へ自然に誘導する（広告感を出さない）
- 最初の行を「title: タイトル」の形式にする

出力は記事本文のみ（説明文不要）。"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    content = message.content[0].text.strip()
    title_match = re.match(r"title:\s*(.+)", content)
    title = title_match.group(1).strip() if title_match else topic
    body = re.sub(r"^title:.+\n+", "", content).strip()

    return title, body


def post_to_note(title: str, body: str, cover_image_path: Path = None) -> None:
    """クッキー認証でnote.comに記事を投稿"""
    session_v5 = os.environ["NOTE_SESSION_V5"]
    gql_auth_token = os.environ["NOTE_GQL_AUTH_TOKEN"]

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="ja-JP",
        )

        # クッキーをセットしてログインをスキップ
        context.add_cookies([
            {"name": "_note_session_v5",   "value": session_v5,      "domain": ".note.com", "path": "/"},
            {"name": "note_gql_auth_token", "value": gql_auth_token,  "domain": ".note.com", "path": "/"},
        ])

        page = context.new_page()

        try:
            os.makedirs("debug_screenshots", exist_ok=True)

            # ログイン確認
            print("認証状態を確認中...")
            page.goto("https://note.com/", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            page.screenshot(path="debug_screenshots/01_top.png", full_page=False)
            print(f"URL: {page.url}")

            # ログインできているか確認（ログインボタンがなければOK）
            if page.locator('a:has-text("ログイン")').count() > 0:
                raise RuntimeError("クッキー認証失敗。セッションが期限切れの可能性があります。")
            print("認証OK")

            # 新規記事作成画面へ
            print("記事作成画面へ移動中...")
            page.goto("https://note.com/notes/new", wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            page.screenshot(path="debug_screenshots/02_new_article.png", full_page=False)
            print(f"URL: {page.url}")

            # カバー画像アップロード
            if cover_image_path and cover_image_path.exists():
                print("カバー画像をアップロード中...")
                page.screenshot(path="debug_screenshots/02a_before_cover.png", full_page=True)

                cover_uploaded = False

                # 方法1: file_chooser イベント経由（クリックでダイアログを開く）
                cover_btn_selectors = [
                    'button[aria-label*="カバー"]',
                    'button[aria-label*="cover"]',
                    '[data-testid*="cover"]',
                    'label[for*="cover"]',
                    'label[for*="image"]',
                    'button:has-text("カバー")',
                    'button:has-text("画像を追加")',
                    '[class*="cover"] button',
                    '[class*="Cover"] button',
                    '[class*="eyecatch"] button',
                    '[class*="thumbnail"] button',
                ]
                for sel in cover_btn_selectors:
                    try:
                        loc = page.locator(sel)
                        if loc.count() > 0 and loc.first.is_visible():
                            print(f"カバーボタン発見: {sel}")
                            with page.expect_file_chooser(timeout=6000) as fc_info:
                                loc.first.click()
                            fc_info.value.set_files(str(cover_image_path))
                            page.wait_for_timeout(4000)
                            cover_uploaded = True
                            print("カバー画像アップロード完了（ダイアログ経由）")
                            break
                    except Exception as e:
                        print(f"  {sel} 失敗: {e}")
                        continue

                # 方法2: file input を直接操作
                if not cover_uploaded:
                    print("方法2: file input 直接操作を試みます")
                    file_inputs = page.locator('input[type="file"]')
                    count = file_inputs.count()
                    print(f"  file input 数: {count}")
                    for i in range(count):
                        try:
                            fi = file_inputs.nth(i)
                            # hidden でも強制的にセット
                            fi.evaluate("el => el.removeAttribute('style')")
                            fi.set_input_files(str(cover_image_path))
                            page.wait_for_timeout(4000)
                            cover_uploaded = True
                            print(f"カバー画像アップロード完了（input[{i}] 直接）")
                            break
                        except Exception as e:
                            print(f"  input[{i}] 失敗: {e}")
                            continue

                if not cover_uploaded:
                    # ページ内のボタン・ラベル一覧をデバッグ出力
                    print("警告: カバー画像アップロード失敗。ページ内の要素を出力します:")
                    for el in page.locator("button").all()[:15]:
                        try:
                            print(f"  button: '{el.inner_text().strip()}' aria={el.get_attribute('aria-label')}")
                        except Exception:
                            pass
                    for el in page.locator("label").all()[:10]:
                        try:
                            print(f"  label: for='{el.get_attribute('for')}' text='{el.inner_text().strip()[:30]}'")
                        except Exception:
                            pass

                page.screenshot(path="debug_screenshots/02b_cover_uploaded.png", full_page=True)

            # タイトル入力
            title_selectors = [
                'div[data-placeholder="記事タイトル"]',
                '[placeholder*="タイトル"]',
                'textarea[placeholder*="タイトル"]',
            ]
            for sel in title_selectors:
                if page.locator(sel).count() > 0:
                    page.click(sel)
                    page.keyboard.type(title)
                    print(f"タイトル入力完了")
                    break

            # 本文入力
            page.keyboard.press("Tab")
            page.wait_for_timeout(1000)
            page.keyboard.type(body)
            print("本文入力完了")

            page.screenshot(path="debug_screenshots/03_article_filled.png", full_page=False)

            # 公開ボタン（ヘッダー右上）
            page.wait_for_timeout(2000)
            for sel in ['button:has-text("公開")', 'button:has-text("投稿")']:
                if page.locator(sel).count() > 0:
                    page.click(sel)
                    print(f"公開ボタンクリック（{sel}）")
                    break

            # ダイアログが開くのを待つ
            page.wait_for_timeout(4000)
            page.screenshot(path="debug_screenshots/04_publish_dialog.png", full_page=False)

            # ダイアログ内のボタンを全列挙してデバッグ
            buttons = page.locator("button").all()
            print(f"ボタン数: {len(buttons)}")
            for i, btn in enumerate(buttons):
                try:
                    print(f"  button[{i}]: '{btn.inner_text().strip()}'")
                except Exception:
                    pass

            # 公開確認ボタン（複数パターン試行）
            confirm_selectors = [
                'button:has-text("投稿する")',
                'button:has-text("公開する")',
                'button:has-text("無料公開")',
                'button:has-text("公開")',
            ]
            confirmed = False
            for sel in confirm_selectors:
                locator = page.locator(sel)
                if locator.count() > 0:
                    # 最後に表示されているボタンをクリック（ダイアログ内のものを優先）
                    locator.last.click()
                    print(f"公開確認クリック（{sel}）")
                    confirmed = True
                    break

            if not confirmed:
                print("警告: 公開確認ボタンが見つかりませんでした")

            page.wait_for_timeout(5000)
            page.screenshot(path="debug_screenshots/05_after_publish.png", full_page=False)
            print(f"最終URL: {page.url}")
            print(f"投稿完了: {title}")

        except PlaywrightTimeoutError as e:
            print(f"タイムアウトエラー: {e}")
            raise
        finally:
            browser.close()


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    print("記事を生成中...")
    title, body = generate_article()

    print(f"\n=== 生成された記事 ===")
    print(f"タイトル: {title}")
    print(f"本文（冒頭）:\n{body[:200]}...")
    print("=" * 24)

    if dry_run:
        print("\n[DRY RUN] 投稿はスキップしました")
        return

    print("カバー画像を生成中...")
    cover_path = generate_cover_image(title)
    try:
        post_to_note(title, body, cover_path)
    finally:
        cover_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
