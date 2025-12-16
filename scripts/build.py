#!/usr/bin/env python3
"""
Build static HTML from i18n markdown digests.

Format: Regular markdown with inline translations:
  <!-- i18n:LANG -->translated content<!-- /i18n -->

Output: Single HTML with lang attributes for CSS-based toggling.
"""

import re
import sys
import json
from pathlib import Path
from datetime import datetime

I18N_PATTERN = re.compile(r'<!-- i18n:(\w+) -->(.+?)<!-- /i18n -->', re.DOTALL)
STORY_PATTERN = re.compile(r'### \[(.+?)\]\((.+?)\) • (\d+)pts (\d+)c')
HN_LINK_PATTERN = re.compile(r'\[HN discussion\]\((https://news\.ycombinator\.com/item\?id=(\d+))\)')

def extract_story_id(text):
    """Extract HN story ID from discussion link."""
    match = HN_LINK_PATTERN.search(text)
    return match.group(2) if match else None

def parse_i18n_md(content):
    """
    Parse markdown with i18n blocks.
    Returns: (clean_md, translations_dict)
    """
    translations = {}

    def collect_translation(match):
        lang = match.group(1)
        text = match.group(2).strip()
        if lang not in translations:
            translations[lang] = []
        translations[lang].append(text)
        return f'<span class="i18n i18n-{lang}" lang="{lang}">{text}</span>'

    processed = I18N_PATTERN.sub(collect_translation, content)
    return processed, translations

def md_to_html(md_content):
    """Simple markdown to HTML conversion."""
    html = md_content

    # Headers
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^\*\*(.+?)\*\*$', r'<strong>\1</strong>', html, flags=re.MULTILINE)

    # Blockquotes (vibe line)
    html = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)

    # Links
    html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html)

    # Bold/italic
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

    # Lists
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)

    # Tags
    html = re.sub(r'#(\w+)', r'<span class="tag">#\1</span>', html)

    # Horizontal rules
    html = re.sub(r'^---$', r'<hr>', html, flags=re.MULTILINE)

    # Paragraphs for TLDR/Take/Comments
    html = re.sub(r'^(TLDR|Take|Comments):(.*)$', r'<p class="\1">\1:\2</p>', html, flags=re.MULTILINE)

    # Wrap lists
    html = re.sub(r'(<li>.+?</li>(\s*<li>.+?</li>)*)', r'<ul>\1</ul>', html, flags=re.DOTALL)

    return html

def build_digest_html(md_path, template=None):
    """Build HTML from a single i18n markdown file."""
    content = Path(md_path).read_text()

    # Parse i18n blocks
    processed, translations = parse_i18n_md(content)

    # Convert to HTML
    html_content = md_to_html(processed)

    # Extract metadata
    title_match = re.search(r'<h1>(.+?)</h1>', html_content)
    title = title_match.group(1) if title_match else 'HN Digest'

    # Extract story IDs for anchors
    story_ids = HN_LINK_PATTERN.findall(content)

    # Available languages
    langs = ['en'] + list(translations.keys())

    return {
        'title': title,
        'html': html_content,
        'langs': langs,
        'story_ids': [sid[1] for sid in story_ids],
        'translations': translations
    }

def generate_page(digests, output_path):
    """Generate full HTML page from multiple digests."""

    all_langs = set(['en'])
    for d in digests:
        all_langs.update(d['langs'])

    lang_buttons = '\n'.join([
        f'<button onclick="setLang(\'{lang}\')" data-lang="{lang}">{lang.upper()}</button>'
        for lang in sorted(all_langs)
    ])

    digest_html = '\n'.join([
        f'<article class="digest">{d["html"]}</article>'
        for d in digests
    ])

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Reads HN</title>
    <style>
        :root {{
            --bg: #fafaf9;
            --fg: #1c1917;
            --muted: #78716c;
            --accent: #ea580c;
            --border: #e7e5e4;
        }}
        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg: #1c1917;
                --fg: #fafaf9;
                --muted: #a8a29e;
                --border: #44403c;
            }}
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: ui-monospace, monospace;
            background: var(--bg);
            color: var(--fg);
            max-width: 720px;
            margin: 0 auto;
            padding: 2rem 1rem;
            line-height: 1.6;
        }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }}
        .logo {{ font-weight: bold; }}
        .lang-switcher button {{
            background: none;
            border: 1px solid var(--border);
            padding: 0.25rem 0.5rem;
            cursor: pointer;
            color: var(--fg);
            font-family: inherit;
        }}
        .lang-switcher button.active {{
            background: var(--accent);
            color: white;
            border-color: var(--accent);
        }}
        h1 {{ font-size: 1.25rem; margin-bottom: 0.5rem; }}
        h3 {{ font-size: 1rem; margin: 1.5rem 0 0.5rem; }}
        blockquote {{
            color: var(--muted);
            font-style: italic;
            margin: 0.5rem 0;
        }}
        a {{ color: var(--accent); }}
        hr {{ border: none; border-top: 1px solid var(--border); margin: 1.5rem 0; }}
        ul {{ list-style: none; padding-left: 1rem; }}
        li {{ margin: 0.25rem 0; }}
        li::before {{ content: "- "; color: var(--muted); }}
        .TLDR, .Take, .Comments {{ margin: 0.5rem 0; }}
        .tag {{
            background: var(--border);
            padding: 0.1rem 0.3rem;
            border-radius: 3px;
            font-size: 0.85em;
        }}
        .i18n {{
            display: none;
            color: var(--muted);
            font-size: 0.9em;
        }}
        .i18n::before {{ content: "↳ "; }}
        body.show-zh .i18n-zh,
        body.show-ja .i18n-ja,
        body.show-ko .i18n-ko,
        body.show-es .i18n-es,
        body.show-de .i18n-de {{ display: block; }}
        body.show-all .i18n {{ display: block; }}
        .digest {{ margin-bottom: 3rem; }}
    </style>
</head>
<body>
    <header>
        <div class="logo">Claude Reads HN</div>
        <div class="lang-switcher">
            {lang_buttons}
            <button onclick="setLang('all')" data-lang="all">ALL</button>
        </div>
    </header>
    <main>
        {digest_html}
    </main>
    <script>
        function setLang(lang) {{
            document.body.className = lang === 'en' ? '' : 'show-' + lang;
            document.querySelectorAll('.lang-switcher button').forEach(b => {{
                b.classList.toggle('active', b.dataset.lang === lang);
            }});
            localStorage.setItem('hn-lang', lang);
        }}
        const saved = localStorage.getItem('hn-lang') || 'en';
        setLang(saved);
    </script>
</body>
</html>'''

    Path(output_path).write_text(html)
    return output_path

def main():
    if len(sys.argv) < 2:
        print("Usage: build.py <digest.md> [output.html]")
        print("       build.py --all  # build all digests")
        sys.exit(1)

    repo_root = Path(__file__).parent.parent

    if sys.argv[1] == '--all':
        # Build all digests
        digest_files = sorted(repo_root.glob('digests/**/*-i18n.md'), reverse=True)
        if not digest_files:
            digest_files = sorted(repo_root.glob('digests/**/*.md'), reverse=True)[:5]

        digests = [build_digest_html(f) for f in digest_files]
        output = repo_root / 'index.html'
        generate_page(digests, output)
        print(f"Built {len(digests)} digests → {output}")
    else:
        md_path = Path(sys.argv[1])
        output = sys.argv[2] if len(sys.argv) > 2 else md_path.with_suffix('.html')

        digest = build_digest_html(md_path)
        generate_page([digest], output)
        print(f"Built {md_path} → {output}")

if __name__ == '__main__':
    main()
