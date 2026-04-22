# CLAUDE.md — AI Assistant Guide

## Project Overview

This is a Jekyll-based GitHub Pages site for a Rakuten Mobile employee referral campaign, hosted at **mobile-friend.com**. The site promotes sign-ups via a personal employee referral link and runs automated SEO blog article generation using the Claude API.

**Primary language:** Japanese (日本語)  
**Audience:** Japanese consumers considering switching to Rakuten Mobile

---

## Repository Structure

```
walktogether/
├── index.html                        # Main landing page (standalone HTML, NOT a Jekyll template)
├── blog/index.html                   # Blog listing page (Jekyll layout: default)
├── _layouts/
│   ├── default.html                  # Jekyll base layout (header, footer, CSS vars, GA4)
│   └── post.html                     # Blog post layout (extends default)
├── _posts/                           # Jekyll blog posts — auto-generated Markdown files
│   └── YYYY-MM-DD-{slug}.md
├── _config.yml                       # Jekyll site config
├── automation/
│   ├── generate_article.py           # Claude API script to generate SEO articles
│   └── requirements.txt              # Python deps (anthropic>=0.40.0)
├── .github/workflows/
│   └── auto_article.yml              # GitHub Actions: auto-generate + commit articles
├── CNAME                             # Custom domain: mobile-friend.com
└── .gitignore                        # Excludes assets/, _site/, .env, image files
```

---

## Key Business Facts (Never Change Without Verification)

These values are factual campaign details embedded throughout the site and generated articles:

| Item | Value |
|------|-------|
| Referral URL | `https://r10.to/henTIE` |
| MNP (carrier switch) points | **14,000pt** |
| New signup / plan change points | **11,000pt** |
| Normal campaign (MNP) | 13,000pt (for comparison) |
| Monthly plan price | ¥3,278（税込） |
| Max referrals per person | 5回線 |
| Point payout schedule | 紹介ログイン月の4ヶ月後から3ヶ月間に分割（期間限定ポイント） |
| Point type | **期間限定ポイント**（通常ポイントではない） |
| Rakuten Link call requirement | **10秒以上の通話が必須**（2026年3月2日以降申込み）。データタイプは不要 |
| Re-contract / 2nd line eligibility | **再契約・2回線目も対象**（通常キャンペーンにはない社員紹介限定特典） |
| Eligible plans | Rakuten最強プラン（スマホ）、Rakuten最強U-NEXT（2025/10/1〜）、Rakuten Turbo（1回線のみ） |
| データタイプ | 2026年3月5日より新規申込み一時停止。既存ユーザーはキャンペーン対象 |
| Login rescue rule | 申込み後7日以内に紹介URL経由でログインすれば特典適用可 |
| Campaign code | 2162 |

---

## Architecture Notes

### Landing Page (`index.html`)
- **Standalone HTML** — does not use Jekyll layouts or Liquid templating.
- Contains all CSS inline in `<style>` tags.
- CSS uses custom properties (CSS vars) defined in `:root`: `--red`, `--text`, `--text-sub`, `--bg-kinari`, etc.
- GA4 tracking ID: `G-ETZGTWCXDQ` (hardcoded in `<head>`).
- The page has sections: HERO → COMPARE table → POINT BREAKDOWN → HOW TO APPLY (5 steps) → PLAN → CTA → FAQ → FOOTER.
- A `.float-cta` fixed button always shows the referral link at the bottom of the screen.

### Blog (`blog/index.html`, `_layouts/default.html`, `_layouts/post.html`)
- Uses Jekyll Liquid templating.
- `default.html` provides the shared header/nav, CSS vars, GA4, and footer.
- `post.html` extends `default` and adds the post header, body styling, a CTA banner, and prev/next navigation.
- All blog posts automatically appear in the listing at `/blog/`.

### Blog Posts (`_posts/`)
- Filename format: `YYYY-MM-DD-{slug}.md`
- Required front matter:
  ```yaml
  ---
  title: "記事タイトル"
  date: YYYY-MM-DD
  description: "SEO説明文"
  ---
  ```
- Body is Markdown rendered by Jekyll. `## ` and `### ` headings are styled via `post.html`.
- `<strong>` text renders in red (`var(--red)`).

### Auto-Generation System

**Script:** `automation/generate_article.py`
- Uses `anthropic` Python SDK (`claude-sonnet-4-6` model, max_tokens=2500).
- Picks an unused topic from the `TOPICS` list (12 predefined keyword/slug pairs).
- Checks `_posts/` for existing slugs to avoid duplicates. Cycles back to random when all topics are used.
- Generates Markdown articles with `title: ...` on the first line.
- Saves to `_posts/YYYY-MM-DD-{slug}.md` with proper front matter.

**Workflow:** `.github/workflows/auto_article.yml`
- Triggers: every Monday and Thursday at 10:00 JST (UTC 01:00), plus manual `workflow_dispatch`.
- Requires `ANTHROPIC_API_KEY` secret in GitHub repository settings.
- Commits only `_posts/` directory changes with message: `auto: SEO記事を追加 YYYY-MM-DD`.

---

## Development Workflows

### Adding a New Blog Post Manually
1. Create `_posts/YYYY-MM-DD-{slug}.md` with front matter (title, date, description).
2. Write Markdown body. End with a section linking to the referral URL.
3. Commit and push to `main`. GitHub Pages rebuilds automatically.

### Running Article Generation Locally
```bash
pip install -r automation/requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python automation/generate_article.py
```

### Triggering Auto-Generation Manually
Go to GitHub Actions → "SEO記事 自動生成・公開" → "Run workflow".

### Adding a New Topic to Auto-Generation
Edit the `TOPICS` list in `automation/generate_article.py`:
```python
TOPICS = [
    ("キーワード文字列", "url-slug"),
    ...
]
```
The slug must be unique and URL-safe (ASCII, hyphens only).

### Updating Campaign Points or Referral URL
These values appear in multiple places — update all of them:
- `index.html` — compare table, points grid, text content, all CTA button `href` attributes
- `automation/generate_article.py` — `REFERRAL_URL` constant and `TOPICS` keyword list
- `_layouts/post.html` — the CTA banner `href`

---

## Conventions

- **All user-facing content is in Japanese.** Code, variable names, and comments may be in English or Japanese.
- **CSS is inline** — no external stylesheets. CSS vars in `:root` are the design system.
- **Brand color:** `--red: #7f0019` (Rakuten dark red).
- **Font stack:** `"Helvetica Neue", Arial, "Noto Sans JP", "Hiragino Kaku Gothic ProN", Meiryo, sans-serif`
- **No JavaScript frameworks** — the site is pure HTML/CSS/Liquid.
- Articles must naturally link to the referral URL at the end without being overly promotional.
- Never commit `.env`, image files (`*.jpg`, `*.png`, etc.), or `_site/`.

---

## Jekyll Plugins (configured in `_config.yml`)
- `jekyll-feed` — generates `/feed.xml`
- `jekyll-sitemap` — generates `/sitemap.xml`
- `jekyll-seo-tag` — injects SEO meta tags via `{% seo %}` in `default.html`
