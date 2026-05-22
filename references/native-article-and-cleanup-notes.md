# Native article extraction and cleanup notes

## What changed

The skill was cleaned up so the legacy entry scripts are compatibility wrappers over a unified `scripts/x_research.py` entrypoint plus shared helpers in `scripts/x_common.py`.

Shared helpers now cover:
- command execution / error handling
- output dir resolution
- tweet payload fetch
- standard note rendering
- combined analysis text construction
- note appending
- first external URL extraction

This reduces drift between:
- `x_research.py`
- `x_research_url.py`
- `x_research_article.py`
- `x_store_text.py`
- `x_store_screenshot.py`

The practical shape is now:
- `x_research.py` = primary CLI for URL / external / text / screenshot routes
- legacy scripts = thin wrappers that preserve old commands

## Native X article path

For long-form X native articles, prefer the X API `article` field instead of OCR or brittle scraping.

Working pattern:
- fetch tweet via `xurl` raw endpoint
- request `tweet.fields=article,note_tweet,created_at,entities,attachments,referenced_tweets`
- read article payload from the tweet object

Useful returned fields include:
- `article.title`
- `article.preview_text`
- `article.plain_text`
- cover media / media entities when present

Practical rule:
- if `article.plain_text` exists, analyze that directly
- do not treat native articles as URL-only pointers
- only fall back to pasted text / screenshot OCR when the API does not provide body text

## External article path

`xurl` does not extract external website article bodies. For tweets linking off-platform, use this sequence:
1. fetch tweet + entities from X API
2. locate the first non-X external URL
3. try JSON-LD `articleBody`
4. fall back to cleaned HTML text extraction

This path is still inherently less reliable than native article extraction.

## Why this matters

Without the `article` field path, long-form X posts get misclassified as thin tweets and lose most of their analytical value. The cleaned-up shared layer also makes future schema or note-format changes much safer because storage and rendering logic now live in one place.
