---
name: x-research
description: Research X/Twitter posts from tweet URLs, pasted tweet text, or tweet screenshots. Use when a user wants a tweet summarized, analyzed, compared, stored for later, or folded into a durable research knowledge base. Prefer the xurl CLI path for tweet URLs, and use pasted text or screenshot OCR as fallbacks.
---

# X Research

Turn tweets into durable research notes.

## Requirements

- **xurl CLI** — authenticated X API client: https://github.com/xdevplatform/xurl
  - Run `xurl auth status` to verify a default app is configured.
- **Python 3.9+**
  - Keep runtime typing compatible with the minimum version. If you add typed payload schemas, avoid Python-3.11-only typing features in live import paths unless you also raise the minimum version.
- **uv** (recommended on macOS for isolated setup) or plain `python3 + pip`
- **requests** — `pip install -r requirements.txt` or use the helper script below
- **tesseract** — system package, required only for screenshot OCR (`brew install tesseract` or `apt-get install tesseract-ocr`)

All scripts live under `{baseDir}/scripts/` and are self-contained. They resolve sibling scripts via `__file__` so the skill can be cloned and used outside Hermes (e.g., by Codex or direct shell usage).

See `references/harness-agnostic-design.md` for the full design rationale.
See `references/native-article-and-cleanup-notes.md` for the shared-script cleanup pattern and the preferred X native article extraction route.
See `references/unified-entrypoint-maintenance.md` for the consolidation pattern: one real CLI entrypoint, compatibility wrappers for legacy commands, and the minimum verification matrix after route changes.
See `references/setup-macos.md` for the one-command Mac setup helper.

## macOS setup helper

If you are moving this skill to another Mac, use the bundled setup script:

```bash
./scripts/setup_macos.sh
./scripts/setup_macos.sh --dry-run
```

It will:
- install `uv` via Homebrew when missing
- install `tesseract` via Homebrew when missing
- install `xurl` via the official install script when missing
- create `.venv`
- install `requirements.txt` into that `.venv`

After it finishes, run:

```bash
xurl auth status
.venv/bin/python scripts/x_research.py --text 'hello world' --author '@test' --json
```

## Ingestion priority

### For standard tweets (x.com/username/status/ID without article content):
1. **xurl CLI path** for tweet URLs
   - `xurl read` fetches the tweet and auto-expands quoted/retweeted content.
2. **Pasted text** fallback
3. **Screenshot OCR** fallback

### For X native articles (x.com/i/article/... or long-form posts):
1. **xurl CLI path** — request the `article` field from X API.
   - `x_fetch.py` now captures `article.title`, `article.preview_text`, `article.plain_text`, and article media metadata when available.
   - This means many native article bodies are directly extractable through `xurl`; OCR is no longer the default fallback for this route.
2. **Pasted text / Screenshot OCR** fallbacks
   - Use these only when the API does not return article body text (for example, restricted/private content or API gaps).

### For tweets linking to external articles:
1. **xurl CLI + article fetch** — fetch the tweet, then extract the first external URL content.

## Main scripts

### Fetch structured tweet data via xurl CLI

```bash
python3 {baseDir}/scripts/x_fetch.py "<tweet-url>"
```

Uses `xurl` raw API to fetch the tweet with full expansions (author, referenced tweets, media, note_tweet, article). Output is unified JSON consumed by the other scripts.

### Unified entrypoint

```bash
python3 {baseDir}/scripts/x_research.py "<tweet-url>"
python3 {baseDir}/scripts/x_research.py "<tweet-url>" --store
python3 {baseDir}/scripts/x_research.py "<tweet-url>" --route external
python3 {baseDir}/scripts/x_research.py "<tweet-url>" --json
python3 {baseDir}/scripts/x_research.py --text "<tweet text>" --author "@handle"
python3 {baseDir}/scripts/x_research.py /path/to/screenshot.jpg --route image --lang eng
```

Single entrypoint that auto-detects or forces these branches:
- normal tweet URL
- native X article content
- tweet + first external article URL
- pasted text
- screenshot OCR

`--json` emits a stable machine-readable result envelope with:
- `route`
- `author`
- `tweet_time`
- `source_url`
- `stored_to`
- `analysis`
- `raw_text`
- `note_body`
- `metadata`

### Research output from tweet URL

```bash
python3 {baseDir}/scripts/x_research_url.py "<tweet-url>"
python3 {baseDir}/scripts/x_research_url.py "<tweet-url>" --store
```

Compatibility wrapper over `x_research.py --route url`. Auto-merges quoted/retweeted content because `x_fetch.py` already expands it.

### Tweet + external article branch

```bash
python3 {baseDir}/scripts/x_research_article.py "<tweet-url>"
python3 {baseDir}/scripts/x_research_article.py "<tweet-url>" --store
```

Compatibility wrapper over `x_research.py --route external`. Fetches the tweet via `xurl`, then attempts to extract the first non-X external URL content.

### Store from pasted tweet text

```bash
python3 {baseDir}/scripts/x_store_text.py --author "@handle" --text "<tweet text>"
```

Compatibility wrapper over `x_research.py --route text --store`.

### OCR from screenshot

```bash
python3 {baseDir}/scripts/x_screenshot_ocr.py /path/to/image.jpg --lang eng
python3 {baseDir}/scripts/x_screenshot_ocr.py /path/to/image.jpg --lang chi_sim
python3 {baseDir}/scripts/x_screenshot_ocr.py /path/to/image.jpg --lang chi_tra
```

### Store from screenshot

```bash
python3 {baseDir}/scripts/x_store_screenshot.py /path/to/image.jpg --lang eng
```

Compatibility wrapper over `x_research.py --route image --store`. Wraps OCR + quality analysis + storage in one command.

## Output format

Align with `research/COMMON_RESEARCH_FORMAT.md`:
- **Summary**
- **Key claim / Core thesis**
- **Type**
- **Why it matters**
- **Possible implication**
- **Confidence**
- **Actionability**
- **Store decision**
- **Follow-up**

## Durable storage

When the user says `store`, `store for later`, or equivalent, append to:

```text
{inbox}/YYYY-MM.md
```

Default inbox: `~/.hermes/workspace/research/x-research/inbox/`
Override with `--output-dir` or the `X_RESEARCH_DIR` environment variable.

## Quality analysis

All research scripts delegate summarization, topic/entity extraction, and quality scoring to:

```bash
python3 {baseDir}/scripts/x_quality.py --text "..." --json
```

This is a rule-based module (no LLM calls) for speed and determinism.

## Notes

- **Do not infer tweet meaning from an unreadable URL.**
- If URL ingestion fails, fall back to pasted text or screenshot OCR.
- Screenshot OCR works best for English, Simplified Chinese, and Traditional Chinese when image quality is decent.
- For native articles, try the X API `article` field first. When available, `xurl` can return `article.title`, `article.preview_text`, and `article.plain_text` directly.
- If native article body is missing from the API response, fall back to pasted text, screenshot OCR, or a logged-in browser capture.
- When running outside Hermes (e.g., Codex), clone the skill directory and run scripts directly. All internal paths are relative to the script file.

For the conceptual flow and route decision logic, see `references/flow.md`.
