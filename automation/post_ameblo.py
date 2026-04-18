"""
アメブロ 自動投稿スクリプト
Playwrightでアメブロにログインし、Claude APIで生成した記事を投稿する

必要な環境変数:
  AMEBLO_EMAIL      - アメブロのログインメールアドレス
  AMEBLO_PASSWORD   - アメブロのパスワード
  ANTHROPIC_API_KEY - Claude API Key
"""

import os
import re
import sys
import random
import anthropic
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

LP_URL = "https://mobile-friend.com"

AMEBLO_TOPICS = [
    "楽天モバイルに乗り換えたら月々の支出が変わった話",
    "社員紹介キャンペーンで14,000ポイントもらえた件",
    "スマホ代を見直したらこうなった",
    "楽天モバイルの社員がおすすめする理由を正直に話す",
    "MNPで乗り換えた手順を全部まとめてみた",
    "楽天経済圏とスマホ代の節約を同時にやってみた",
    "家族全員で乗り換えたら年間いくら変わったか",
    "社員紹介と通常申込みの違いを比べてみた",
    "楽天モバイルのデータ無制限プランを使い倒した感想",
    "乗り換えを迷ってる人に伝えたいこと",
]


def generate_article() -> tuple[str, str]:
    """Claude APIでアメブロ向け体験談記事を生成"""
    client = anthropic.Anthropic()
    topic = random.choice(AMEBLO_TOPICS)

    prompt = f"""アメブロ（アメーバブログ）に投稿する体験談ブログ記事を書いてください。

テーマ: {topic}
紹介LP URL: {LP_URL}

前提知識:
- 楽天モバイルの社員紹介キャンペーンはMNP（乗り換え）で最大14,000ポイント
- 新規申込みは11,000ポイント
- 通常キャンペーンより多くもらえる（通常は13,000ポイント）
- 月額料金は3,278円（税込）でデータ無制限
- ポイントは紹介ログイン月の4ヶ月後から3ヶ月間に分割進呈
- 条件にRakuten Linkで10秒以上の通話が必要

要件:
- 一人称・体験談スタイル（「私は〜」「〜でした」）
- アメブロらしい親しみやすい文体（絵文字や「〜ですよね！」など）
- 文字数: 800〜1200字
- 読者に役立つ具体的な情報を含める
- 見出し(##)を3〜4個使って構造化する
- 最後のセクションで {LP_URL} へ自然に誘導する（広告感を出さない）
- 最初の行を「title: タイトル」の形式にする

出力は記事本文のみ（説明文不要）。"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1800,
        messages=[{"role": "user", "content": prompt}]
    )

    content = message.content[0].text.strip()
    title_match = re.match(r"title:\s*(.+)", content)
    title = title_match.group(1).strip() if title_match else topic
    body = re.sub(r"^title:.+\n+", "", content).strip()

    return title, body


def markdown_to_ameblo_html(body: str) -> str:
    """MarkdownをアメブロのHTMLエディタ向けに変換"""
    lines = body.split("\n")
    html_lines = []
    for line in lines:
        # ## 見出し → <h3>
        if line.startswith("## "):
            text = line[3:].strip()
            html_lines.append(f"<h3><strong>{text}</strong></h3>")
        # ### 見出し → <h4>
        elif line.startswith("### "):
            text = line[4:].strip()
            html_lines.append(f"<h4><strong>{text}</strong></h4>")
        # **太字**
        elif line.strip():
            converted = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
            html_lines.append(f"<p>{converted}</p>")
        else:
            html_lines.append("<br>")
    return "\n".join(html_lines)


def post_to_ameblo(title: str, body: str) -> None:
    """Playwrightでアメブロにログインして記事を投稿"""
    email = os.environ["AMEBLO_EMAIL"]
    password = os.environ["AMEBLO_PASSWORD"]
    html_body = markdown_to_ameblo_html(body)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            locale="ja-JP",
        )
        page = context.new_page()

        try:
            os.makedirs("debug_screenshots", exist_ok=True)

            # ── 1. ログインページへ ──────────────────────────────────
            print("ログインページへ移動中...")
            page.goto("https://www.ameba.jp/", wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            page.screenshot(path="debug_screenshots/01_top.png")

            # ログインリンクをクリック
            login_selectors = [
                'a:has-text("ログイン")',
                'a[href*="login"]',
                'a[href*="accounts.ameba"]',
            ]
            for sel in login_selectors:
                if page.locator(sel).first.is_visible():
                    page.locator(sel).first.click()
                    break
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(2000)
            page.screenshot(path="debug_screenshots/02_login_page.png")
            print(f"ログインページURL: {page.url}")

            # ── 2. メールアドレス入力 ──────────────────────────────
            email_selectors = [
                'input[type="email"]',
                'input[name="email"]',
                'input[placeholder*="メール"]',
                'input[id*="email"]',
            ]
            for sel in email_selectors:
                if page.locator(sel).count() > 0:
                    page.fill(sel, email)
                    print("メールアドレス入力完了")
                    break

            # メール入力後に「次へ」ボタンがある場合はクリック
            next_btn_selectors = [
                'button:has-text("次へ")',
                'button[type="submit"]:has-text("次")',
                'input[type="submit"]',
            ]
            for sel in next_btn_selectors:
                if page.locator(sel).count() > 0:
                    page.click(sel)
                    page.wait_for_load_state("domcontentloaded")
                    page.wait_for_timeout(2000)
                    break

            page.screenshot(path="debug_screenshots/03_after_email.png")

            # ── 3. パスワード入力 ──────────────────────────────────
            password_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                'input[placeholder*="パスワード"]',
            ]
            for sel in password_selectors:
                if page.locator(sel).count() > 0:
                    page.fill(sel, password)
                    print("パスワード入力完了")
                    break

            # ログインボタンをクリック
            submit_selectors = [
                'button[type="submit"]',
                'button:has-text("ログイン")',
                'input[type="submit"]',
            ]
            for sel in submit_selectors:
                if page.locator(sel).count() > 0:
                    page.click(sel)
                    break

            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(4000)
            page.screenshot(path="debug_screenshots/04_after_login.png")
            print(f"ログイン後URL: {page.url}")

            # ログイン成功確認
            if "login" in page.url or "accounts.ameba" in page.url:
                raise RuntimeError(f"ログイン失敗。現在のURL: {page.url}")
            print("ログイン成功")

            # ── 4. 新規記事作成ページへ ────────────────────────────
            print("記事作成ページへ移動中...")
            page.goto("https://blog.ameba.jp/entries/new", wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            page.screenshot(path="debug_screenshots/05_new_entry.png")
            print(f"記事作成ページURL: {page.url}")

            # ── 5. タイトル入力 ───────────────────────────────────
            title_selectors = [
                'input[placeholder*="タイトル"]',
                'input[name="title"]',
                'input[id*="title"]',
                'textarea[placeholder*="タイトル"]',
                '[data-testid="title-input"]',
            ]
            title_filled = False
            for sel in title_selectors:
                if page.locator(sel).count() > 0:
                    page.click(sel)
                    page.fill(sel, title)
                    print(f"タイトル入力完了: {title}")
                    title_filled = True
                    break

            if not title_filled:
                print("警告: タイトル入力フィールドが見つかりませんでした")

            page.wait_for_timeout(1000)

            # ── 6. 本文入力（HTMLエディタ経由） ──────────────────
            # まずHTMLモードに切り替えを試みる
            html_mode_selectors = [
                'button:has-text("HTML")',
                '[data-testid="html-mode"]',
                'button:has-text("ソース")',
                'label:has-text("HTML")',
            ]
            html_mode_switched = False
            for sel in html_mode_selectors:
                if page.locator(sel).count() > 0:
                    page.click(sel)
                    page.wait_for_timeout(1000)
                    html_mode_switched = True
                    print("HTMLモードに切り替え")
                    break

            if html_mode_switched:
                # HTMLモード: textarea に直接書き込む
                textarea_selectors = [
                    'textarea[name="body"]',
                    'textarea[id*="body"]',
                    'textarea[placeholder*="本文"]',
                    '.html-editor textarea',
                    'textarea',
                ]
                body_filled = False
                for sel in textarea_selectors:
                    if page.locator(sel).count() > 0:
                        page.fill(sel, html_body)
                        print("本文入力完了（HTMLモード）")
                        body_filled = True
                        break
            else:
                body_filled = False

            if not body_filled:
                # リッチテキストエディタ（contenteditable）にキー入力
                body_selectors = [
                    '[contenteditable="true"]',
                    '.ProseMirror',
                    '[data-testid="body-editor"]',
                    '.ql-editor',
                    '[role="textbox"]',
                ]
                for sel in body_selectors:
                    locators = page.locator(sel).all()
                    # タイトル以外の最初のeditableを使用
                    for loc in locators:
                        if loc.is_visible():
                            loc.click()
                            page.wait_for_timeout(500)
                            # プレーンテキストとして入力（Markdownのまま）
                            page.keyboard.type(body, delay=5)
                            print("本文入力完了（リッチテキストエディタ）")
                            body_filled = True
                            break
                    if body_filled:
                        break

            if not body_filled:
                print("警告: 本文入力フィールドが見つかりませんでした")

            page.wait_for_timeout(2000)
            page.screenshot(path="debug_screenshots/06_article_filled.png")

            # ── 7. 公開ボタンをクリック ────────────────────────────
            publish_selectors = [
                'button:has-text("公開する")',
                'button:has-text("投稿する")',
                'button:has-text("公開")',
                'button:has-text("投稿")',
                '[data-testid="publish-button"]',
            ]
            published = False
            for sel in publish_selectors:
                if page.locator(sel).count() > 0:
                    page.locator(sel).first.click()
                    print(f"公開ボタンクリック: {sel}")
                    published = True
                    break

            if not published:
                # ボタン一覧をデバッグ出力
                buttons = page.locator("button").all()
                print(f"ボタン一覧（{len(buttons)}件）:")
                for i, btn in enumerate(buttons):
                    try:
                        print(f"  [{i}] '{btn.inner_text().strip()}'")
                    except Exception:
                        pass
                raise RuntimeError("公開ボタンが見つかりませんでした")

            page.wait_for_timeout(4000)
            page.screenshot(path="debug_screenshots/07_publish_dialog.png")

            # 確認ダイアログがある場合
            confirm_selectors = [
                'button:has-text("公開する")',
                'button:has-text("投稿する")',
                'button:has-text("OK")',
                'button:has-text("確認")',
            ]
            for sel in confirm_selectors:
                if page.locator(sel).count() > 0:
                    page.locator(sel).last.click()
                    print(f"確認ダイアログクリック: {sel}")
                    break

            page.wait_for_timeout(5000)
            page.screenshot(path="debug_screenshots/08_after_publish.png")
            print(f"最終URL: {page.url}")
            print(f"投稿完了: {title}")

        except PlaywrightTimeoutError as e:
            page.screenshot(path="debug_screenshots/error_timeout.png")
            print(f"タイムアウトエラー: {e}")
            raise
        except Exception as e:
            try:
                page.screenshot(path="debug_screenshots/error_general.png")
            except Exception:
                pass
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

    post_to_ameblo(title, body)


if __name__ == "__main__":
    main()
