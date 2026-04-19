"""
Threads投稿スケジュールCSV生成スクリプト（SocialDog形式）

記事生成後に実行し、2週間分の投稿スケジュールを生成する。
- 当日生成されたブログ記事の紹介投稿（週1〜2回差し込み）
- 日常系カジュアル投稿（1日5回ペース）
"""

import csv
import random
from datetime import date, datetime, timedelta
from pathlib import Path
import re

REPO_ROOT = Path(__file__).parent.parent
SITE_URL = "https://mobile-friend.com"
OUTPUT_CSV = REPO_ROOT / "assets" / "posts.csv"
SCHEDULE_DAYS = 14  # 何日分生成するか（月・木生成なら2週間でちょうどよい）

# 1日あたりの投稿時刻（hour, minute_base） ランダムに±15分ずらす
DAILY_TIMES = [
    (7, 30),
    (12, 20),
    (15, 45),
    (19, 10),
    (22, 0),
]

# ─────────────────────────────────────────────
# 日常系カジュアル投稿プール（80件）
# ─────────────────────────────────────────────
CASUAL_POSTS = [
    # 食事・グルメ
    "ランチにパスタ食べてきた🍝 クリームソースが濃厚で幸せ。午後の仕事の活力もらいました",
    "今日のランチは会社近くの定食屋さん🐟 鯖の塩焼き定食850円でこのボリューム、コスパ最強すぎる",
    "今日の夜ごはん、豚の生姜焼き。自分で言うけど今日のはかなりうまくできた🎉",
    "近所の中華料理屋の麻婆豆腐が辛くておいしすぎた🌶️ 辛いの苦手なはずなのに気づいたら全部食べてた",
    "今日は外食。パスタとサラダと白ワインで贅沢なディナー🍷 たまにはいいよね",
    "社食カレー。毎回食べてるけど毎回おいしい。社食のカレーって不思議な魅力がある🍛",
    "夜、急に唐揚げが食べたくなって作ってしまった。衣サクサクで大満足🍗 明日のお弁当にも入れよう",
    "今日はお弁当持参の日！昨夜作った鶏の照り焼きと卵焼きを詰めた🍱 自分で作ったやつが一番おいしい",
    "コンビニランチ。最近のコンビニのサラダって種類豊富すぎて毎回迷う。今日はシーザーサラダとおにぎり2個",
    "退勤後にスーパー寄って食材買い出し。今日は豚の生姜焼きにしようと決めてたのに鶏肉が安くて迷った🥩",
    "週末に料理の作り置きをした🍳 週の前半はこれで乗り切れる予定。頑張った自分",
    "朝ごはん、昨日の残りご飯でたまごかけごはんにした。シンプルだけどこれが一番落ち着く",
    "ラーメン屋さん、ずっと気になってたところに行ってきた🍜 濃厚スープがしみた。また行く",
    "友達とご飯行って3時間くらいしゃべりっぱなしだった。直接会うのが一番楽しいって毎回思う",
    "今日のランチ後に同僚と苺のタルト食べてきた🍓 季節限定って言われると食べないわけにいかない",
    "お風呂上がりのアイスクリームが最近の楽しみ🍦 罪悪感はあるけど毎日食べちゃう",
    "今日の仕事終わりに同期と焼き鳥🍢 全然関係ない話で盛り上がりながら飲むビールが最高だった",
    "スーパーで旬の野菜を買い込んだ。八百屋みたいな量になってるけど全部使い切る気でいる🥦",
    "近所に新しいタイ料理屋ができてたので行ってみた。グリーンカレーがばちばちに辛くておいしかった🌿",
    "お昼に会社の近くで新しいランチスポット発見。ハンバーグ定食が800円でボリューム満点だった🍖",

    # コーヒー・カフェ
    "今日も朝コーヒーからスタート☕ 最近コンビニのカフェラテにハマってるんだけど、じわじわおいしくなってる気がする",
    "3時のコーヒーが一日で一番おいしい説。疲れをちょうどよくリセットしてくれる感じがする☕",
    "ランチ後に同期と近くのカフェでコーヒー休憩☕ この時間が一番のリフレッシュになってる",
    "ちょっと早めに家を出てお気に入りのカフェでモーニング☕ こういう余裕のある朝がしたい",
    "今日は友達とカフェ巡り☕ 3軒ハシゴしたけど全部当たりだった。インスタ映えより味重視派",
    "新しいコーヒー豆を買ってみた。フルーティーで酸味が爽やかで朝から気分が上がる☕",
    "在宅の日のコーヒーはドリップで丁寧に淹れる。この5分が一日の中で一番豊かな時間かもしれない",

    # 運動・健康
    "ジムでひたすら走ってきた。30分で3km、少しずつ距離が伸びてる。継続は力なり💪",
    "6時に起きて朝ランしてきた。桜並木を走るのが気持ちよすぎて早起きが苦じゃなくなってきた🌸",
    "休日ランニング、平日より距離が伸ばせた！5km達成。ご褒美に好きなスイーツ食べた🏃‍♀️",
    "夜ヨガをやってみた。終わったあと体が軽くてびっくり。これは続けてみようかも🧘‍♀️",
    "最近ストレッチを毎朝やるようにしたら肩こりがかなり改善された。継続大事だなとしみじみ",
    "朝活で近所の公園をウォーキング。鳥の声と新緑がすごくよくて、なんか一日のテンションが上がった🌿",
    "筋トレ始めて3ヶ月。最初は腕立て5回もキツかったのに今は20回できるようになった。地味に嬉しい💪",
    "週末に近所の公園で縄跳びしてきた。子どもの頃ぶりにやったけど全然続かなくて笑えた🪢",

    # 自然・季節
    "お花見してきた！！桜がちょうど満開で最高だった🌸 来年もここで見たい",
    "通勤路の桜並木、今年も綺麗だった🌸 毎年この道を歩けることが地味に嬉しい",
    "帰り道に夕焼けがきれいすぎてしばらく立ち止まってしまった。写真に撮っても全然伝わらないやつ",
    "5月になって緑が一気に鮮やかになってきた。この季節の東京ってほんとに好き🌳",
    "仕事の合間にちょっと外の空気吸いに行ったら青空がきれいすぎた。もうちょっと頑張れる気がしてくる☀️",
    "今日の空が雲ひとつなくて気持ちよかった。こういう日って何かいいことある気がする☀️",
    "雨の日の窓際って妙に落ち着く。コーヒーとお気に入りの本があれば最強の休日☔",
    "週末に散歩してたら知らない路地においしそうなパン屋さんを発見した🍞 こういう発見が散歩の醍醐味",

    # 仕事・日常
    "今朝寝坊してギリギリだったけど間に合った。自分を褒めたい。電車の中でまだ心臓バクバクしてる",
    "今日のMTGが思ったより早く終わった。溜まってたタスクを消化できそうで少し気持ちが軽くなった",
    "今週も頑張った〜！金曜の夜のこの解放感、毎週何度味わっても最高。お疲れ自分🎉",
    "月曜の朝の電車って独特の重さがあるよね。みんな同じ顔してる気がして少し笑えてくる",
    "在宅ワークの日は通勤ない分、朝の時間の使い方が全然変わる。これに慣れるとオフィスがつらくなるやつ",
    "今日は仕事で小さいけど目標達成できた。こういう積み重ねが大事だよね。明日も頑張ろ",
    "ゴールデンウィーク明け、なんとか会社行けた。自分を褒めたい。同じ気持ちの人いる？",
    "15時のおやつタイム。同僚の差し入れのどら焼きがうますぎた。こういう日は仕事もはかどる",
    "残業続きの今週もなんとか乗り越えた。週末は完全オフにするって決めた。えらい自分",
    "リモートワークで気づいたらずっと座ってた。1時間に1回立つって決めたのに全然できてない",

    # 趣味・娯楽
    "読み始めた本がおもしろすぎて気づいたら1時になってた。明日眠いのわかってるのにやめられない📚",
    "映画館でずっと気になってた映画を観てきた🎬 久しぶりに映画でこんなに泣いた",
    "休日のんびりNetflix。気づいたら3時間経ってた。これが幸せってやつだよね🛋️",
    "ドラマ見ながら晩酌🍺 このゆるい時間が一番好きかもしれない。今日も一日お疲れ",
    "明日早いのに全然眠れない。こういう夜に限ってスマホを無限に見てしまうやつ🌙",
    "GWの計画を立ててる。どこか旅行行きたいな〜。国内か海外かでまだ悩んでる✈️",
    "週末に実家に帰ったら急にゲームしたくなって、昔のゲーム引っ張り出してきた。夢中になりすぎた🎮",
    "最近Podcastにハマってる。通勤中に聴いてるだけで勉強できてる気がして少し得した感じ🎧",

    # ショッピング・買い物
    "楽天スーパーセールはじまってる！欲しかったもの全部まとめてポイントで還元しながら買えるのは楽天の強みだよね💰",
    "楽天お買い物マラソン中だから買いたかったもの全部まとめて注文した。届くのが楽しみ📦",
    "楽天市場で調理器具を探してたら欲しかったやつがセール価格だった。ポイントもつくしこれは買いでしょ🛒",
    "コンビニの新商品、全部試したくなってしまう。今日はチョコ系のお菓子を3つも買ってしまった🍫",
    "靴を新調した。久しぶりに買い替えたら足が軽くなった気がする。いいものを長く使うのが好き👟",
    "文房具屋に入ったら気づいたら30分経ってた。ペンとかノートとか見てるだけで楽しい✏️",

    # 実家・人間関係
    "実家に帰省。お母さんのご飯が世界一おいしいのは不変の事実🏠",
    "友達と久しぶりに連絡とったら急に会うことになった。こういう流れ、好き",
    "今日は一人でのんびり過ごした。たまには誰とも話さない日があってもいい。充電完了✨",
    "後輩に頼られる機会が増えてきた。自分も最初はそうだったなと思うと、なんか感慨深い",

    # その他日常
    "GW初日！溜まってた家の掃除をして一気にスッキリした。部屋が綺麗だと心も軽い✨",
    "休日の朝はゆっくり起きてブランチ🥞 平日にはできない贅沢な時間。これが週末の醍醐味",
    "日曜の夜ってなんであんなに時間が経つの早いんだろう。気づいたらもう22時でびっくりする",
    "最近早起きを習慣にしようとしてる。今日は5時半に起きれた。朝の静かな時間って貴重",
    "引越しして半年、ようやく部屋が自分の空間って感じになってきた。インテリア楽しい🏠",
    "手帳を書くのが最近の習慣になってる。ただの日記だけど、振り返ると気づきがある📓",
]

# 記事紹介テンプレート（{title}と{url}を置換）
ARTICLE_TEMPLATES = [
    "新しいブログ記事を書きました✍️\n「{title}」\n楽天モバイルへの乗り換えを検討してる方にぜひ読んでもらいたい内容です👇\n{url}",
    "ブログ更新しました📝\n{title}\n\n社員紹介リンク経由で申し込むとMNPで14,000ptもらえるキャンペーンについてまとめてます。気になる方はこちら👇\n{url}",
    "スマホ代の節約を考えてる方へ。楽天モバイルに乗り換えると月3,278円で使い放題、さらに社員紹介でボーナスポイントも🎁\n詳しくはブログにまとめたので読んでみてください👇\n{url}",
    "【ブログ更新】{title}\n\n実際に使ってみてわかったこととか、ポイントのもらい方とかをまとめました。参考になれば嬉しいです😊\n{url}",
    "楽天モバイルの社員紹介、通常キャンペーンより1,000ptお得なの知ってた？ブログにまとめたので気になる方はどうぞ📖\n{url}",
]


def get_todays_ja_posts(lookback_days: int = 7) -> list[dict]:
    """直近 lookback_days 日以内に生成された日本語記事（langプレフィックスなし）を取得"""
    posts_dir = REPO_ROOT / "_posts"
    if not posts_dir.exists():
        return []
    cutoff = date.today() - timedelta(days=lookback_days - 1)
    results = []
    for p in sorted(posts_dir.glob("*.md")):
        # 英語・韓国語等はスキップ（ja以外のlangプレフィックスが含まれるファイル）
        stem = p.stem  # e.g. "2026-04-18-employee-referral-14000pt"
        # ファイル名から日付を取得してカットオフ判定
        try:
            post_date = date.fromisoformat(stem[:10])
        except ValueError:
            continue
        if post_date < cutoff:
            continue
        slug_part = stem.split("-", 3)[-1]  # e.g. "employee-referral-14000pt"
        # 言語コードで始まるものをスキップ（en-, ko-, zh-cn-, zh-tw-, tl-, vi-）
        if re.match(r"^(en|ko|zh-cn|zh-tw|tl|vi)-", slug_part):
            continue
        # タイトルを front matter から取得
        text = p.read_text(encoding="utf-8")
        title_match = re.search(r'^title:\s*"?(.+?)"?\s*$', text, re.MULTILINE)
        title = title_match.group(1) if title_match else slug_part
        # URL 構築: /YYYY/MM/DD/slug/
        parts = stem.split("-", 3)
        url = f"{SITE_URL}/{parts[0]}/{parts[1]}/{parts[2]}/{parts[3]}/"
        # OGP画像パス (assets/ogp/ にあれば添付)
        ogp_path = REPO_ROOT / "assets" / "ogp" / f"{stem[:10]}-{parts[3]}.png"
        image_path = str(ogp_path) if ogp_path.exists() else ""
        results.append({"title": title, "url": url, "image": image_path})
    return results


def build_schedule(start_date: date, article_posts: list[dict]) -> list[dict]:
    """2週間分の投稿スケジュールを組む"""
    rng = random.Random()  # シードなし（毎回変わる）
    schedule = []

    # カジュアル投稿を配置（1日5件 × 14日 = 70件）
    casual_pool = CASUAL_POSTS.copy()
    rng.shuffle(casual_pool)
    pool_index = 0

    for day_offset in range(SCHEDULE_DAYS):
        day = start_date + timedelta(days=day_offset)
        for hour, minute_base in DAILY_TIMES:
            minute = minute_base + rng.randint(-10, 10)
            if minute < 0:
                hour -= 1
                minute += 60
            elif minute >= 60:
                hour += 1
                minute -= 60
            dt = datetime(day.year, day.month, day.day, hour, minute)
            content = casual_pool[pool_index % len(casual_pool)]
            pool_index += 1
            schedule.append({"dt": dt, "content": content, "image": ""})

    # 記事紹介投稿を差し込む（1〜3日目の昼ごろ）
    for i, ap in enumerate(article_posts):
        insert_day = start_date + timedelta(days=min(i + 1, 3))
        insert_hour = 11
        insert_minute = rng.randint(0, 59)
        dt = datetime(insert_day.year, insert_day.month, insert_day.day, insert_hour, insert_minute)
        template = rng.choice(ARTICLE_TEMPLATES)
        content = template.format(title=ap["title"], url=ap["url"])
        schedule.append({"dt": dt, "content": content, "image": ap.get("image", "")})

    return sorted(schedule, key=lambda x: x["dt"])


def write_csv(schedule: list[dict]) -> None:
    """SocialDog形式のCSVを書き出す"""
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        header = ["投稿日時", "投稿内容"] + [f"メディア{i}" for i in range(1, 11)]
        writer.writerow(header)
        for row in schedule:
            dt_str = row["dt"].strftime("%Y/%m/%d %H:%M")
            image = row.get("image", "")
            writer.writerow([dt_str, row["content"], image] + [""] * 9)
    print(f"CSV生成完了: {OUTPUT_CSV} ({len(schedule)}件)")


def main() -> None:
    today = date.today()
    # 当日の記事投稿を取得
    article_posts = get_todays_ja_posts()
    if article_posts:
        print(f"本日の記事 {len(article_posts)} 件を紹介投稿に含めます")
        for ap in article_posts:
            print(f"  - {ap['title']}")
    else:
        print("本日の記事なし（カジュアル投稿のみ生成）")

    # 明日から2週間のスケジュールを生成
    start_date = today + timedelta(days=1)
    schedule = build_schedule(start_date, article_posts)
    write_csv(schedule)


if __name__ == "__main__":
    main()
