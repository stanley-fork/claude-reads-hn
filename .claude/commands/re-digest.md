# Re-Digest Command

Reprocess existing digests: update format, generate translations, add historical stories.

## Usage

```bash
# Re-digest single file
claude /re-digest digests/2025/12/15-0600.md

# Re-digest date range
claude /re-digest digests/2025/12/10-*.md digests/2025/12/11-*.md

# Re-digest all December 2025
claude /re-digest digests/2025/12/*.md
```

## What It Does

1. **Format Update**: Ensure consistent structure
   - `Comments:` with bullet format (2-3 contrasting views)
   - `Tags:` with 2-4 lowercase English hashtags
   - All URLs preserved unchanged

2. **Translate**: Spawn translator agents for all languages
   - Languages: zh, ja, ko, es, de
   - Output: `digests/i18n/{lang}/YYYY/MM/DD-HHMM.md`

3. **Regenerate Index**: Run `./llms-gen.py`

## Execution Steps

Given file(s) as $ARGS:

```
1. Parse file list from $ARGS (glob expansion)

2. For each digest file:
   a. Read current content
   b. Verify/fix format:
      - Title: # HN Digest YYYY-MM-DD HH:MM UTC
      - Vibe: > one-liner
      - Stories: ### [Title](url) • Xpts Yc
      - Comments: bullet list with 2-3 quotes
      - Tags: #lowercase #hashtags
   c. Write corrected version back

3. Spawn translator agents (parallel):
   claude --agent translator "Translate $FILE to zh" --run-in-background
   claude --agent translator "Translate $FILE to ja" --run-in-background
   claude --agent translator "Translate $FILE to ko" --run-in-background
   claude --agent translator "Translate $FILE to es" --run-in-background
   claude --agent translator "Translate $FILE to de" --run-in-background

4. Wait for all translators to complete

5. Run ./llms-gen.py

6. Git commit with message: "re-digest: update format + translations for {files}"
```

## Adding Historical Stories

To add stories from the past (not from live HN feed):

```bash
# Create digest manually or from archive
claude "Create digest for HN top stories from 2024-01-15 using web.archive.org snapshots"
```

Historical digests follow same format, just different source data.

## Notes

- Does NOT re-fetch articles (preserves existing TLDRs and Takes)
- Translations overwrite existing i18n files
- Run during low-usage hours for batch operations
- Use `--model haiku` for format checks, `--model sonnet` for translations
