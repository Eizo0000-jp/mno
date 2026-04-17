"""
LP（ランディングページ）多言語翻訳スクリプト
index.htmlを読み込み、各言語版を生成する
実行: python automation/generate_lp_translations.py
"""

import anthropic
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SOURCE_LP = REPO_ROOT / "index.html"

LANGUAGES = {
    "en": {
        "name": "English",
        "html_lang": "en",
        "dir": "en",
        "active_label": "English",
    },
    "ko": {
        "name": "Korean (한국어)",
        "html_lang": "ko",
        "dir": "ko",
        "active_label": "한국어",
    },
    "zh-cn": {
        "name": "Chinese Simplified (简体中文)",
        "html_lang": "zh-Hans",
        "dir": "zh-cn",
        "active_label": "简体中文",
    },
    "zh-tw": {
        "name": "Chinese Traditional (繁體中文)",
        "html_lang": "zh-Hant",
        "dir": "zh-tw",
        "active_label": "繁體中文",
    },
    "tl": {
        "name": "Filipino/Tagalog",
        "html_lang": "tl",
        "dir": "tl",
        "active_label": "Filipino",
    },
    "vi": {
        "name": "Vietnamese (Tiếng Việt)",
        "html_lang": "vi",
        "dir": "vi",
        "active_label": "Tiếng Việt",
    },
}


def translate_lp(source_html: str, lang_code: str, lang_info: dict) -> str:
    """Claude APIでLPを翻訳"""
    client = anthropic.Anthropic()

    prompt = f"""You are a professional translator. Translate this Japanese landing page HTML to {lang_info['name']}.

Rules:
1. Translate ALL user-visible Japanese text to {lang_info['name']}
2. Keep ALL HTML structure, CSS, JavaScript UNCHANGED
3. Keep ALL URLs unchanged (especially https://r10.to/henTIE and https://network.mobile.rakuten.co.jp/)
4. Keep ALL numeric values unchanged (14,000, 11,000, 3,278, etc.)
5. Change <html lang="ja"> to <html lang="{lang_info['html_lang']}">
6. In the .lang-bar div, add class="active" to the <a> tag for "{lang_info['active_label']}" and REMOVE class="active" from the Japanese link
7. The nav link href="/blog/" should become href="/{lang_info['dir']}/blog/"
8. Keep all CSS class names, IDs, and attributes in English
9. Output ONLY the complete translated HTML, no explanations

Source HTML:
{source_html}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text.strip()


def main() -> None:
    source_html = SOURCE_LP.read_text(encoding="utf-8")
    print(f"ソースファイル読み込み: {len(source_html)}文字")

    for lang_code, lang_info in LANGUAGES.items():
        print(f"\n{lang_info['name']} を生成中...")

        translated = translate_lp(source_html, lang_code, lang_info)

        # 出力先ディレクトリ作成
        output_dir = REPO_ROOT / lang_info["dir"]
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "index.html"

        # コードブロックの除去（Claude が```html で囲む場合）
        if translated.startswith("```"):
            lines = translated.split("\n")
            translated = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])

        output_path.write_text(translated, encoding="utf-8")
        print(f"  保存完了: {output_path.relative_to(REPO_ROOT)}")

    print("\n全言語のLP生成が完了しました。")


if __name__ == "__main__":
    main()
