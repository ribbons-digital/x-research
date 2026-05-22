#!/usr/bin/env python3
"""Shared helpers for the x-research script suite."""

from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests

SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_OUTPUT_DIR = Path.home() / '.hermes' / 'workspace' / 'research' / 'x-research' / 'inbox'
IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tif', '.tiff', '.heic'}
X_HOST_TOKENS = ('x.com/', 'twitter.com/', 'pic.x.com', 't.co/')


def run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def fail(msg: str, detail: str | None = None, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    if detail:
        print(detail.strip(), file=sys.stderr)
    sys.exit(code)


def load_json(stdout: str, label: str) -> dict:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        fail(f'Failed to parse {label} output', str(exc))


def fetch_payload(url: str) -> dict:
    code, stdout, stderr = run(['python3', str(SCRIPT_DIR / 'x_fetch.py'), url])
    if code != 0:
        fail('x_fetch failed', stderr)
    return load_json(stdout, 'x_fetch')


def analyze_text(text: str) -> dict:
    code, stdout, stderr = run(['python3', str(SCRIPT_DIR / 'x_quality.py'), '--text', text, '--json'])
    if code != 0:
        fail('x_quality failed', stderr)
    return load_json(stdout, 'x_quality')


def resolve_output_dir(output_dir: Path | None) -> Path:
    return output_dir or Path(os.environ.get('X_RESEARCH_DIR', str(DEFAULT_OUTPUT_DIR)))


def append_note(note_body: str, output_dir: Path, heading: str) -> Path:
    ts = datetime.now(timezone.utc)
    month = ts.strftime('%Y-%m')
    stamp = ts.strftime('%Y-%m-%d %H:%M UTC')
    inbox = output_dir / f'{month}.md'
    inbox.parent.mkdir(parents=True, exist_ok=True)
    with inbox.open('a') as handle:
        if inbox.exists() and inbox.stat().st_size > 0:
            handle.write('\n\n')
        handle.write(f'## {stamp} — {heading}\n\n')
        handle.write(note_body.rstrip())
        handle.write('\n')
    return inbox


def format_value(value) -> str:
    if value is None:
        return 'N/A'
    if isinstance(value, list):
        return ', '.join(str(item) for item in value) if value else 'N/A'
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    text = str(value).strip()
    return text or 'N/A'


def format_referenced_tweets(refs: Iterable[dict]) -> str:
    lines = []
    for ref in refs or []:
        ref_text = ref.get('note_tweet_text') or ref.get('text') or ''
        preview = ref_text.replace('\n', ' ').strip()
        if len(preview) > 180:
            preview = preview[:177] + '...'
        lines.append(
            f"- [{ref.get('type', 'unknown')}] {ref.get('author_handle', 'unknown')}"
            f": {preview or 'N/A'}"
        )
    return '\n'.join(lines) if lines else 'N/A'


def extract_first_external_url(item: dict) -> str | None:
    for url_item in item.get('urls', []) or []:
        expanded = (url_item.get('expanded_url') or '').strip()
        if expanded and not any(token in expanded for token in X_HOST_TOKENS):
            return expanded
    return None


def article_text(item: dict) -> str:
    article = item.get('article') or {}
    return (article.get('plain_text') or article.get('preview_text') or '').strip()


def build_combined_text(item: dict, include_references: bool = True) -> str:
    parts: list[str] = []

    article = item.get('article') or {}
    article_title = (article.get('title') or '').strip()
    article_body = article_text(item)
    primary_text = article_body or item.get('note_tweet_text') or item.get('raw_text') or ''

    if article_title:
        parts.append(article_title)
    if primary_text:
        parts.append(primary_text)

    if include_references:
        for ref in item.get('referenced_tweets', []) or []:
            ref_text = (ref.get('note_tweet_text') or ref.get('text') or '').strip()
            if ref_text:
                parts.append(f"[Referenced tweet by {ref.get('author_handle', 'unknown')}]\n{ref_text}")

    return '\n\n'.join(part.strip() for part in parts if part and part.strip()).strip()


def _extract_article_body_from_jsonld(html_text: str) -> str:
    matches = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>',
        html_text,
        flags=re.I,
    )
    for raw in matches:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        candidates = payload if isinstance(payload, list) else [payload]
        for candidate in candidates:
            if isinstance(candidate, dict) and candidate.get('articleBody'):
                return str(candidate['articleBody']).strip()
    return ''


def extract_article_text(url: str, max_chars: int = 12000) -> str:
    try:
        response = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        html_text = response.text

        jsonld_body = _extract_article_body_from_jsonld(html_text)
        if jsonld_body:
            return jsonld_body[:max_chars]

        cleaned = re.sub(r'(?is)<script[\s\S]*?</script>|<style[\s\S]*?</style>', ' ', html_text)
        cleaned = re.sub(r'(?i)</p>|</div>|</li>|</h[1-6]>', '\n', cleaned)
        cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
        cleaned = html.unescape(cleaned)
        cleaned = re.sub(r'\n\s*\n+', '\n\n', cleaned)
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned[:max_chars]
    except Exception as exc:
        return f'[Failed to fetch article: {exc}]'


def ocr_image(image: Path, lang: str = 'eng') -> str:
    code, stdout, stderr = run(['python3', str(SCRIPT_DIR / 'x_screenshot_ocr.py'), str(image), '--lang', lang])
    if code != 0:
        fail('OCR failed', stderr)
    return stdout


def clean_ocr_lines(text: str) -> list[str]:
    lines = []
    skip_contains = [
        'Post your reply', 'Postyourreply', 'CryptoCondom reposted',
        '@ X.com', 'XX.com', 'al >', 'Qf @', '< Post',
    ]
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line in {'Post', 'Post your reply', 'Postyourreply', 'tom.'}:
            continue
        if any(token in line for token in skip_contains):
            continue
        if 'Post' in line and not line.startswith('@'):
            continue
        if len(line) <= 2:
            continue
        lines.append(line)
    return lines


def parse_screenshot_content(text: str) -> dict:
    lines = clean_ocr_lines(text)
    if not lines:
        fail('No useful text extracted from screenshot')

    body_lines = []
    handle = None
    author = None
    for idx, line in enumerate(lines):
        if line.startswith('@') and handle is None:
            handle = line
            continue
        if author is None and ('BITWU' in line or '.ETH' in line or (idx + 1 < len(lines) and lines[idx + 1].startswith('@'))):
            author = line
            continue
        body_lines.append(line)

    if not body_lines:
        body_lines = lines[:]

    return {
        'author': f"{handle or 'unknown'} ({author or 'unknown'})",
        'body_text': '\n'.join(body_lines).strip(),
        'raw_text': '\n'.join(lines).strip(),
    }


def infer_input_route(raw_input: str | None) -> str:
    if not raw_input:
        return 'unknown'
    candidate = raw_input.strip()
    if candidate.startswith(('http://', 'https://')):
        return 'url'
    path = Path(candidate).expanduser()
    if path.suffix.lower() in IMAGE_SUFFIXES:
        return 'image'
    return 'unknown'


def render_standard_note(
    *,
    source_type: str,
    source_url: str,
    author: str,
    tweet_time: str,
    analysis: dict,
    raw_text: str,
    stored_because: str,
    follow_up: str | None = None,
    extra_sections: list[tuple[str, str]] | None = None,
) -> str:
    lines = [
        f'- Source type: {source_type}',
        f'- Source URL: {format_value(source_url)}',
        f'- Author: {format_value(author)}',
        f'- Tweet time: {format_value(tweet_time)}',
        f'- Type: {format_value(analysis.get("type"))}',
        f'- Topics: {format_value(analysis.get("topics"))}',
        f'- Entities: {format_value(analysis.get("entities"))}',
        f'- Confidence: {format_value(analysis.get("confidence"))}',
        '- Actionability: medium',
        f'- Stored because: {stored_because}',
        '',
        '### Summary',
        format_value(analysis.get('summary')),
        '',
        '### Key claim / Core thesis',
        format_value(analysis.get('thesis')),
        '',
        '### Why it matters',
        format_value(analysis.get('why')),
        '',
        '### Possible implication',
        format_value(analysis.get('implication')),
        '',
        '### Follow-up',
        format_value(follow_up or analysis.get('follow_up')),
    ]

    for title, body in extra_sections or []:
        lines.extend(['', f'### {title}', format_value(body)])

    lines.extend(['', '### Raw / extracted text', format_value(raw_text)])
    return '\n'.join(lines).rstrip() + '\n'
