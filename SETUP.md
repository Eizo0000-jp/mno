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

## Step 1: GitHubリポジトリを作る

1. https://github.com/Eizo0000-jp にログイン
2. 右上「+」→「New repository」
3. 設定：
   - Repository name: `walktogether`（任意）
   - Public を選択（GitHub Pagesの無料枠に必要）
   - 他はデフォルトのまま
4. 「Create repository」をクリック

---

## Step 2: ファイルをアップロードする

作成したファイル一式をGitHubにプッシュします。  
ターミナル（コマンドプロンプト）で以下を実行：

```bash
cd C:\Users\呉栄三\Documents\walktogether

git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/Eizo0000-jp/walktogether.git
git push -u origin main
```

---

## Step 3: GitHub Pagesを有効にする

1. GitHubのリポジトリページを開く
2. 上部タブ「Settings」をクリック
3. 左メニュー「Pages」をクリック
4. 「Source」を **Deploy from a branch** に設定
5. Branch: `main` / `/ (root)` を選択して「Save」

→ 数分後に `https://Eizo0000-jp.github.io/walktogether/` でサイトが公開される

---

## Step 4: 独自ドメインを設定する（推奨）

独自ドメインがあるとSEO効果が大きく上がります。

### 4-1. ドメインを取得する

お名前.com・ムームードメイン・お好みのところで取得（例：`rakuten-intro.com`）

### 4-2. DNSを設定する

ドメイン管理画面で以下のAレコードを追加：

| タイプ | ホスト名 | 値              |
|--------|----------|-----------------|
| A      | @        | 185.199.108.153 |
| A      | @        | 185.199.109.153 |
| A      | @        | 185.199.110.153 |
| A      | @        | 185.199.111.153 |

または CNAMEレコード：

| タイプ | ホスト名 | 値                            |
|--------|----------|-------------------------------|
| CNAME  | www      | Eizo0000-jp.github.io         |

### 4-3. CNAMEファイルを編集する

`CNAME` ファイルを開き、`yourdomain.com` を実際のドメインに変更してコミット：

```
rakuten-intro.com
```

### 4-4. GitHub Pagesでカスタムドメインを設定

Settings → Pages → Custom domain にドメインを入力して Save  
「Enforce HTTPS」にチェックを入れる

### 4-5. _config.yml を更新する

```yaml
url: "https://rakuten-intro.com"   # ← 実際のドメインに変更
```

---

## Step 5: Anthropic APIキーを取得する

1. https://console.anthropic.com/ にアクセス
2. アカウント作成（Googleアカウントでもログイン可）
3. 「API Keys」→「Create Key」
4. 表示されたキー（`sk-ant-...`）をコピーしてメモ

---

## Step 6: GitHub Secretsに登録する

1. GitHubのリポジトリページ → Settings → Secrets and variables → Actions
2. 「New repository secret」で以下を登録：

| Name                | Value                  |
|---------------------|------------------------|
| `ANTHROPIC_API_KEY` | Step 5 でコピーしたキー |

---

## Step 7: 動作確認

1. GitHubのリポジトリ → 上部タブ「Actions」を開く
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

### サイトが表示されない場合
- Settings → Pages で公開設定が有効か確認
- 独自ドメインのDNS設定は反映に最大48時間かかる場合がある

### 記事が増えない場合
- `_posts/` フォルダが空の場合、手動で一度 Run workflow を実行する
