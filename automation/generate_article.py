"""
SEOブログ記事 自動生成スクリプト（全言語同時生成）
1トピックを選び、日本語・英語・韓国語・中国語（簡体・繁体）・タガログ語・ベトナム語
の7言語で同時生成し _posts/ に保存する
"""

import re
import random
from datetime import date
from pathlib import Path
import anthropic

REFERRAL_URL = "https://r10.to/henTIE"
REPO_ROOT = Path(__file__).parent.parent

# 1トピック＝1エントリ。slugが一致する記事が既にあればスキップ
TOPICS = [
    {
        "slug": "employee-referral-14000pt",
        "ja": "楽天モバイル 社員紹介キャンペーン 14000ポイント もらい方",
        "en": "Rakuten Mobile employee referral campaign up to 14000 points how to get",
        "ko": "라쿠텐 모바일 직원 소개 14000포인트 받는 방법",
        "zh-cn": "乐天手机员工介绍活动最高14000积分如何获得",
        "zh-tw": "樂天手機員工介紹活動最高14000點數如何獲得",
        "tl": "Rakuten Mobile employee referral 14000 puntos paano makuha",
        "vi": "Rakuten Mobile giới thiệu nhân viên 14000 điểm cách nhận",
    },
    {
        "slug": "referral-vs-normal",
        "ja": "楽天モバイル 社員紹介 通常申込み 違い ポイント比較",
        "en": "Rakuten Mobile employee referral vs normal application points comparison",
        "ko": "라쿠텐 모바일 직원 소개 vs 일반 신청 포인트 비교",
        "zh-cn": "乐天手机员工介绍和普通申请积分对比",
        "zh-tw": "樂天手機員工介紹和一般申請點數比較",
        "tl": "Rakuten Mobile referral link kumpara sa normal na application pagkakaiba",
        "vi": "So sánh Rakuten Mobile giới thiệu nhân viên vs đăng ký thường",
    },
    {
        "slug": "referral-link-how-to",
        "ja": "楽天モバイル 紹介リンク 申込み 手順 わかりやすく",
        "en": "How to apply for Rakuten Mobile via employee referral link step by step",
        "ko": "라쿠텐 모바일 직원 소개 링크로 신청하는 방법 단계별 가이드",
        "zh-cn": "如何通过员工介绍链接申请乐天手机详细步骤",
        "zh-tw": "如何透過員工介紹連結申請樂天手機詳細步驟",
        "tl": "Paano mag-apply sa Rakuten Mobile sa pamamagitan ng referral link hakbang hakbang",
        "vi": "Hướng dẫn đăng ký Rakuten Mobile qua link giới thiệu từng bước chi tiết",
    },
    {
        "slug": "14000-points-usage",
        "ja": "楽天ポイント 14000 使い道 お得な活用法",
        "en": "How to use 14000 Rakuten points best ways for foreign residents in Japan",
        "ko": "라쿠텐 포인트 14000포인트 활용법 재일 외국인",
        "zh-cn": "14000乐天积分怎么用最划算在日华人必看",
        "zh-tw": "14000樂天點數怎麼用最划算在日台灣人必看",
        "tl": "Paano gamitin ang 14000 Rakuten points pinakamabuting paraan",
        "vi": "14000 điểm Rakuten dùng gì tiết kiệm nhất người Việt ở Nhật",
    },
    {
        "slug": "employee-referral-faq",
        "ja": "楽天モバイル 社員紹介 よくある質問 まとめ",
        "en": "Rakuten Mobile employee referral campaign FAQ for foreign residents Japan",
        "ko": "라쿠텐 모바일 직원 소개 캠페인 자주 묻는 질문 모음",
        "zh-cn": "乐天手机员工介绍活动常见问题解答",
        "zh-tw": "樂天手機員工介紹活動常見問題解答",
        "tl": "Rakuten Mobile employee referral campaign mga madalas na tanong",
        "vi": "Rakuten Mobile giới thiệu nhân viên câu hỏi thường gặp",
    },
    {
        "slug": "referral-best-timing",
        "ja": "楽天モバイル 乗り換え 社員紹介 タイミング いつがお得",
        "en": "Best time to switch to Rakuten Mobile using employee referral when is it worth it",
        "ko": "라쿠텐 모바일 번호이동 직원 소개 최적 타이밍 언제가 유리한가",
        "zh-cn": "什么时候通过员工介绍申请乐天手机最合适",
        "zh-tw": "什麼時候透過員工介紹申請樂天手機最合適",
        "tl": "Pinakamainam na panahon para lumipat sa Rakuten Mobile gamit ang referral",
        "vi": "Thời điểm tốt nhất để chuyển sang Rakuten Mobile qua giới thiệu nhân viên",
    },
    {
        "slug": "rakuten-vs-major-carriers",
        "ja": "楽天モバイル ドコモ au ソフトバンク 料金 比較",
        "en": "Rakuten Mobile vs Docomo au Softbank price comparison for foreigners in Japan",
        "ko": "라쿠텐 모바일 도코모 au 소프트뱅크 요금 비교",
        "zh-cn": "乐天手机vs三大运营商价格比较在日外国人必看",
        "zh-tw": "樂天手機vs三大電信費用比較在日外國人必看",
        "tl": "Rakuten Mobile vs Docomo au Softbank paghahambing ng presyo",
        "vi": "So sánh giá cước Rakuten Mobile vs Docomo au Softbank",
    },
    {
        "slug": "rakuten-mnp-guide",
        "ja": "楽天モバイル MNP 乗り換え 手順 わかりやすく",
        "en": "Rakuten Mobile MNP number portability complete guide for foreigners",
        "ko": "라쿠텐 모바일 번호이동 신청 방법 완전 가이드",
        "zh-cn": "乐天手机携号转网完整指南在日外国人",
        "zh-tw": "樂天手機號碼攜入完整指南在日外國人",
        "tl": "Rakuten Mobile MNP numero portability kumpletong gabay",
        "vi": "Hướng dẫn chuyển mạng giữ số sang Rakuten Mobile đầy đủ",
    },
    {
        "slug": "rakuten-family-switch",
        "ja": "楽天モバイル 家族 全員 乗り換え 節約額",
        "en": "Switch whole family to Rakuten Mobile how much can you save",
        "ko": "가족 모두 라쿠텐 모바일로 전환 얼마나 절약할 수 있나",
        "zh-cn": "全家转乐天手机能省多少钱详细计算",
        "zh-tw": "全家轉樂天手機能省多少錢詳細試算",
        "tl": "Ilipat ang buong pamilya sa Rakuten Mobile magkano ang matitipid",
        "vi": "Cả gia đình chuyển sang Rakuten Mobile tiết kiệm được bao nhiêu",
    },
    {
        "slug": "rakuten-ecosystem-maximize",
        "ja": "楽天経済圏 最大化 スマホ 活用術",
        "en": "How to maximize Rakuten ecosystem savings with smartphone in Japan",
        "ko": "라쿠텐 경제권 최대화 스마트폰 활용법",
        "zh-cn": "如何最大化利用乐天经济圈智能手机省钱",
        "zh-tw": "如何最大化利用樂天經濟圈智慧型手機省錢",
        "tl": "Paano i-maximize ang Rakuten ecosystem savings gamit ang smartphone",
        "vi": "Cách tận dụng tối đa hệ sinh thái Rakuten để tiết kiệm tối đa",
    },
    {
        "slug": "rakuten-review-honest",
        "ja": "楽天モバイル 口コミ 評判 実際に使ってみた",
        "en": "Rakuten Mobile honest review from a foreign resident in Japan real experience",
        "ko": "라쿠텐 모바일 솔직한 후기 재일 외국인이 실제로 써봤다",
        "zh-cn": "乐天手机真实评价在日外国人使用体验",
        "zh-tw": "樂天手機真實評價在日外國人使用體驗",
        "tl": "Rakuten Mobile tapat na review mula sa dayuhang nakatira sa Japan",
        "vi": "Đánh giá thật về Rakuten Mobile từ người nước ngoài ở Nhật",
    },
    {
        "slug": "rakuten-point-double",
        "ja": "楽天ポイント スマホ代 節約 二重取り 方法",
        "en": "How to double dip Rakuten points with your smartphone plan save money",
        "ko": "라쿠텐 포인트 스마트폰 요금 이중 획득 절약 방법",
        "zh-cn": "如何双重获得乐天积分手机费用节省方法",
        "zh-tw": "如何雙重獲得樂天點數手機費用節省方法",
        "tl": "Paano mag-double dip ng Rakuten points sa smartphone plan",
        "vi": "Cách kiếm điểm Rakuten gấp đôi từ gói cước điện thoại",
    },
]

LANG_PROMPTS = {
    "ja": """SEOに最適化された日本語ブログ記事をMarkdown形式で作成してください。

メインキーワード: {keyword}
楽天モバイル社員紹介URL: {url}

前提知識:
- 楽天モバイルには社員紹介キャンペーンがある
- 社員紹介リンク経由で申し込むと、MNP（乗り換え）で14,000ポイント、新規申込みで11,000ポイント付与
- 通常キャンペーンはMNP13,000ポイント（社員紹介の方が1,000pt多い）
- 料金は月3,278円（税込）、データ無制限
- ポイントは紹介ログイン月の4ヶ月後から3ヶ月間に分割進呈
- 最大5回線まで対象

要件:
- 最初の行を「title: 記事タイトル」の形式にする
- ## と ### の見出しで構造化する
- 文字数: 1200〜1800字
- 具体的な数字で価値を伝える
- 自然な文章で押しつけがましくない
- 記事の最後のセクションで紹介リンクへ自然に誘導する

出力は記事本文のみ。""",

    "en": """Write an SEO-optimized English blog article in Markdown format.
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

    "ko": """한국어로 SEO에 최적화된 블로그 기사를 Markdown 형식으로 작성하세요.
대상 독자: 라쿠텐 모바일로 전환을 고려하는 재일 한국인.

메인 키워드: {keyword}
라쿠텐 모바일 직원 소개 URL: {url}

주요 사실:
- 라쿠텐 모바일에는 직원 소개 캠페인이 있음
- 소개 링크를 통해 신청하면: MNP(번호이동) 14,000포인트, 신규 신청 11,000포인트
- 일반 캠페인은 MNP 13,000포인트 (직원 소개가 1,000pt 더 많음)
- 월 요금: 3,278엔 (세금 포함), 데이터 무제한
- 포인트는 소개 로그인 월로부터 4개월 후부터 3개월에 걸쳐 지급
- 1인당 최대 5회선까지 대상

요건:
- 첫 번째 줄: "title: 기사 제목" (한국어로)
- ## 및 ### 제목으로 구성
- 분량: 900~1400자
- 구체적인 숫자 포함
- 자연스럽고 강요하지 않는 톤
- 마지막에 자연스럽게 소개 링크로 유도

기사 본문만 출력.""",

    "zh-cn": """用简体中文写一篇SEO优化的博客文章，格式为Markdown。
目标读者：考虑使用乐天手机的在日中国人。

主要关键词: {keyword}
乐天手机员工介绍URL: {url}

主要信息:
- 乐天手机有员工介绍活动
- 通过介绍链接申请：MNP（携号转网）14,000积分，新申请11,000积分
- 普通活动：MNP 13,000积分（员工介绍多1,000积分）
- 月费：3,278日元（含税），无限流量
- 积分从介绍登录月起4个月后开始，分3个月发放
- 每人最多5条号码

要求:
- 第一行："title: 文章标题"（用简体中文）
- 用##和###标题组织结构
- 字数：900-1400字
- 包含具体数字
- 自然、不强迫推销的语气
- 结尾自然引导到介绍链接

只输出文章正文。""",

    "zh-tw": """用繁體中文寫一篇SEO優化的部落格文章，格式為Markdown。
目標讀者：考慮使用樂天手機的在日台灣人。

主要關鍵詞: {keyword}
樂天手機員工介紹URL: {url}

主要資訊:
- 樂天手機有員工介紹活動
- 透過介紹連結申請：MNP（號碼攜入）14,000點數，新申請11,000點數
- 一般活動：MNP 13,000點數（員工介紹多1,000點）
- 月費：3,278日圓（含稅），無限流量
- 點數從介紹登入月起4個月後開始，分3個月發放
- 每人最多5門號

要求:
- 第一行：「title: 文章標題」（用繁體中文）
- 用##和###標題組織結構
- 字數：900-1400字
- 包含具體數字
- 自然、不強迫推銷的語氣
- 結尾自然引導到介紹連結

只輸出文章正文。""",

    "tl": """Write an SEO-optimized blog article in Filipino/Tagalog in Markdown format.
Target audience: Filipino residents in Japan considering Rakuten Mobile.

Main keyword: {keyword}
Rakuten Mobile employee referral URL: {url}

Key facts:
- Rakuten Mobile has an employee referral campaign
- Via referral link: 14,000 points for MNP, 11,000 points for new signup
- Normal campaign: 13,000 points for MNP
- Monthly fee: ¥3,278 (tax included), unlimited data
- Points paid in 3 installments starting 4 months after referral login
- Max 5 lines per person

Requirements:
- First line: "title: Pamagat ng Artikulo" (in Filipino)
- Use ## and ### headings
- Length: 800-1200 words in Filipino/Tagalog
- Include specific point numbers
- Natural, friendly tone
- End with natural referral link guidance

Output article body only.""",

    "vi": """Viết một bài blog SEO tối ưu bằng tiếng Việt theo định dạng Markdown.
Độc giả mục tiêu: Người Việt Nam tại Nhật Bản đang xem xét chuyển sang Rakuten Mobile.

Từ khóa chính: {keyword}
URL giới thiệu nhân viên Rakuten Mobile: {url}

Thông tin chính:
- Rakuten Mobile có chương trình giới thiệu nhân viên
- Qua link giới thiệu: 14,000 điểm cho MNP, 11,000 điểm cho đăng ký mới
- Chiến dịch thông thường: 13,000 điểm cho MNP
- Phí hàng tháng: 3,278 yên (đã bao gồm thuế), data không giới hạn
- Điểm được trả trong 3 đợt bắt đầu từ 4 tháng sau tháng đăng nhập giới thiệu
- Tối đa 5 dòng mỗi người

Yêu cầu:
- Dòng đầu tiên: "title: Tiêu đề bài viết" (bằng tiếng Việt)
- Dùng ## và ### cho tiêu đề
- Độ dài: 800-1200 từ bằng tiếng Việt
- Bao gồm số điểm cụ thể
- Giọng điệu tự nhiên, không ép buộc
- Kết thúc với hướng dẫn tự nhiên đến link giới thiệu

Chỉ xuất nội dung bài viết.""",
}


def pick_unused_topic() -> dict:
    """まだ全言語で記事化していないトピックを選ぶ（日本語版の有無で判断）"""
    posts_dir = REPO_ROOT / "_posts"
    existing_slugs = (
        {p.stem.split("-", 3)[-1] for p in posts_dir.glob("*.md")}
        if posts_dir.exists() else set()
    )
    unused = [t for t in TOPICS if t["slug"] not in existing_slugs]
    if not unused:
        unused = TOPICS
    return random.choice(unused)


def generate_article(keyword: str, lang: str) -> tuple[str, str]:
    """Claude APIで指定言語の記事を生成しタイトルと本文を返す"""
    client = anthropic.Anthropic()
    prompt = LANG_PROMPTS[lang].format(keyword=keyword, url=REFERRAL_URL)

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
    print(f"  保存: {filepath.name}")
    return filepath


def main() -> None:
    topic = pick_unused_topic()
    print(f"トピック: {topic['slug']}")

    for lang in LANG_PROMPTS:
        keyword = topic[lang]
        slug = topic["slug"] if lang == "ja" else f"{lang}-{topic['slug']}"
        print(f"[{lang}] {keyword}")
        title, body = generate_article(keyword, lang)
        save_post(title, body, slug, lang)

    print(f"\n完了: 7言語 × トピック「{topic['slug']}」")


if __name__ == "__main__":
    main()
