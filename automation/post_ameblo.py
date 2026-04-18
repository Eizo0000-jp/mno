"""
アメブロ 自動投稿スクリプト
Cookie認証でアメブロにアクセスし、Claude APIで生成した記事を投稿する

必要な環境変数:
  AMEBLO_AT         - blog.ameba.jp の Cookie "AT" の値
  AMEBLO_JSESSIONID - blog.ameba.jp の Cookie "JSESSIONID" の値
  AMEBLO_P          - blog.ameba.jp の Cookie "p" の値
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
    """Cookie認証でアメブロに記事を投稿"""
    at_cookie      = os.environ["AMEBLO_AT"]
    jsessionid     = os.environ["AMEBLO_JSESSIONID"]
    p_cookie       = os.environ["AMEBLO_P"]
    html_body = markdown_to_ameblo_html(body)

    ENTRY_URL = "https://blog.ameba.jp/ucs/entry/srventryinsertinput.do"

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

        # ── 1. Cookie をセット ───────────────────────────────────────
        context.add_cookies([
            {"name": "AT",         "value": at_cookie,  "domain": "blog.ameba.jp", "path": "/"},
            {"name": "JSESSIONID", "value": jsessionid, "domain": "blog.ameba.jp", "path": "/"},
            {"name": "p",          "value": p_cookie,   "domain": "blog.ameba.jp", "path": "/"},
            # 親ドメインにも AT を設定（SSO連携用）
            {"name": "AT",         "value": at_cookie,  "domain": ".ameba.jp",     "path": "/"},
            {"name": "p",          "value": p_cookie,   "domain": ".ameba.jp",     "path": "/"},
        ])

        page = context.new_page()

        try:
            os.makedirs("debug_screenshots", exist_ok=True)

            # ── 2. 記事作成ページへ直接アクセス ────────────────────
            print("記事作成ページへアクセス中...")
            page.goto(ENTRY_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            page.screenshot(path="debug_screenshots/01_initial.png")
            print(f"初期URL: {page.url}")

            # Cookie切れ等でログイン画面にリダイレクトされた場合
            if any(d in page.url for d in ["auth.user.ameba", "accounts.ameba", "signin"]):
                raise RuntimeError(
                    "Cookie認証失敗。セッションが期限切れの可能性があります。\n"
                    "ブラウザで blog.ameba.jp にログインし直して "
                    "AT・JSESSIONID・p Cookie を再取得してください。"
                )
            print("Cookie認証OK")

            # ── 4. 記事作成ページへ（まだそこにいなければ移動） ────
            if "srventryinsertinput" not in page.url:
                print("記事作成ページへ移動中...")
                page.goto(ENTRY_URL, wait_until="domcontentloaded")
                page.wait_for_timeout(5000)
            else:
                print("すでに記事作成ページにいます")
            page.screenshot(path="debug_screenshots/05_new_entry.png")
            print(f"記事作成ページURL: {page.url}")

            # ── 5. タイトル入力 ───────────────────────────────────
            # 旧アメブロエディタのタイトルフィールド
            title_selectors = [
                'input[name="entry_title"]',
                'input[id="entryTitle"]',
                'input[placeholder*="タイトル"]',
                'input[name="title"]',
            ]
            title_filled = False
            for sel in title_selectors:
                if page.locator(sel).count() > 0:
                    page.fill(sel, title)
                    print(f"タイトル入力完了: {title}")
                    title_filled = True
                    break

            if not title_filled:
                print("警告: タイトル入力フィールドが見つかりませんでした")

            page.wait_for_timeout(1000)

            # ── 6. 本文入力 ───────────────────────────────────────
            # まず「テキスト」「HTML」モードへの切り替えボタンを探す
            # 旧エディタはFCKeditor（iframe内）か、テキストモード用textarea
            page.screenshot(path="debug_screenshots/06_editor.png")

            # ── 本文入力（新WYSIWYGエディタ対応） ────────────────
            # タイトル以外の大きい contenteditable に本文を書き込む
            body_filled = page.evaluate("""(text) => {
                const editables = Array.from(
                    document.querySelectorAll('[contenteditable="true"]')
                );
                // 高さ100px以上の要素を本文エリアとみなす（タイトルを除外）
                const bodyEl = editables.find(el => {
                    const rect = el.getBoundingClientRect();
                    return rect.height > 100;
                });
                if (!bodyEl) return false;
                bodyEl.focus();
                // 既存内容をクリアしてテキストをセット
                bodyEl.innerText = text;
                bodyEl.dispatchEvent(new Event('input', { bubbles: true }));
                bodyEl.dispatchEvent(new Event('change', { bubbles: true }));
                return true;
            }""", body)

            if body_filled:
                print("本文入力完了（JS innerText）")
            else:
                print("警告: 本文エリアが見つかりませんでした")

            page.wait_for_timeout(2000)
            page.screenshot(path="debug_screenshots/07_article_filled.png")

            # ── 7. 公開（投稿）ボタンをクリック ─────────────────
            # 新エディタ: button要素を優先、input[type=submit]もフォールバック
            published = False
            publish_selectors = [
                'button:has-text("投稿する")',
                'button:has-text("公開する")',
                'button:has-text("投稿")',
                'button:has-text("公開")',
                'input[type="submit"][value*="投稿"]',
                'input[type="submit"][value*="公開"]',
                'input[type="submit"]',
            ]
            for sel in publish_selectors:
                locs = page.locator(sel)
                if locs.count() > 0 and locs.first.is_visible():
                    locs.first.click()
                    print(f"投稿ボタンクリック: {sel}")
                    published = True
                    break

            if not published:
                # デバッグ: 全ボタンを出力
                for el in page.locator("button").all():
                    try:
                        print(f"  button: '{el.inner_text().strip()}' visible={el.is_visible()}")
                    except Exception:
                        pass
                for el in page.locator('input[type="submit"]').all():
                    print(f"  submit: value='{el.get_attribute('value')}'")
                raise RuntimeError("投稿ボタンが見つかりませんでした")

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
