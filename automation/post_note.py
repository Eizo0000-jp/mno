"""
note.com 自動投稿スクリプト
Playwrightでnote.comにログインし、Claude APIで生成した記事を投稿する

必要な環境変数:
  NOTE_EMAIL        - note.comのメールアドレス
  NOTE_PASSWORD     - note.comのパスワード
  ANTHROPIC_API_KEY - Claude API Key
"""

import os
import re
import sys
import random
import anthropic
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import stealth_sync

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


def post_to_note(title: str, body: str) -> None:
    """Playwrightでnote.comに記事を投稿"""
    email = os.environ["NOTE_EMAIL"]
    password = os.environ["NOTE_PASSWORD"]

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="ja-JP",
        )
        page = context.new_page()
        stealth_sync(page)  # bot検知を回避

        try:
            os.makedirs("debug_screenshots", exist_ok=True)

            # ログイン
            print("ログイン中...")
            page.goto("https://note.com/login", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            page.screenshot(path="debug_screenshots/01_login_page.png", full_page=True)
            print(f"現在URL: {page.url}")
            print(f"ページタイトル: {page.title()}")

            # 全inputを列挙してデバッグ
            inputs = page.locator("input").all()
            print(f"inputの数: {len(inputs)}")
            for i, inp in enumerate(inputs):
                try:
                    print(f"  input[{i}]: type={inp.get_attribute('type')} name={inp.get_attribute('name')} placeholder={inp.get_attribute('placeholder')}")
                except Exception:
                    pass

            # メールアドレス入力
            email_selectors = [
                'input[type="email"]',
                'input[name="email"]',
                'input[placeholder*="メール"]',
                'input[placeholder*="mail"]',
                'input[placeholder*="Mail"]',
            ]
            email_filled = False
            for sel in email_selectors:
                if page.locator(sel).count() > 0:
                    page.fill(sel, email)
                    print(f"メール入力完了（セレクター: {sel}）")
                    email_filled = True
                    break
            if not email_filled:
                print("警告: メール入力欄が見つかりませんでした")

            # パスワード入力
            password_selectors = [
                'input[type="password"]',
                'input[name="password"]',
            ]
            password_filled = False
            for sel in password_selectors:
                if page.locator(sel).count() > 0:
                    page.fill(sel, password)
                    print("パスワード入力完了")
                    password_filled = True
                    break
            if not password_filled:
                print("警告: パスワード入力欄が見つかりませんでした")

            page.screenshot(path="debug_screenshots/02_login_filled.png", full_page=True)

            # ログインボタンをクリック
            login_selectors = [
                'button[type="submit"]',
                'button:has-text("ログイン")',
                'input[type="submit"]',
            ]
            for sel in login_selectors:
                if page.locator(sel).count() > 0:
                    page.click(sel)
                    print(f"ログインボタンクリック（セレクター: {sel}）")
                    break

            page.wait_for_timeout(5000)
            page.screenshot(path="debug_screenshots/03_after_login.png", full_page=True)
            print(f"ログイン後URL: {page.url}")
            print(f"ログイン後タイトル: {page.title()}")

            # 新規記事作成画面へ
            print("記事作成画面へ移動中...")
            page.goto("https://note.com/notes/new", wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            page.screenshot(path="debug_screenshots/04_new_article.png", full_page=True)
            print(f"記事作成URL: {page.url}")

            # タイトル入力
            title_selectors = [
                'div[data-placeholder="記事タイトル"]',
                'textarea[placeholder*="タイトル"]',
                '.title-input',
                'div.title',
                '[placeholder*="タイトル"]',
            ]
            title_filled = False
            for sel in title_selectors:
                if page.locator(sel).count() > 0:
                    page.click(sel)
                    page.keyboard.type(title)
                    print(f"タイトル入力完了（セレクター: {sel}）")
                    title_filled = True
                    break
            if not title_filled:
                print("警告: タイトル入力欄が見つかりませんでした")

            # 本文入力
            page.keyboard.press("Tab")
            page.wait_for_timeout(1000)
            page.keyboard.type(body)
            print("本文入力完了")

            page.screenshot(path="debug_screenshots/05_article_filled.png", full_page=True)

            # 公開ボタンをクリック
            page.wait_for_timeout(2000)
            publish_selectors = [
                'button:has-text("公開")',
                'button:has-text("投稿")',
            ]
            publish_clicked = False
            for sel in publish_selectors:
                if page.locator(sel).count() > 0:
                    page.click(sel)
                    print(f"公開ボタンクリック（セレクター: {sel}）")
                    publish_clicked = True
                    break
            if not publish_clicked:
                print("警告: 公開ボタンが見つかりませんでした")

            page.wait_for_timeout(3000)
            page.screenshot(path="debug_screenshots/06_publish_dialog.png", full_page=True)

            # 公開確認ダイアログ
            confirm_selectors = [
                'button:has-text("公開する")',
                'button:has-text("投稿する")',
            ]
            for sel in confirm_selectors:
                if page.locator(sel).count() > 0:
                    page.click(sel)
                    print(f"公開確認クリック（セレクター: {sel}）")
                    break

            page.wait_for_timeout(4000)
            page.screenshot(path="debug_screenshots/07_after_publish.png", full_page=True)
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

    post_to_note(title, body)


if __name__ == "__main__":
    main()
