#!/usr/bin/env python3
"""
Translate HN digests to multiple languages using Claude API.
Uses claude-sonnet-4-5 for cost efficiency.

Usage:
  python translate.py digests/2025/12/15-0600.md
  python translate.py digests/2025/12/15-0600.md --lang zh
  python translate.py --all  # translate all untranslated digests
"""

import os
import sys
import argparse
import json
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("pip install anthropic")
    sys.exit(1)

LANGUAGES = {
    "zh": {"name": "Chinese (Simplified)", "native": "简体中文"},
    "es": {"name": "Spanish", "native": "Español"},
    "ja": {"name": "Japanese", "native": "日本語"},
    "de": {"name": "German", "native": "Deutsch"},
    "fr": {"name": "French", "native": "Français"},
}

MODEL = "claude-sonnet-4-5-20241022"

SYSTEM_PROMPT = """You are a native {lang_name} translator specializing in tech content.
Translate the following HN digest into {lang_name}.

RULES:
- Keep ALL markdown formatting exactly as-is (headers, links, bold, etc.)
- Keep URLs unchanged
- Keep usernames unchanged (e.g. -username stays as -username)
- Keep hashtags unchanged (e.g. #rust stays as #rust)
- Keep technical terms that are commonly used in English (API, GitHub, etc.)
- Translate naturally as a native speaker would write, not word-for-word
- Preserve the spicy/sarcastic tone - it should feel fun in {lang_name} too
- The "Take:" section should sound like a witty tech commentator in {lang_name}

Output ONLY the translated markdown, nothing else."""


def translate_digest(content: str, lang_code: str) -> str:
    """Translate digest content to target language."""
    client = anthropic.Anthropic()
    lang = LANGUAGES[lang_code]

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT.format(lang_name=lang["name"]),
        messages=[{"role": "user", "content": content}]
    )

    return response.content[0].text


def get_translation_path(original_path: str, lang_code: str) -> Path:
    """Get path for translated file: digests/zh/2025/12/15-0600.md"""
    path = Path(original_path)
    parts = path.parts

    # Find 'digests' in path and insert language after it
    if 'digests' in parts:
        idx = parts.index('digests')
        new_parts = parts[:idx+1] + (lang_code,) + parts[idx+1:]
        return Path(*new_parts)

    return path.parent / lang_code / path.name


def translate_file(file_path: str, lang_codes: list[str] = None, force: bool = False):
    """Translate a single digest file to specified languages."""
    if lang_codes is None:
        lang_codes = list(LANGUAGES.keys())

    path = Path(file_path)
    if not path.exists():
        print(f"File not found: {file_path}")
        return

    content = path.read_text()

    for lang in lang_codes:
        if lang not in LANGUAGES:
            print(f"Unknown language: {lang}")
            continue

        out_path = get_translation_path(file_path, lang)

        if out_path.exists() and not force:
            print(f"[skip] {out_path} exists")
            continue

        print(f"[translate] {path.name} -> {lang} ({LANGUAGES[lang]['native']})")

        try:
            translated = translate_digest(content, lang)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(translated)
            print(f"[done] {out_path}")
        except Exception as e:
            print(f"[error] {lang}: {e}")


def translate_all(force: bool = False):
    """Translate all untranslated digests."""
    digests_dir = Path("digests")
    if not digests_dir.exists():
        print("No digests directory found")
        return

    # Find all English digests (not in language subdirs)
    for md_file in sorted(digests_dir.glob("20*/**/*.md")):
        # Skip if path contains a language code
        if any(f"/{lang}/" in str(md_file) for lang in LANGUAGES):
            continue
        translate_file(str(md_file), force=force)


def main():
    parser = argparse.ArgumentParser(description="Translate HN digests")
    parser.add_argument("file", nargs="?", help="Digest file to translate")
    parser.add_argument("--lang", "-l", help="Target language (zh, es, ja, de, fr)")
    parser.add_argument("--all", "-a", action="store_true", help="Translate all digests")
    parser.add_argument("--force", "-f", action="store_true", help="Overwrite existing")
    parser.add_argument("--list", action="store_true", help="List supported languages")

    args = parser.parse_args()

    if args.list:
        print("Supported languages:")
        for code, info in LANGUAGES.items():
            print(f"  {code}: {info['name']} ({info['native']})")
        return

    if args.all:
        translate_all(force=args.force)
    elif args.file:
        langs = [args.lang] if args.lang else None
        translate_file(args.file, lang_codes=langs, force=args.force)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
