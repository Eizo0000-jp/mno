"""
Threads投稿スケジュールCSV生成スクリプト（SocialDog形式）

記事生成後に実行し、2週間分の投稿スケジュールを生成する。
- 当日生成されたブログ記事の紹介投稿（1日1記事差し込み）
- 日常系カジュアル投稿（1日5回ペース、時間帯に合ったコンテンツ）
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

# 1日あたりの投稿時刻（hour, minute_base, slot） ランダムに±10分ずらす
DAILY_TIMES = [
    (7, 30, "morning"),
    (12, 20, "lunch"),
    (15, 45, "afternoon"),
    (19, 10, "evening"),
    (22, 0, "night"),
]

# ─────────────────────────────────────────────
# 日常系カジュアル投稿プール（時間帯別）
# ─────────────────────────────────────────────
CASUAL_BY_TIME = {
    # 朝：起床・朝食・朝コーヒー・朝活・通勤
    "morning": [
        "今朝寝坊してギリギリだったけど間に合った。自分を褒めたい。電車の中でまだ心臓バクバクしてる",
        "今日も朝コーヒーからスタート☕ 最近コンビニのカフェラテにハマってるんだけど、じわじわおいしくなってる気がする",
        "ちょっと早めに家を出てお気に入りのカフェでモーニング☕ こういう余裕のある朝がしたい",
        "朝ごはん、昨日の残りご飯でたまごかけごはんにした。シンプルだけどこれが一番落ち着く",
        "6時に起きて朝ランしてきた。桜並木を走るのが気持ちよすぎて早起きが苦じゃなくなってきた🌸",
        "朝活で近所の公園をウォーキング。鳥の声と新緑がすごくよくて、なんか一日のテンションが上がった🌿",
        "最近早起きを習慣にしようとしてる。今日は5時半に起きれた。朝の静かな時間って貴重",
        "在宅の日のコーヒーはドリップで丁寧に淹れる。この5分が一日の中で一番豊かな時間かもしれない",
        "月曜の朝の電車って独特の重さがあるよね。みんな同じ顔してる気がして少し笑えてくる",
        "新しいコーヒー豆を買ってみた。フルーティーで酸味が爽やかで朝から気分が上がる☕",
        "最近ストレッチを毎朝やるようにしたら肩こりがかなり改善された。継続大事だなとしみじみ",
        "休日ランニング、平日より距離が伸ばせた！5km達成。ご褒美に好きなスイーツ食べよう🏃‍♀️",
        "休日の朝はゆっくり起きてブランチ🥞 平日にはできない贅沢な時間。これが週末の醍醐味",
        "通勤路の桜並木、今年も綺麗だった🌸 毎年この道を歩けることが地味に嬉しい",
        "週末に近所の公園で縄跳びしてきた。子どもの頃ぶりにやったけど全然続かなくて笑えた🪢",
        "GW初日！溜まってた家の掃除をして一気にスッキリした。部屋が綺麗だと心も軽い✨",
    ],

    # ランチ：昼食・昼休み・カフェ休憩
    "lunch": [
        "ランチにパスタ食べてきた🍝 クリームソースが濃厚で幸せ。午後の仕事の活力もらいました",
        "今日のランチは会社近くの定食屋さん🐟 鯖の塩焼き定食850円でこのボリューム、コスパ最強すぎる",
        "社食カレー。毎回食べてるけど毎回おいしい。社食のカレーって不思議な魅力がある🍛",
        "今日はお弁当持参の日！昨夜作った鶏の照り焼きと卵焼きを詰めた🍱 自分で作ったやつが一番おいしい",
        "コンビニランチ。最近のコンビニのサラダって種類豊富すぎて毎回迷う。今日はシーザーサラダとおにぎり2個",
        "今日のランチ後に同僚と苺のタルト食べてきた🍓 季節限定って言われると食べないわけにいかない",
        "ランチ後に同期と近くのカフェでコーヒー休憩☕ この時間が一番のリフレッシュになってる",
        "お昼に会社の近くで新しいランチスポット発見。ハンバーグ定食が800円でボリューム満点だった🍖",
        "ラーメン屋さん、ずっと気になってたところに行ってきた🍜 濃厚スープがしみた。また行く",
        "近所の中華料理屋の麻婆豆腐が辛くておいしすぎた🌶️ 辛いの苦手なはずなのに気づいたら全部食べてた",
        "友達とご飯行って3時間くらいしゃべりっぱなしだった。直接会うのが一番楽しいって毎回思う",
        "今日は友達とカフェ巡り☕ 3軒ハシゴしたけど全部当たりだった。インスタ映えより味重視派",
        "近所に新しいタイ料理屋ができてたので行ってみた。グリーンカレーがばちばちに辛くておいしかった🌿",
        "お花見してきた！！桜がちょうど満開で最高だった🌸 来年もここで見たい",
        "コンビニの新商品、全部試したくなってしまう。今日はチョコ系のお菓子を3つも買ってしまった🍫",
    ],

    # 午後：3時のおやつ・仕事の合間・小休憩
    "afternoon": [
        "3時のコーヒーが一日で一番おいしい説。疲れをちょうどよくリセットしてくれる感じがする☕",
        "15時のおやつタイム。同僚の差し入れのどら焼きがうますぎた。こういう日は仕事もはかどる",
        "仕事の合間にちょっと外の空気吸いに行ったら青空がきれいすぎた。もうちょっと頑張れる気がしてくる☀️",
        "今日のMTGが思ったより早く終わった。溜まってたタスクを消化できそうで少し気持ちが軽くなった",
        "リモートワークで気づいたらずっと座ってた。1時間に1回立つって決めたのに全然できてない",
        "今日は仕事で小さいけど目標達成できた。こういう積み重ねが大事だよね。明日も頑張ろ",
        "在宅ワークの日は通勤ない分、時間の使い方が全然変わる。これに慣れるとオフィスがつらくなるやつ",
        "最近Podcastにハマってる。仕事の合間に聴いてるだけで勉強できてる気がして少し得した感じ🎧",
        "後輩に頼られる機会が増えてきた。自分も最初はそうだったなと思うと、なんか感慨深い",
        "GWの計画を立ててる。どこか旅行行きたいな〜。国内か海外かでまだ悩んでる✈️",
        "文房具屋に入ったら気づいたら30分経ってた。ペンとかノートとか見てるだけで楽しい✏️",
        "今日の空が雲ひとつなくて気持ちよかった。こういう日って何かいいことある気がする☀️",
        "5月になって緑が一気に鮮やかになってきた。この季節の東京ってほんとに好き🌳",
        "週末に散歩してたら知らない路地においしそうなパン屋さんを発見した🍞 こういう発見が散歩の醍醐味",
        "筋トレ始めて3ヶ月。最初は腕立て5回もキツかったのに今は20回できるようになった。地味に嬉しい💪",
    ],

    # 夕方：退勤後・夕食・夕方の買い物・夕焼け
    "evening": [
        "今日の夜ごはん、豚の生姜焼き。自分で言うけど今日のはかなりうまくできた🎉",
        "退勤後にスーパー寄って食材買い出し。今日は豚の生姜焼きにしようと決めてたのに鶏肉が安くて迷った🥩",
        "帰り道に夕焼けがきれいすぎてしばらく立ち止まってしまった。写真に撮っても全然伝わらないやつ",
        "今日は外食。パスタとサラダと白ワインで贅沢なディナー🍷 たまにはいいよね",
        "今週も頑張った〜！金曜の夜のこの解放感、毎週何度味わっても最高。お疲れ自分🎉",
        "今日の仕事終わりに同期と焼き鳥🍢 全然関係ない話で盛り上がりながら飲むビールが最高だった",
        "夜ヨガをやってみた。終わったあと体が軽くてびっくり。これは続けてみようかも🧘‍♀️",
        "ジムでひたすら走ってきた。30分で3km、少しずつ距離が伸びてる。継続は力なり💪",
        "スーパーで旬の野菜を買い込んだ。八百屋みたいな量になってるけど全部使い切る気でいる🥦",
        "夜、急に唐揚げが食べたくなって作ってしまった。衣サクサクで大満足🍗 明日のお弁当にも入れよう",
        "楽天お買い物マラソン中だから買いたかったもの全部まとめて注文した。届くのが楽しみ📦",
        "楽天市場で調理器具を探してたら欲しかったやつがセール価格だった。ポイントもつくしこれは買いでしょ🛒",
        "実家に帰省。お母さんのご飯が世界一おいしいのは不変の事実🏠",
        "友達と久しぶりに連絡とったら急に会うことになった。こういう流れ、好き",
        "楽天スーパーセールはじまってる！欲しかったもの全部まとめてポイントで還元しながら買えるのは楽天の強みだよね💰",
        "靴を新調した。久しぶりに買い替えたら足が軽くなった気がする。いいものを長く使うのが好き👟",
    ],

    # 夜：就寝前・晩酌・Netflix・お風呂上がり・眠れない
    "night": [
        "明日早いのに全然眠れない。こういう夜に限ってスマホを無限に見てしまうやつ🌙",
        "読み始めた本がおもしろすぎて気づいたら1時になってた。明日眠いのわかってるのにやめられない📚",
        "休日のんびりNetflix。気づいたら3時間経ってた。これが幸せってやつだよね🛋️",
        "ドラマ見ながら晩酌🍺 このゆるい時間が一番好きかもしれない。今日も一日お疲れ",
        "日曜の夜ってなんであんなに時間が経つの早いんだろう。気づいたらもう22時でびっくりする",
        "お風呂上がりのアイスクリームが最近の楽しみ🍦 罪悪感はあるけど毎日食べちゃう",
        "残業続きの今週もなんとか乗り越えた。週末は完全オフにするって決めた。えらい自分",
        "今日は一人でのんびり過ごした。たまには誰とも話さない日があってもいい。充電完了✨",
        "雨の日の窓際って妙に落ち着く。コーヒーとお気に入りの本があれば最強の休日☔",
        "引越しして半年、ようやく部屋が自分の空間って感じになってきた。インテリア楽しい🏠",
        "映画館でずっと気になってた映画を観てきた🎬 久しぶりに映画でこんなに泣いた",
        "週末に実家に帰ったら急にゲームしたくなって、昔のゲーム引っ張り出してきた。夢中になりすぎた🎮",
        "手帳を書くのが最近の習慣になってる。ただの日記だけど、振り返ると気づきがある📓",
        "週末に料理の作り置きをした🍳 週の前半はこれで乗り切れる予定。頑張った自分",
    ],
}

# 記事紹介テンプレート（{title}と{url}を置換）
ARTICLE_TEMPLATES = [
    "新しいブログ記事を書きました✍️\n「{title}」\n楽天モバイルへの乗り換えを検討してる方にぜひ読んでもらいたい内容です👇\n{url}",
    "ブログ更新しました📝\n{title}\n\n社員紹介リンク経由で申し込むとMNPで14,000ptもらえるキャンペーンについてまとめてます。気になる方はこちら👇\n{url}",
    "スマホ代の節約を考えてる方へ。楽天モバイルに乗り換えると月3,278円で使い放題、さらに社員紹介でボーナスポイントも🎁\n詳しくはブログにまとめたので読んでみてください👇\n{url}",
    "【ブログ更新】{title}\n\n実際に使ってみてわかったこととか、ポイントのもらい方とかをまとめました。参考になれば嬉しいです😊\n{url}",
    "楽天モバイルの社員紹介、通常キャンペーンより1,000ptお得なの知ってた？ブログにまとめたので気になる方はどうぞ📖\n{url}",
]


def get_all_ja_posts() -> list[dict]:
    """全日本語記事を新しい順で取得（1日1記事紹介用）"""
    posts_dir = REPO_ROOT / "_posts"
    if not posts_dir.exists():
        return []
    results = []
    for p in sorted(posts_dir.glob("*.md"), reverse=True):
        stem = p.stem
        try:
            date.fromisoformat(stem[:10])
        except ValueError:
            continue
        slug_part = stem.split("-", 3)[-1]
        if re.match(r"^(en|ko|zh-cn|zh-tw|tl|vi)-", slug_part):
            continue
        text = p.read_text(encoding="utf-8")
        title_match = re.search(r'^title:\s*"?(.+?)"?\s*$', text, re.MULTILINE)
        title = title_match.group(1) if title_match else slug_part
        parts = stem.split("-", 3)
        url = f"{SITE_URL}/{parts[0]}/{parts[1]}/{parts[2]}/{parts[3]}.html"
        ogp_path = REPO_ROOT / "assets" / "ogp" / f"{stem[:10]}-{parts[3]}.png"
        image_path = str(ogp_path) if ogp_path.exists() else ""
        results.append({"title": title, "url": url, "image": image_path})
    return results


def build_schedule(start_date: date, all_articles: list[dict]) -> list[dict]:
    """2週間分の投稿スケジュールを組む（1日1記事紹介 + カジュアル5件）"""
    rng = random.Random()
    schedule = []

    # 各スロットのカジュアル投稿プールをシャッフル
    slot_pools = {slot: posts.copy() for slot, posts in CASUAL_BY_TIME.items()}
    for posts in slot_pools.values():
        rng.shuffle(posts)
    slot_indices = {slot: 0 for slot in CASUAL_BY_TIME}

    for day_offset in range(SCHEDULE_DAYS):
        day = start_date + timedelta(days=day_offset)

        # カジュアル投稿 5件（時間帯に合ったスロットから選ぶ）
        for hour, minute_base, slot in DAILY_TIMES:
            minute = minute_base + rng.randint(-10, 10)
            if minute < 0:
                hour -= 1
                minute += 60
            elif minute >= 60:
                hour += 1
                minute -= 60
            dt = datetime(day.year, day.month, day.day, hour, minute)
            pool = slot_pools[slot]
            idx = slot_indices[slot]
            content = pool[idx % len(pool)]
            slot_indices[slot] += 1
            schedule.append({"dt": dt, "content": content, "image": ""})

        # 記事紹介投稿 1件/日（記事をサイクル）
        if all_articles:
            ap = all_articles[day_offset % len(all_articles)]
            insert_hour = 11
            insert_minute = rng.randint(0, 59)
            dt = datetime(day.year, day.month, day.day, insert_hour, insert_minute)
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
    all_articles = get_all_ja_posts()
    print(f"記事 {len(all_articles)} 件を1日1件ずつ紹介投稿に配置します")
    for ap in all_articles[:5]:
        print(f"  - {ap['title']}")
    if len(all_articles) > 5:
        print(f"  ... 他 {len(all_articles) - 5} 件")

    # 明日から2週間のスケジュールを生成
    start_date = today + timedelta(days=1)
    schedule = build_schedule(start_date, all_articles)
    write_csv(schedule)


if __name__ == "__main__":
    main()
