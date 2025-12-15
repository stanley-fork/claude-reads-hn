#!/bin/bash
# Batch translate digests using the translator agent
# Usage: ./scripts/translate-batch.sh [files...]
# Example: ./scripts/translate-batch.sh digests/2025/12/*.md

set -e

LANGS="zh ja ko es de"
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <digest-files...>"
    echo "Example: $0 digests/2025/12/15-*.md"
    exit 1
fi

cd "$BASE_DIR"

for file in "$@"; do
    if [ ! -f "$file" ]; then
        echo "skip: $file (not found)"
        continue
    fi

    # skip i18n files
    if [[ "$file" == *"/i18n/"* ]]; then
        echo "skip: $file (already translation)"
        continue
    fi

    echo "=== Translating: $file ==="

    for lang in $LANGS; do
        # derive target path
        target="${file/digests\//digests/i18n/$lang/}"
        target_dir=$(dirname "$target")

        if [ -f "$target" ]; then
            echo "  $lang: exists, skipping"
            continue
        fi

        echo "  $lang: translating..."
        mkdir -p "$target_dir"

        # spawn translator agent
        claude --agent translator "Translate $file to $lang" \
            --model claude-sonnet-4-5-20250514 \
            --print 2>/dev/null || echo "  $lang: failed"
    done
done

echo "=== Done ==="
echo "Run: git add digests/i18n && git commit -m 'i18n: batch translations'"
