# セットアップ手順

## 全体の仕組み

```
あなたが何もしなくても…

毎週月・木  GitHub Actionsが起動
    ↓
Claude APIがSEO記事を自動生成
    ↓
_posts/ にMarkdownファイルをコミット
    ↓
GitHub Pagesが自動でサイトを更新
    ↓
Googleに記事がインデックスされ検索流入が増える
    ↓
読者が紹介リンクをクリックして申し込む
```

---

## 完了済み ✅

- [x] Step 1: GitHubリポジトリ作成（`Eizo0000-jp/mno`）
- [x] Step 2: ファイルをプッシュ
- [x] Step 3: GitHub Pages有効化（`https://eizo0000-jp.github.io/mno/`）
- [x] Step 4-1: ドメイン取得（`mobile-friend.com`）
- [x] Step 4-2: DNSのAレコード設定（お名前.com）
- [x] Step 4-3: CNAMEファイル設定済み

---

## 残りの手順

### Step 4-4: GitHub Pagesにカスタムドメインを登録する

1. https://github.com/Eizo0000-jp/mno/settings/pages を開く
2. **Custom domain** に `mobile-friend.com` と入力して「Save」
3. DNS反映後（最大48時間）に **Enforce HTTPS** のチェックが押せるようになる → チェックを入れる

> DNS反映の確認方法：ターミナルで `nslookup mobile-friend.com` を実行し、GitHubのIPが返ってくればOK

---

### Step 5: Anthropic APIキーを取得する

1. https://console.anthropic.com/ にアクセス
2. アカウント作成（Googleアカウントでもログイン可）
3. 「API Keys」→「Create Key」
4. 表示されたキー（`sk-ant-...`）をコピーしてメモ

---

### Step 6: GitHub Secretsに登録する

1. https://github.com/Eizo0000-jp/mno/settings/secrets/actions を開く
2. 「New repository secret」で以下を登録：

| Name                | Value                  |
|---------------------|------------------------|
| `ANTHROPIC_API_KEY` | Step 5 でコピーしたキー |

---

### Step 7: 動作確認

1. https://github.com/Eizo0000-jp/mno/actions を開く
2. 左の「SEO記事 自動生成・公開」をクリック
3. 右上「Run workflow」→「Run workflow」で手動実行
4. 緑チェックになれば成功
5. `_posts/` フォルダに記事ファイルが増えていることを確認

---

## 以降は全自動

設定完了後は何もしなくても、**毎週月曜・木曜に新記事が1本追加**されます。
記事が12本（テーマが一巡）するとランダムに再生成を続けます。

---

## トラブルシューティング

### Actionsが失敗する場合
- Actions タブでエラーログを確認
- Secrets の `ANTHROPIC_API_KEY` が正しく登録されているか確認

### サイトが `mobile-friend.com` で表示されない場合
- DNS反映待ち（最大48時間）
- お名前.comのAレコードが4つ正しく設定されているか確認

### 記事が増えない場合
- `_posts/` フォルダが空の場合、手動で一度 Run workflow を実行する
