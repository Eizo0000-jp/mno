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

            ENTRY_URL = "https://blog.ameba.jp/ucs/entry/srventryinsertinput.do"

            # ── 1. 記事作成URLへ直接アクセス（SSOリダイレクト待ち） ──
            print("記事作成ページへ直接アクセス（SSOフロー開始）...")
            page.goto(ENTRY_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            page.screenshot(path="debug_screenshots/01_initial.png")
            print(f"初期URL: {page.url}")

            # ── 2. ログイン処理（auth.user.ameba.jp のSPA対応） ────────
            # SPAなのでJSレンダリングを待ってからフォームを探す
            print(f"現在のURL: {page.url}")

            # auth ドメインにいる＝ログインが必要
            if any(d in page.url for d in ["auth.user.ameba", "accounts.ameba", "signin"]):
                print("ログインフォームを待機中...")

                # SPAのレンダリングを待つ（最大15秒）
                try:
                    page.wait_for_selector("input", timeout=15000)
                except Exception:
                    pass
                page.wait_for_timeout(2000)
                page.screenshot(path="debug_screenshots/02_login_form.png")

                # ページ上の全inputを列挙してデバッグ
                inputs = page.locator("input").all()
                print(f"input要素数: {len(inputs)}")
                for i, inp in enumerate(inputs):
                    try:
                        print(f"  input[{i}] type={inp.get_attribute('type')} name={inp.get_attribute('name')} id={inp.get_attribute('id')} placeholder={inp.get_attribute('placeholder')}")
                    except Exception:
                        pass

                # メールアドレス入力（幅広くセレクタを試す）
                email_sel = None
                for s in [
                    'input[type="email"]',
                    'input[name="email"]',
                    'input[name="signin_id"]',
                    'input[name="ameba_id"]',
                    'input[name="username"]',
                    'input[name="userId"]',
                    'input[autocomplete="email"]',
                    'input[autocomplete="username"]',
                    'input[type="text"]',  # 最終フォールバック
                ]:
                    if page.locator(s).count() > 0 and page.locator(s).first.is_visible():
                        email_sel = s
                        break

                if email_sel is None:
                    raise RuntimeError("メールアドレス入力欄が見つかりません。スクリーンショットを確認してください。")

                page.fill(email_sel, email)
                print(f"メールアドレス入力完了（{email_sel}）")

                # パスワード欄がなければ「次へ」で進む
                if page.locator('input[type="password"]').count() == 0:
                    for s in ['button:has-text("次へ")', 'button:has-text("続ける")', 'button[type="submit"]', 'input[type="submit"]']:
                        if page.locator(s).count() > 0 and page.locator(s).first.is_visible():
                            page.click(s)
                            print(f"次へボタンクリック: {s}")
                            page.wait_for_timeout(3000)
                            break

                page.screenshot(path="debug_screenshots/03_after_email.png")

                # パスワード入力（最大10秒待機）
                try:
                    page.wait_for_selector('input[type="password"]', timeout=10000)
                except Exception:
                    pass

                pw_sel = None
                for s in ['input[type="password"]', 'input[name="password"]']:
                    if page.locator(s).count() > 0 and page.locator(s).first.is_visible():
                        pw_sel = s
                        break

                if pw_sel is None:
                    raise RuntimeError("パスワード入力欄が見つかりません。")

                page.fill(pw_sel, password)
                print(f"パスワード入力完了（{pw_sel}）")

                # ログインボタン
                for s in ['button[type="submit"]', 'button:has-text("ログイン")', 'button:has-text("サインイン")', 'input[type="submit"]']:
                    if page.locator(s).count() > 0 and page.locator(s).first.is_visible():
                        page.click(s)
                        print(f"ログインボタンクリック: {s}")
                        break

                # SSO完了 → blog.ameba.jp へのリダイレクトを待つ
                print("SSOリダイレクト待機中...")
                try:
                    page.wait_for_url("**/blog.ameba.jp/**", timeout=30000)
                except Exception:
                    pass
                page.wait_for_timeout(3000)

            page.screenshot(path="debug_screenshots/04_after_login.png")
            print(f"ログイン後URL: {page.url}")

            # まだ auth ドメインにいる場合はログイン失敗
            if any(d in page.url for d in ["auth.user.ameba", "accounts.ameba", "signin"]):
                raise RuntimeError(f"ログイン失敗 / SSO未完了。現在のURL: {page.url}")
            print("ログイン・SSO完了")

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
            text_mode_selectors = [
                'a:has-text("テキスト")',
                'a:has-text("HTML")',
                'input[value="テキスト"]',
                'span:has-text("テキスト")',
                '#tabText',
                '.tab-text',
            ]
            for sel in text_mode_selectors:
                if page.locator(sel).count() > 0:
                    page.click(sel)
                    page.wait_for_timeout(1500)
                    print(f"テキストモードに切り替え: {sel}")
                    break

            page.screenshot(path="debug_screenshots/06_text_mode.png")

            body_filled = False

            # パターンA: テキストモードの textarea に直接書き込む
            textarea_selectors = [
                'textarea[name="entry_body"]',
                'textarea[id="bodyText"]',
                'textarea[id*="body"]',
                'textarea[name*="body"]',
                'textarea[placeholder*="本文"]',
            ]
            for sel in textarea_selectors:
                if page.locator(sel).count() > 0 and page.locator(sel).first.is_visible():
                    page.fill(sel, html_body)
                    print(f"本文入力完了（textarea: {sel}）")
                    body_filled = True
                    break

            # パターンB: FCKeditor iframe内の contenteditable
            if not body_filled:
                frames = page.frames
                print(f"フレーム数: {len(frames)}")
                for frame in frames:
                    try:
                        editable = frame.locator('[contenteditable="true"]')
                        if editable.count() > 0 and editable.first.is_visible():
                            editable.first.click()
                            frame.evaluate(
                                "(el, html) => { el.innerHTML = html; }",
                                [editable.first.element_handle(), html_body],
                            )
                            print("本文入力完了（FCKeditor iframe）")
                            body_filled = True
                            break
                    except Exception as e:
                        print(f"フレーム試行スキップ: {e}")

            # パターンC: メインページの contenteditable
            if not body_filled:
                for sel in ['[contenteditable="true"]', '.ql-editor', '[role="textbox"]']:
                    locs = page.locator(sel).all()
                    for loc in locs:
                        if loc.is_visible():
                            loc.click()
                            page.wait_for_timeout(500)
                            page.keyboard.type(body, delay=3)
                            print(f"本文入力完了（contenteditable: {sel}）")
                            body_filled = True
                            break
                    if body_filled:
                        break

            if not body_filled:
                print("警告: 本文入力フィールドが見つかりませんでした")

            page.wait_for_timeout(2000)
            page.screenshot(path="debug_screenshots/07_article_filled.png")

            # ── 7. 公開（投稿）ボタンをクリック ─────────────────
            # 旧エディタは input[type=submit] が多い
            published = False
            submit_input_selectors = [
                'input[type="submit"][value*="投稿"]',
                'input[type="submit"][value*="公開"]',
                'input[type="submit"][value*="保存"]',
                'input[type="submit"]',
            ]
            for sel in submit_input_selectors:
                if page.locator(sel).count() > 0 and page.locator(sel).first.is_visible():
                    page.locator(sel).first.click()
                    print(f"投稿ボタンクリック: {sel}")
                    published = True
                    break

            if not published:
                # button 形式もフォールバックで試す
                for sel in ['button:has-text("投稿")', 'button:has-text("公開")']:
                    if page.locator(sel).count() > 0:
                        page.locator(sel).first.click()
                        print(f"投稿ボタンクリック（button）: {sel}")
                        published = True
                        break

            if not published:
                # デバッグ: 全 submit 要素を出力
                for el in page.locator('input[type="submit"]').all():
                    print(f"  submit: value='{el.get_attribute('value')}'")
                for el in page.locator("button").all():
                    try:
                        print(f"  button: '{el.inner_text().strip()}'")
                    except Exception:
                        pass
                raise RuntimeError("投稿ボタンが見つかりませんでした")

            page.wait_for_timeout(5000)
            page.screenshot(path="debug_screenshots/08_after_publish.png")

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
