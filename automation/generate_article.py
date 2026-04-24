"""
SEOブログ記事 自動生成スクリプト（全言語同時生成）
1トピックを選び、日本語・英語・韓国語・中国語（簡体・繁体）・タガログ語・ベトナム語
の7言語で同時生成し _posts/ に保存する
"""

import re
import json
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
    {
        "slug": "rakuten-esim-setup",
        "ja": "楽天モバイル eSIM 設定方法 メリット デメリット",
        "en": "Rakuten Mobile eSIM setup guide pros cons for foreign residents",
        "ko": "라쿠텐 모바일 eSIM 설정 방법 장단점 완전 가이드",
        "zh-cn": "乐天手机eSIM设置方法优缺点完整指南",
        "zh-tw": "樂天手機eSIM設定方法優缺點完整指南",
        "tl": "Rakuten Mobile eSIM setup gabay para sa mga dayuhan sa Japan",
        "vi": "Hướng dẫn cài đặt eSIM Rakuten Mobile ưu nhược điểm",
    },
    {
        "slug": "rakuten-link-app-guide",
        "ja": "Rakuten Link アプリ 使い方 無料通話 活用術",
        "en": "Rakuten Link app complete guide free calls for foreigners in Japan",
        "ko": "Rakuten Link 앱 사용법 무료 통화 완전 활용 가이드",
        "zh-cn": "Rakuten Link应用使用指南免费通话完整教程",
        "zh-tw": "Rakuten Link應用使用指南免費通話完整教學",
        "tl": "Rakuten Link app gabay libreng tawag para sa mga dayuhan",
        "vi": "Hướng dẫn sử dụng ứng dụng Rakuten Link gọi miễn phí",
    },
    {
        "slug": "docomo-to-rakuten-guide",
        "ja": "ドコモから楽天モバイル 乗り換え 手順 注意点",
        "en": "How to switch from Docomo to Rakuten Mobile complete guide",
        "ko": "도코모에서 라쿠텐 모바일로 번호이동 방법 주의점",
        "zh-cn": "从docomo转到乐天手机详细步骤注意事项",
        "zh-tw": "從docomo轉到樂天手機詳細步驟注意事項",
        "tl": "Paano lumipat mula Docomo papunta Rakuten Mobile hakbang hakbang",
        "vi": "Hướng dẫn chuyển từ Docomo sang Rakuten Mobile chi tiết",
    },
    {
        "slug": "au-to-rakuten-guide",
        "ja": "auから楽天モバイル 乗り換え 手順 SIMロック解除",
        "en": "How to switch from au to Rakuten Mobile SIM unlock guide",
        "ko": "au에서 라쿠텐 모바일로 번호이동 심락 해제 방법",
        "zh-cn": "从au转到乐天手机步骤SIM锁解除方法",
        "zh-tw": "從au轉到樂天手機步驟SIM鎖解除方法",
        "tl": "Paano lumipat mula au papunta Rakuten Mobile SIM unlock",
        "vi": "Hướng dẫn chuyển từ au sang Rakuten Mobile mở khóa SIM",
    },
    {
        "slug": "softbank-to-rakuten-guide",
        "ja": "ソフトバンクから楽天モバイル 乗り換え メリット デメリット",
        "en": "Switching from SoftBank to Rakuten Mobile pros cons guide",
        "ko": "소프트뱅크에서 라쿠텐 모바일로 전환 장단점 가이드",
        "zh-cn": "从软银转到乐天手机优缺点完整指南",
        "zh-tw": "從軟銀轉到樂天手機優缺點完整指南",
        "tl": "Paglipat mula SoftBank papunta Rakuten Mobile kalamangan kahinaan",
        "vi": "Chuyển từ SoftBank sang Rakuten Mobile ưu nhược điểm",
    },
    {
        "slug": "rakuten-overseas-roaming",
        "ja": "楽天モバイル 海外ローミング 使い方 無料2GB 活用法",
        "en": "Rakuten Mobile overseas roaming free 2GB how to use abroad",
        "ko": "라쿠텐 모바일 해외 로밍 무료 2GB 사용 방법",
        "zh-cn": "乐天手机海外漫游免费2GB使用方法",
        "zh-tw": "樂天手機海外漫遊免費2GB使用方法",
        "tl": "Rakuten Mobile overseas roaming libreng 2GB paano gamitin",
        "vi": "Rakuten Mobile roaming quốc tế miễn phí 2GB cách sử dụng",
    },
    {
        "slug": "foreign-residents-sim-guide",
        "ja": "在日外国人 スマホ SIM 選び方 楽天モバイルが最適な理由",
        "en": "Best SIM card for foreigners living in Japan why Rakuten Mobile",
        "ko": "재일 외국인을 위한 최고의 SIM 선택 가이드 라쿠텐 모바일 추천",
        "zh-cn": "在日外国人最佳SIM卡选择指南为什么选乐天手机",
        "zh-tw": "在日外國人最佳SIM卡選擇指南為什麼選樂天手機",
        "tl": "Pinakamainam na SIM para sa mga dayuhan sa Japan bakit Rakuten Mobile",
        "vi": "SIM tốt nhất cho người nước ngoài ở Nhật lý do chọn Rakuten Mobile",
    },
    {
        "slug": "iphone-rakuten-setup",
        "ja": "iPhone 楽天モバイル 設定方法 APN eSIM 対応",
        "en": "iPhone Rakuten Mobile setup guide APN eSIM configuration",
        "ko": "아이폰 라쿠텐 모바일 설정 방법 APN eSIM 완전 가이드",
        "zh-cn": "iPhone乐天手机设置方法APN eSIM完整配置",
        "zh-tw": "iPhone樂天手機設定方法APN eSIM完整配置",
        "tl": "iPhone Rakuten Mobile setup gabay APN eSIM configuration",
        "vi": "Cài đặt Rakuten Mobile trên iPhone hướng dẫn APN eSIM",
    },
    {
        "slug": "rakuten-student-benefits",
        "ja": "楽天モバイル 学生 メリット 節約 ポイント活用",
        "en": "Rakuten Mobile benefits for students in Japan save on phone bills",
        "ko": "라쿠텐 모바일 학생 혜택 절약 포인트 활용법",
        "zh-cn": "乐天手机对学生的好处省钱积分活用",
        "zh-tw": "樂天手機對學生的好處省錢積分活用",
        "tl": "Mga benepisyo ng Rakuten Mobile para sa mga estudyante sa Japan",
        "vi": "Lợi ích của Rakuten Mobile cho sinh viên tại Nhật tiết kiệm cước",
    },
    {
        "slug": "rakuten-wifi-router",
        "ja": "楽天モバイル Rakuten Turbo Wi-Fiルーター 自宅回線 節約",
        "en": "Rakuten Turbo home Wi-Fi router replace home broadband save money",
        "ko": "라쿠텐 터보 가정용 Wi-Fi 라우터 인터넷 대체 절약",
        "zh-cn": "乐天Turbo家用Wi-Fi路由器替代宽带省钱",
        "zh-tw": "樂天Turbo家用Wi-Fi路由器替代寬頻省錢",
        "tl": "Rakuten Turbo home Wi-Fi palitan ang broadband para makatipid",
        "vi": "Rakuten Turbo bộ phát Wi-Fi gia đình thay thế cáp quang tiết kiệm",
    },
    {
        "slug": "rakuten-point-smart-usage",
        "ja": "楽天ポイント 賢い使い方 期間限定ポイント 失効しない方法",
        "en": "Smart ways to use Rakuten points avoid expiry limited period points",
        "ko": "라쿠텐 포인트 현명한 사용법 기간한정 포인트 소멸 방지",
        "zh-cn": "楽天积分聪明使用方法防止限期积分失效",
        "zh-tw": "樂天點數聰明使用方法防止限期點數失效",
        "tl": "Matalinong paraan ng paggamit ng Rakuten points limitadong panahon",
        "vi": "Cách sử dụng điểm Rakuten thông minh tránh mất điểm có hạn",
    },
    {
        "slug": "rakuten-recontract-referral",
        "ja": "楽天モバイル 再契約 社員紹介 ポイント もらえる 条件",
        "en": "Rakuten Mobile re-contract employee referral points eligible conditions",
        "ko": "라쿠텐 모바일 재계약 직원 소개 포인트 받을 수 있는 조건",
        "zh-cn": "乐天手机重新签约通过员工介绍获得积分的条件",
        "zh-tw": "樂天手機重新簽約透過員工介紹獲得點數條件",
        "tl": "Rakuten Mobile muling pag-sign up referral ng empleyado kondisyon ng puntos",
        "vi": "Rakuten Mobile tái ký hợp đồng qua giới thiệu nhân viên điều kiện nhận điểm",
    },
    {
        "slug": "rakuten-link-10sec-call",
        "ja": "Rakuten Link 10秒通話 社員紹介 ポイント 受け取り条件 やり方",
        "en": "Rakuten Link 10 second call requirement for employee referral points how to do it",
        "ko": "Rakuten Link 10초 통화 직원 소개 포인트 수령 조건 방법",
        "zh-cn": "Rakuten Link通话10秒员工介绍积分领取条件方法",
        "zh-tw": "Rakuten Link通話10秒員工介紹點數領取條件方法",
        "tl": "Rakuten Link 10 segundo na tawag kondisyon para sa referral points paano gawin",
        "vi": "Rakuten Link gọi 10 giây điều kiện nhận điểm giới thiệu nhân viên cách thực hiện",
    },
    {
        "slug": "rakuten-second-line-referral",
        "ja": "楽天モバイル 2回線目 社員紹介 ポイント 申込み 方法",
        "en": "Rakuten Mobile second line employee referral how to get points for additional lines",
        "ko": "라쿠텐 모바일 2번째 회선 직원 소개 포인트 신청 방법",
        "zh-cn": "乐天手机第二条线通过员工介绍获得积分申请方法",
        "zh-tw": "樂天手機第二條線透過員工介紹獲得點數申請方法",
        "tl": "Rakuten Mobile ikalawang linya referral ng empleyado paano makakuha ng puntos",
        "vi": "Rakuten Mobile đường dây thứ hai qua giới thiệu nhân viên cách nhận điểm",
    },
    {
        "slug": "referral-store-apply",
        "ja": "楽天モバイル 社員紹介 店舗申込み 方法 Web以外でも対象",
        "en": "Rakuten Mobile employee referral in-store application how to apply at shop",
        "ko": "라쿠텐 모바일 직원 소개 매장 신청 방법 웹 이외도 대상",
        "zh-cn": "乐天手机员工介绍门店申请方法线上线下均可",
        "zh-tw": "樂天手機員工介紹門市申請方法線上線下均可",
        "tl": "Rakuten Mobile employee referral mag-apply sa tindahan pati online",
        "vi": "Rakuten Mobile giới thiệu nhân viên đăng ký tại cửa hàng hay online đều được",
    },
    {
        "slug": "referral-data-sim-eligible",
        "ja": "楽天モバイル 社員紹介 データSIM 対象 通常キャンペーンとの違い",
        "en": "Rakuten Mobile employee referral data SIM eligible difference from normal campaign",
        "ko": "라쿠텐 모바일 직원 소개 데이터 SIM 대상 일반 캠페인과 차이",
        "zh-cn": "乐天手机员工介绍数据SIM也对象与普通活动的区别",
        "zh-tw": "樂天手機員工介紹數據SIM也對象與一般活動的差別",
        "tl": "Rakuten Mobile referral data SIM kasama pagkakaiba sa normal na campaign",
        "vi": "Rakuten Mobile giới thiệu nhân viên data SIM cũng được khác gì campaign thường",
    },
    {
        "slug": "rakuten-reputation-honest",
        "ja": "楽天モバイル 評判 口コミ メリット デメリット 正直レビュー",
        "en": "Rakuten Mobile reputation reviews pros and cons honest 2026",
        "ko": "라쿠텐 모바일 평판 리뷰 장단점 솔직한 후기 2026",
        "zh-cn": "乐天手机口碑评价优缺点真实用户评测2026",
        "zh-tw": "樂天手機口碑評價優缺點真實用戶評測2026",
        "tl": "Rakuten Mobile reputasyon review pros cons 2026",
        "vi": "Đánh giá Rakuten Mobile ưu nhược điểm thực tế 2026",
    },
    {
        "slug": "rakuten-demerits-solutions",
        "ja": "楽天モバイル デメリット 弱点 対処法 つながりにくい エリア",
        "en": "Rakuten Mobile disadvantages weak points solutions coverage issues 2026",
        "ko": "라쿠텐 모바일 단점 약점 해결법 통화 연결 문제 2026",
        "zh-cn": "乐天手机缺点弱点及解决方法信号覆盖问题2026",
        "zh-tw": "樂天手機缺點弱點及解決方法訊號覆蓋問題2026",
        "tl": "Rakuten Mobile disadvantages weak points solusyon coverage 2026",
        "vi": "Nhược điểm của Rakuten Mobile và cách khắc phục vùng phủ sóng 2026",
    },
    {
        "slug": "rakuten-application-documents",
        "ja": "楽天モバイル 申込み 必要書類 手続き 流れ 完全ガイド",
        "en": "Rakuten Mobile application required documents procedure complete guide 2026",
        "ko": "라쿠텐 모바일 신청 필요 서류 절차 완전 가이드 2026",
        "zh-cn": "乐天手机申请所需材料手续流程完整指南2026",
        "zh-tw": "樂天手機申請所需文件手續流程完整指南2026",
        "tl": "Rakuten Mobile application mga kinakailangang dokumento proseso 2026",
        "vi": "Đăng ký Rakuten Mobile giấy tờ cần thiết quy trình đầy đủ 2026",
    },
    {
        "slug": "rakuten-signal-troubleshoot",
        "ja": "楽天モバイル つながらない 圏外 解決法 エリア確認",
        "en": "Rakuten Mobile no signal connection issues troubleshooting coverage check 2026",
        "ko": "라쿠텐 모바일 연결 안됨 전파 음영 해결법 커버리지 확인 2026",
        "zh-cn": "乐天手机没有信号连接问题解决方法覆盖区域确认2026",
        "zh-tw": "樂天手機沒有訊號連線問題解決方法覆蓋區域確認2026",
        "tl": "Rakuten Mobile walang signal problema solusyon coverage check 2026",
        "vi": "Rakuten Mobile mất sóng vấn đề kết nối cách khắc phục kiểm tra vùng phủ 2026",
    },
    {
        "slug": "rakuten-unext-referral",
        "ja": "楽天最強U-NEXT 社員紹介 ポイント キャンペーン 申込み",
        "en": "Rakuten Saikyou U-NEXT employee referral points campaign how to apply",
        "ko": "라쿠텐 최강 U-NEXT 직원 소개 포인트 캠페인 신청 방법",
        "zh-cn": "乐天最强U-NEXT员工介绍积分活动申请方法",
        "zh-tw": "樂天最強U-NEXT員工介紹點數活動申請方法",
        "tl": "Rakuten Saikyou U-NEXT employee referral points campaign paano mag-apply",
        "vi": "Rakuten Saikyou U-NEXT giới thiệu nhân viên điểm thưởng cách đăng ký",
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
- 最初の行を「title: 記事タイトル」の形式にする（タイトルには必ず「【2026年版】」を含める）
- ## と ### の見出しで構造化する
- 文字数: 2500〜3500字
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
- First line: "title: Article Title" (in English, must include "[2026 Guide]" or "[Updated 2026]")
- Use ## and ### headings for structure
- Length: 1500-2200 words
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
- 첫 번째 줄: "title: 기사 제목" (한국어로, 반드시 「【2026년판】」 포함)
- ## 및 ### 제목으로 구성
- 분량: 1500~2200자
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
- 第一行："title: 文章标题"（用简体中文，必须包含「【2026年版】」）
- 用##和###标题组织结构
- 字数：1500-2200字
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
- 第一行：「title: 文章標題」（用繁體中文，必須包含「【2026年版】」）
- 用##和###標題組織結構
- 字數：1500-2200字
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
- First line: "title: Pamagat ng Artikulo" (in Filipino, must include "[2026 Guide]")
- Use ## and ### headings
- Length: 1200-1800 words in Filipino/Tagalog
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
- Dòng đầu tiên: "title: Tiêu đề bài viết" (bằng tiếng Việt, phải có "[Cập nhật 2026]")
- Dùng ## và ### cho tiêu đề
- Độ dài: 1200-1800 từ bằng tiếng Việt
- Bao gồm số điểm cụ thể
- Giọng điệu tự nhiên, không ép buộc
- Kết thúc với hướng dẫn tự nhiên đến link giới thiệu

Chỉ xuất nội dung bài viết.""",
}


def get_recent_articles(lang: str = "ja", count: int = 5) -> list[dict]:
    """内部リンク生成用に直近の記事一覧を取得"""
    posts_dir = REPO_ROOT / "_posts"
    if not posts_dir.exists():
        return []
    results = []
    for p in sorted(posts_dir.glob("*.md"), reverse=True):
        stem = p.stem
        slug_part = stem.split("-", 3)[-1]
        if lang == "ja":
            if re.match(r"^(en|ko|zh-cn|zh-tw|tl|vi)-", slug_part):
                continue
        else:
            if not slug_part.startswith(f"{lang}-"):
                continue
        text = p.read_text(encoding="utf-8")
        title_match = re.search(r'^title:\s*"?(.+?)"?\s*$', text, re.MULTILINE)
        title = title_match.group(1) if title_match else slug_part
        parts = stem.split("-", 3)
        url = f"https://mobile-friend.com/{parts[0]}/{parts[1]}/{parts[2]}/{parts[3]}.html"
        results.append({"title": title, "url": url})
        if len(results) >= count:
            break
    return results


def _get_existing_slugs() -> set[str]:
    """_posts/ 内の既存記事スラグ一覧を返す"""
    posts_dir = REPO_ROOT / "_posts"
    if not posts_dir.exists():
        return set()
    return {p.stem.split("-", 3)[-1] for p in posts_dir.glob("*.md")}


def load_seo_topics() -> list[dict]:
    """seo_reports/seo_topics.json から未使用のSEO推奨トピックを返す"""
    topics_file = REPO_ROOT / "seo_reports" / "seo_topics.json"
    if not topics_file.exists():
        return []
    try:
        data = json.loads(topics_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    existing_slugs = _get_existing_slugs()
    # used_slugs（手動管理）と既存記事の両方でフィルタ
    used = set(data.get("used_slugs", [])) | existing_slugs
    return [t for t in data.get("topics", []) if t["slug"] not in used]


def seo_topic_to_full_topic(seo_t: dict) -> dict:
    """SEO推奨トピック（ja_keyword + slug）を全言語トピックdictに変換"""
    kw = seo_t["ja_keyword"]
    slug = seo_t["slug"]
    en_hint = slug.replace("-", " ")
    return {
        "slug": slug,
        "ja": kw,
        "en": f"Rakuten Mobile {en_hint} complete guide for foreigners in Japan",
        "ko": f"라쿠텐 모바일 {en_hint} 완전 가이드 재일 외국인",
        "zh-cn": f"乐天手机 {en_hint} 完整指南在日外国人必看",
        "zh-tw": f"樂天手機 {en_hint} 完整指南在日外國人必看",
        "tl": f"Rakuten Mobile {en_hint} kumpletong gabay para sa mga dayuhan sa Japan",
        "vi": f"Rakuten Mobile {en_hint} hướng dẫn đầy đủ cho người nước ngoài ở Nhật",
        "_from_seo_report": True,
    }


def pick_unused_topic() -> dict:
    """まだ記事化していないトピックを選ぶ。SEOレポート推奨トピックを優先"""
    # SEOレポートの推奨トピックを最優先
    seo_topics = load_seo_topics()
    if seo_topics:
        chosen = seo_topics[0]  # リスト先頭（レポート記載順）を使う
        print(f"📊 SEOレポート推奨トピックを使用: {chosen['ja_keyword']}")
        return seo_topic_to_full_topic(chosen)

    # フォールバック: 固定TOPICSリスト
    existing_slugs = _get_existing_slugs()
    unused = [t for t in TOPICS if t["slug"] not in existing_slugs]
    if not unused:
        unused = TOPICS
    return random.choice(unused)


def build_internal_links_note(lang: str) -> str:
    """直近記事リストを内部リンク誘導用テキストに変換"""
    articles = get_recent_articles(lang, count=5)
    if not articles:
        return ""
    lines = "\n".join(f"- [{a['title']}]({a['url']})" for a in articles)
    notes = {
        "ja": f"\n\n関連する既存記事（記事内に自然なMarkdownリンクを1〜2箇所挿入してください）:\n{lines}",
        "en": f"\n\nExisting related articles (naturally insert 1-2 Markdown links in the article body):\n{lines}",
        "ko": f"\n\n기존 관련 기사 (본문에 자연스럽게 1~2개의 Markdown 링크를 삽입하세요):\n{lines}",
        "zh-cn": f"\n\n现有相关文章（在正文中自然插入1-2个Markdown链接）：\n{lines}",
        "zh-tw": f"\n\n現有相關文章（在正文中自然插入1-2個Markdown連結）：\n{lines}",
        "tl": f"\n\nMga kasalukuyang kaugnay na artikulo (natural na maglagay ng 1-2 Markdown link sa katawan):\n{lines}",
        "vi": f"\n\nCác bài viết liên quan hiện có (chèn tự nhiên 1-2 link Markdown trong bài):\n{lines}",
    }
    return notes.get(lang, "")


def generate_article(keyword: str, lang: str) -> tuple[str, str]:
    """Claude APIで指定言語の記事を生成しタイトルと本文を返す"""
    client = anthropic.Anthropic()
    internal_links_note = build_internal_links_note(lang)
    prompt = LANG_PROMPTS[lang].format(keyword=keyword, url=REFERRAL_URL) + internal_links_note

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    content = message.content[0].text.strip()
    title_match = re.match(r"title:\s*(.+)", content)
    title = title_match.group(1).strip().strip('"') if title_match else keyword
    body = re.sub(r"^title:.+\n+", "", content).strip()
    return title, body


def save_post(title: str, body: str, slug: str, lang: str, post_date: date = None, base_slug: str = None) -> Path:
    today = post_date or date.today()
    filename = f"{today.strftime('%Y-%m-%d')}-{slug}.md"
    posts_dir = REPO_ROOT / "_posts"
    posts_dir.mkdir(exist_ok=True)
    filepath = posts_dir / filename

    # OGP画像は全言語で日本語版のベーススラッグ共通画像を使用
    ogp_base = base_slug or slug
    ogp_image = f"/assets/ogp/{today.strftime('%Y-%m-%d')}-{ogp_base}.png"

    front_matter = (
        "---\n"
        f'title: "{title}"\n'
        f"date: {today.isoformat()}\n"
        f'description: "{title}"\n'
        f"lang: {lang}\n"
        f"ogp_image: {ogp_image}\n"
        "---\n\n"
    )
    filepath.write_text(front_matter + body, encoding="utf-8")
    print(f"  保存: {filepath.name}")
    return filepath


def main() -> None:
    import sys
    post_date = None
    for arg in sys.argv[1:]:
        if arg.startswith("--date="):
            post_date = date.fromisoformat(arg.split("=", 1)[1])
            print(f"指定日付: {post_date}")

    topic = pick_unused_topic()
    from_seo_report = topic.pop("_from_seo_report", False)
    print(f"トピック: {topic['slug']} {'[SEOレポート推奨]' if from_seo_report else '[固定リスト]'}")

    for lang in LANG_PROMPTS:
        keyword = topic[lang]
        slug = topic["slug"] if lang == "ja" else f"{lang}-{topic['slug']}"
        print(f"[{lang}] {keyword}")
        title, body = generate_article(keyword, lang)
        save_post(title, body, slug, lang, post_date, base_slug=topic["slug"])

    print(f"\n完了: 7言語 × トピック「{topic['slug']}」")


if __name__ == "__main__":
    main()
