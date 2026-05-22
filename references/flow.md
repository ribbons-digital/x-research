# X Research Flow

## Purpose

This skill turns tweet-like content into a durable research record.

## Primary route

### Unified entrypoint
- `x_research.py` is now the primary entrypoint.
- It auto-detects URL vs screenshot input, and also supports `--text` / `--file` for pasted content.
- URL mode fetches structured content via `xurl` CLI (`x_fetch.py`), which auto-expands quoted/retweeted content via X API v2 expansions.
- Then it picks one route:
  - native X article body when `article.plain_text` exists
  - external article branch when the tweet has a first non-X URL and the native article body is absent (or `--route external` is forced)
  - plain tweet branch otherwise
- Then it runs rule-based quality analysis (`x_quality.py`) and optionally stores the rendered note.
- `--json` can be used on the unified entrypoint to get a stable machine-readable console schema across all branches.

## Fallback routes

### Pasted text
Use when URL ingestion fails or the user already pasted the tweet text.
- Primary: `x_research.py --text "..." --author "@handle"`
- Compatibility: `x_store_text.py --text "..."` wraps the unified entrypoint and writes directly to inbox.

### Screenshot OCR
Use when the user sends a screenshot instead of text.
- Primary: `x_research.py /path/to/image.jpg --route image --lang eng`
- Compatibility: `x_store_screenshot.py /path/to/image.jpg` wraps the unified entrypoint and writes directly to inbox.
- Lower confidence when OCR quality is weak.

## Enrichment routes

### External article link
If the tweet includes a non-X external URL and appears to be a short wrapper around linked content:
- Primary: `x_research.py <url> --route external`
- Auto path: `x_research.py <url>` falls into this branch when no native article body exists and a non-X URL does.
- Compatibility: `x_research_article.py <url>` wraps the unified entrypoint.
- Combines tweet + article into one research note.

### Native article detection
If the tweet resolves to an `x.com/i/article/...` URL:
- `x_fetch.py` requests the X API `article` field and detects the `native_article_url`.
- When the API returns `article.plain_text`, `x_research.py` uses the native article body directly.
- If the API does not return body text, it can fall back to the external-URL branch when available, otherwise pasted text, screenshot OCR, or browser capture.

## Durable storage target

- Default: `~/.hermes/workspace/research/x-research/inbox/YYYY-MM.md`
- Configurable via `--output-dir` or `X_RESEARCH_DIR` env var.

## Why this matters

The goal is to keep tweet research usable even when direct URL extraction is unreliable. All scripts are harness-agnostic: they resolve sibling paths via `__file__` and do not depend on Hermes-specific directory structure.

See `references/harness-agnostic-design.md` for the design rationale.
