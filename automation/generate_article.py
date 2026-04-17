"""
SEOブログ記事 自動生成スクリプト（多言語対応）
Claude APIで楽天モバイル関連記事を生成し _posts/ に保存する
"""

import re
import random
from datetime import date
from pathlib import Path
import anthropic

REFERRAL_URL = "https://r10.to/henTIE"
REPO_ROOT = Path(__file__).parent.parent

LANG_CONFIGS = {
    "ja": {
        "weight": 4,
        "topics": [
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
        ],
        "prompt": """SEOに最適化された日本語ブログ記事をMarkdown形式で作成してください。

メインキーワード: {keyword}
楽天モバイル社員紹介URL: {url}

前提知識:
- 楽天モバイルには社員紹介キャンペーンがある
- 社員紹介リンク経由で申し込むと、MNP（乗り換え）で14,000ポイント、新規申込みで11,000ポイント付与
- 通常キャンペーンはMNP13,000ポイント（社員紹介の方が1,000pt多い）
- 料金は月3,278円（税込）、データ無制限
- ポイントは紹介ログイン月の4ヶ月後から3ヶ月間に分割進呈

要件:
- 最初の行を「title: 記事タイトル」の形式にする
- ## と ### の見出しで構造化する
- 文字数: 1200〜1800字
- 具体的な数字で価値を伝える
- 自然な文章で押しつけがましくない
- 記事の最後のセクションで紹介リンクへ自然に誘導する

出力は記事本文のみ。""",
    },
    "en": {
        "weight": 1,
        "topics": [
            ("Rakuten Mobile employee referral campaign up to 14000 points how to get", "en-employee-referral-14000pt"),
            ("Rakuten Mobile employee referral vs normal application points comparison", "en-referral-vs-normal"),
            ("How to apply for Rakuten Mobile via employee referral link step by step", "en-referral-apply-guide"),
            ("How to use 14000 Rakuten points best ways for foreign residents Japan", "en-14000-points-usage"),
            ("Rakuten Mobile employee referral campaign FAQ for foreigners in Japan", "en-employee-referral-faq"),
            ("Best time to switch to Rakuten Mobile using employee referral", "en-referral-best-timing"),
            ("Rakuten Mobile vs Docomo au Softbank price comparison for foreigners", "en-vs-major-carriers"),
            ("How to do MNP number portability to Rakuten Mobile complete guide", "en-mnp-guide"),
            ("Rakuten ecosystem maximize savings smartphone foreign resident Japan", "en-ecosystem-savings"),
            ("Switch whole family to Rakuten Mobile savings calculation", "en-family-switch-savings"),
        ],
        "prompt": """Write an SEO-optimized English blog article in Markdown format.
Target audience: foreign residents in Japan considering switching to Rakuten Mobile.

Main keyword: {keyword}
Rakuten Mobile employee referral URL: {url}

Key facts:
- Rakuten Mobile has an employee referral campaign
- Via referral link: 14,000 points for MNP (carrier switch), 11,000 points for new signup
- Normal campaign: 13,000 points for MNP (referral gives 1,000pt more)
- Monthly plan: ¥3,278 (tax included), unlimited data
- Points paid in 3 installments starting 4 months after referral login month
- Max 5 lines per person

Requirements:
- First line: "title: Article Title" (in English)
- Use ## and ### headings for structure
- Length: 900-1400 words
- Include specific point numbers
- Natural, non-pushy tone
- End with natural referral link guidance

Output article body only.""",
    },
    "ko": {
        "weight": 1,
        "topics": [
            ("라쿠텐 모바일 직원 소개 14000포인트 받는 방법", "ko-employee-referral-14000pt"),
            ("라쿠텐 모바일 직원 소개 vs 일반 신청 포인트 비교", "ko-referral-vs-normal"),
            ("라쿠텐 모바일 직원 소개 링크로 신청하는 방법 단계별 가이드", "ko-referral-apply-guide"),
            ("라쿠텐 포인트 14000포인트 활용법 재일 외국인", "ko-14000-points-usage"),
            ("라쿠텐 모바일 직원 소개 캠페인 자주 묻는 질문", "ko-employee-referral-faq"),
            ("라쿠텐 모바일 번호이동 신청 방법 완전 가이드", "ko-mnp-guide"),
            ("라쿠텐 모바일 도코모 au 소프트뱅크 요금 비교", "ko-vs-major-carriers"),
            ("가족 모두 라쿠텐 모바일로 전환 절약 금액 계산", "ko-family-switch"),
        ],
        "prompt": """한국어로 SEO에 최적화된 블로그 기사를 Markdown 형식으로 작성하세요.
대상 독자: 라쿠텐 모바일로 전환을 고려하는 재일 한국인.

메인 키워드: {keyword}
라쿠텐 모바일 직원 소개 URL: {url}

주요 사실:
- 라쿠텐 모바일에는 직원 소개 캠페인이 있음
- 소개 링크를 통해 신청하면: MNP(번호이동) 14,000포인트, 신규 신청 11,000포인트
- 일반 캠페인은 MNP 13,000포인트 (직원 소개가 1,000pt 더 많음)
- 월 요금: 3,278엔 (세금 포함), 데이터 무제한
- 포인트는 소개 로그인 월로부터 4개월 후부터 3개월에 걸쳐 지급

요건:
- 첫 번째 줄: "title: 기사 제목" (한국어로)
- ## 및 ### 제목으로 구성
- 분량: 900~1400 단어
- 구체적인 숫자 포함
- 자연스럽고 강요하지 않는 톤
- 마지막에 자연스럽게 소개 링크로 유도

기사 본문만 출력.""",
    },
    "zh-cn": {
        "weight": 1,
        "topics": [
            ("乐天手机员工介绍活动最高14000积分如何获得", "zh-cn-employee-referral-14000pt"),
            ("乐天手机员工介绍和普通申请积分对比", "zh-cn-referral-vs-normal"),
            ("如何通过员工介绍链接申请乐天手机详细步骤", "zh-cn-referral-apply-guide"),
            ("14000乐天积分怎么用最划算在日华人", "zh-cn-14000-points-usage"),
            ("乐天手机员工介绍活动常见问题解答", "zh-cn-employee-referral-faq"),
            ("乐天手机携号转网详细指南", "zh-cn-mnp-guide"),
            ("乐天手机vs三大运营商价格比较", "zh-cn-vs-major-carriers"),
            ("全家转乐天手机能省多少钱", "zh-cn-family-switch"),
        ],
        "prompt": """用简体中文写一篇SEO优化的博客文章，格式为Markdown。
目标读者：考虑使用乐天手机的在日华人。

主要关键词: {keyword}
乐天手机员工介绍URL: {url}

主要信息:
- 乐天手机有员工介绍活动
- 通过介绍链接申请：MNP（携号转网）14,000积分，新申请11,000积分
- 普通活动：MNP 13,000积分（员工介绍多1,000积分）
- 月费：3,278日元（含税），无限流量
- 积分从介绍登录月起4个月后开始，分3个月发放

要求:
- 第一行："title: 文章标题"（用中文）
- 用##和###标题组织结构
- 字数：900-1400字
- 包含具体数字
- 自然、不强迫推销的语气
- 结尾自然引导到介绍链接

只输出文章正文。""",
    },
    "zh-tw": {
        "weight": 1,
        "topics": [
            ("樂天手機員工介紹活動最高14000點數如何獲得", "zh-tw-employee-referral-14000pt"),
            ("樂天手機員工介紹和一般申請點數比較", "zh-tw-referral-vs-normal"),
            ("如何透過員工介紹連結申請樂天手機詳細步驟", "zh-tw-referral-apply-guide"),
            ("14000樂天點數怎麼用最划算在日台灣人", "zh-tw-14000-points-usage"),
            ("樂天手機員工介紹活動常見問題解答", "zh-tw-employee-referral-faq"),
            ("樂天手機號碼攜入詳細指南", "zh-tw-mnp-guide"),
            ("樂天手機vs三大電信費用比較", "zh-tw-vs-major-carriers"),
            ("全家轉樂天手機能省多少錢", "zh-tw-family-switch"),
        ],
        "prompt": """用繁體中文寫一篇SEO優化的部落格文章，格式為Markdown。
目標讀者：考慮使用樂天手機的在日台灣人。

主要關鍵詞: {keyword}
樂天手機員工介紹URL: {url}

主要資訊:
- 樂天手機有員工介紹活動
- 透過介紹連結申請：MNP（號碼攜入）14,000點數，新申請11,000點數
- 一般活動：MNP 13,000點數（員工介紹多1,000點）
- 月費：3,278日圓（含稅），無限流量
- 點數從介紹登入月起4個月後開始，分3個月發放

要求:
- 第一行：「title: 文章標題」（用繁體中文）
- 用##和###標題組織結構
- 字數：900-1400字
- 包含具體數字
- 自然、不強迫推銷的語氣
- 結尾自然引導到介紹連結

只輸出文章正文。""",
    },
    "tl": {
        "weight": 1,
        "topics": [
            ("Rakuten Mobile employee referral 14000 puntos paano makuha", "tl-employee-referral-14000pt"),
            ("Rakuten Mobile referral link paano mag-apply hakbang hakbang", "tl-referral-apply-guide"),
            ("Rakuten Mobile referral vs normal application pagkakaiba", "tl-referral-vs-normal"),
            ("14000 Rakuten points paano gamitin pinakamabuting paraan", "tl-14000-points-usage"),
            ("Rakuten Mobile MNP numero portability gabay Pilipino sa Japan", "tl-mnp-guide"),
            ("Buong pamilya mag-switch Rakuten Mobile magkano matitipid", "tl-family-switch"),
        ],
        "prompt": """Write an SEO-optimized blog article in Filipino/Tagalog in Markdown format.
Target audience: Filipino residents in Japan considering Rakuten Mobile.

Main keyword: {keyword}
Rakuten Mobile employee referral URL: {url}

Key facts:
- Rakuten Mobile has an employee referral campaign
- Via referral link: 14,000 points for MNP, 11,000 points for new signup
- Normal campaign: 13,000 points for MNP
- Monthly fee: ¥3,278 (tax included), unlimited data
- Points paid in 3 installments starting 4 months after referral login

Requirements:
- First line: "title: Pamagat ng Artikulo" (in Filipino)
- Use ## and ### headings
- Length: 800-1200 words in Filipino/Tagalog
- Include specific point numbers
- Natural, friendly tone
- End with natural referral link guidance

Output article body only.""",
    },
    "vi": {
        "weight": 1,
        "topics": [
            ("Rakuten Mobile giới thiệu nhân viên 14000 điểm cách nhận", "vi-employee-referral-14000pt"),
            ("Hướng dẫn đăng ký Rakuten Mobile qua link giới thiệu từng bước", "vi-referral-apply-guide"),
            ("So sánh Rakuten Mobile giới thiệu nhân viên vs đăng ký thường", "vi-referral-vs-normal"),
            ("14000 điểm Rakuten dùng gì tiết kiệm nhất người Việt ở Nhật", "vi-14000-points-usage"),
            ("Hướng dẫn chuyển mạng giữ số sang Rakuten Mobile đầy đủ", "vi-mnp-guide"),
            ("Cả gia đình chuyển sang Rakuten Mobile tiết kiệm bao nhiêu", "vi-family-switch"),
        ],
        "prompt": """Viết một bài blog SEO tối ưu bằng tiếng Việt theo định dạng Markdown.
Độc giả mục tiêu: Người Việt Nam tại Nhật Bản đang xem xét chuyển sang Rakuten Mobile.

Từ khóa chính: {keyword}
URL giới thiệu nhân viên Rakuten Mobile: {url}

Thông tin chính:
- Rakuten Mobile có chương trình giới thiệu nhân viên
- Qua link giới thiệu: 14,000 điểm cho MNP, 11,000 điểm cho đăng ký mới
- Chiến dịch thông thường: 13,000 điểm cho MNP
- Phí hàng tháng: 3,278 yên (đã bao gồm thuế), data không giới hạn
- Điểm được trả trong 3 đợt bắt đầu từ 4 tháng sau tháng đăng nhập giới thiệu

Yêu cầu:
- Dòng đầu tiên: "title: Tiêu đề bài viết" (bằng tiếng Việt)
- Dùng ## và ### cho tiêu đề
- Độ dài: 800-1200 từ bằng tiếng Việt
- Bao gồm số điểm cụ thể
- Giọng điệu tự nhiên, không ép buộc
- Kết thúc với hướng dẫn tự nhiên đến link giới thiệu

Chỉ xuất nội dung bài viết.""",
    },
}


def pick_lang() -> str:
    """言語をウェイトに基づいてランダムに選択"""
    langs = list(LANG_CONFIGS.keys())
    weights = [LANG_CONFIGS[l]["weight"] for l in langs]
    return random.choices(langs, weights=weights)[0]


def pick_unused_topic(lang: str) -> tuple[str, str]:
    """まだ記事化していないトピックを選ぶ"""
    posts_dir = REPO_ROOT / "_posts"
    existing_slugs = {p.stem.split("-", 3)[-1] for p in posts_dir.glob("*.md")} if posts_dir.exists() else set()

    topics = LANG_CONFIGS[lang]["topics"]
    unused = [(kw, slug) for kw, slug in topics if slug not in existing_slugs]
    if not unused:
        unused = topics

    return random.choice(unused)


def generate_article(keyword: str, lang: str) -> tuple[str, str]:
    """Claude APIで記事を生成しタイトルと本文を返す"""
    client = anthropic.Anthropic()

    prompt_template = LANG_CONFIGS[lang]["prompt"]
    prompt = prompt_template.format(keyword=keyword, url=REFERRAL_URL)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}]
    )

    content = message.content[0].text.strip()

    title_match = re.match(r"title:\s*(.+)", content)
    title = title_match.group(1).strip().strip('"') if title_match else keyword
    body = re.sub(r"^title:.+\n+", "", content).strip()

    return title, body


def save_post(title: str, body: str, slug: str, lang: str) -> Path:
    today = date.today()
    filename = f"{today.strftime('%Y-%m-%d')}-{slug}.md"
    posts_dir = REPO_ROOT / "_posts"
    posts_dir.mkdir(exist_ok=True)
    filepath = posts_dir / filename

    front_matter = (
        "---\n"
        f'title: "{title}"\n'
        f"date: {today.isoformat()}\n"
        f'description: "{title}"\n'
        f"lang: {lang}\n"
        "---\n\n"
    )

    filepath.write_text(front_matter + body, encoding="utf-8")
    print(f"保存完了: {filepath.name} (lang: {lang})")
    return filepath


def main() -> None:
    lang = pick_lang()
    print(f"言語: {lang}")

    keyword, slug = pick_unused_topic(lang)
    print(f"テーマ: {keyword}")

    title, body = generate_article(keyword, lang)
    print(f"タイトル: {title}")

    save_post(title, body, slug, lang)


if __name__ == "__main__":
    main()
