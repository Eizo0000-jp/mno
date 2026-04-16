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

    post_to_note(title, body)


if __name__ == "__main__":
    main()
