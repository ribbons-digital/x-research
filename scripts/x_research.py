#!/usr/bin/env python3
"""Unified x-research entrypoint for URL, text, file, and screenshot inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from x_common import (
    analyze_text,
    append_note,
    article_text,
    build_combined_text,
    extract_article_text,
    extract_first_external_url,
    fetch_payload,
    format_referenced_tweets,
    infer_input_route,
    ocr_image,
    parse_screenshot_content,
    render_standard_note,
    resolve_output_dir,
)


def _base_result(route: str, author: str, stored_to: str | None = None, source_url: str | None = None, tweet_time: str | None = None) -> dict[str, Any]:
    return {
        'route': route,
        'author': author,
        'tweet_time': tweet_time,
        'source_url': source_url,
        'stored_to': stored_to,
    }


def _print_analysis(analysis: dict) -> None:
    print('Summary:')
    print(analysis['summary'])
    print('\nKey claim / Core thesis:')
    print(analysis['thesis'])
    print('\nType:')
    print(analysis['type'])
    print('\nWhy it matters:')
    print(analysis['why'])
    print('\nPossible implication:')
    print(analysis['implication'])
    print('\nConfidence:')
    print(analysis['confidence'])


def _print_result(result: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if result.get('stored_to'):
        print(f"Stored to: {result['stored_to']}\n")

    metadata = result.get('metadata') or {}
    print(f"Author: {result.get('author')}")
    if result.get('tweet_time'):
        print(f"Tweet time: {result['tweet_time']}")
    print(f"Route: {result.get('route')}")
    for key, value in metadata.items():
        label = key.replace('_', ' ').title()
        print(f'{label}: {value}')
    print()
    _print_analysis(result['analysis'])


def _store_note(note_body: str, output_dir: Path, heading: str, should_store: bool) -> str | None:
    if not should_store:
        return None
    inbox = append_note(note_body, output_dir, heading)
    return str(inbox)


def _research_url(url: str, output_dir: Path, should_store: bool, article_max_chars: int, prefer_external: bool) -> dict[str, Any]:
    item = fetch_payload(url)
    author = f"{item.get('author_handle')} ({item.get('author_name')})"
    tweet_time = item.get('tweet_timestamp') or 'unknown'
    tweet_text = (item.get('note_tweet_text') or item.get('raw_text') or '').strip()
    article = item.get('article') or {}
    native_article_body = article_text(item)
    native_article_url = item.get('native_article_url')
    external_article_url = extract_first_external_url(item)

    use_external_branch = bool(external_article_url and (prefer_external or not native_article_body))

    if use_external_branch:
        external_article_text = extract_article_text(external_article_url, article_max_chars)
        combined_text = '\n\n'.join(part for part in [tweet_text, external_article_text] if part).strip()
        analysis = analyze_text(combined_text)
        note_body = render_standard_note(
            source_type='xurl_api + external_article',
            source_url=url,
            author=author,
            tweet_time=tweet_time,
            analysis=analysis,
            raw_text=combined_text,
            stored_because='Tweet referenced an external article worth preserving with context.',
            follow_up='Validate the external article independently; this branch still depends on webpage extraction quality.',
            extra_sections=[
                ('Tweet text', tweet_text or 'N/A'),
                ('Article URL', external_article_url),
                ('Article excerpt', external_article_text or 'N/A'),
                ('Referenced tweets', format_referenced_tweets(item.get('referenced_tweets') or [])),
                ('Native article URL', native_article_url or 'N/A'),
            ],
        )
        return {
            **_base_result('external_article', author, _store_note(note_body, output_dir, 'tweet + article item', should_store), url, tweet_time),
            'analysis': analysis,
            'raw_text': combined_text,
            'note_body': note_body,
            'metadata': {
                'article_url': external_article_url,
                'article_extracted': 'yes' if external_article_text else 'no',
                'referenced_tweets': len(item.get('referenced_tweets', [])),
                'native_article_url': native_article_url or 'N/A',
            },
        }

    combined_text = build_combined_text(item)
    analysis = analyze_text(combined_text)
    has_native_article_body = bool(native_article_body)

    if has_native_article_body:
        analysis['why'] = 'This post contains an X native article body returned directly by the X API article field, so the long-form content is available without brittle HTML scraping.'
        analysis['implication'] = 'Native long-form posts can be researched directly from xurl/X API when the article field is requested, which makes this route materially more reliable than OCR or webpage scraping.'
        analysis['follow_up'] = 'Validate the thesis against referenced tweets or linked sources, then store the full article text if it is decision-useful.'

    follow_up = analysis.get('follow_up')
    if item.get('has_media') and not has_native_article_body:
        follow_up = 'This post includes media; OCR/image analysis may still add context beyond the text payload.'

    note_body = render_standard_note(
        source_type='xurl_api_article' if has_native_article_body else 'xurl_api',
        source_url=item.get('source_url') or url,
        author=author,
        tweet_time=tweet_time,
        analysis=analysis,
        raw_text=native_article_body or tweet_text,
        stored_because='X API returned structured post content worth retaining.' if not has_native_article_body else 'X API returned the full native article body, which is durable long-form source material.',
        follow_up=follow_up,
        extra_sections=[
            ('Article title', article.get('title') or 'N/A'),
            ('Article preview', article.get('preview_text') or 'N/A'),
            ('Referenced tweets', format_referenced_tweets(item.get('referenced_tweets') or [])),
            ('Native article URL', native_article_url or 'N/A'),
            ('External article URL', external_article_url or 'N/A'),
        ],
    )
    route = 'native_article' if has_native_article_body else 'tweet'
    return {
        **_base_result(route, author, _store_note(note_body, output_dir, 'x api url item', should_store), item.get('source_url') or url, tweet_time),
        'analysis': analysis,
        'raw_text': native_article_body or tweet_text,
        'note_body': note_body,
        'metadata': {
            'has_media': item.get('has_media'),
            'referenced_tweets': len(item.get('referenced_tweets', [])),
            'native_article_url': native_article_url or 'N/A',
            'external_article_url': external_article_url or 'N/A',
            'article_body_via_x_api': 'yes' if has_native_article_body else 'no',
        },
    }


def _research_text(raw_text: str, output_dir: Path, should_store: bool, author: str, source_url: str) -> dict[str, Any]:
    analysis = analyze_text(raw_text)
    note = render_standard_note(
        source_type='pasted text',
        source_url=source_url,
        author=author,
        tweet_time='unknown',
        analysis=analysis,
        raw_text=raw_text,
        stored_because='Pasted text produced readable content worth retaining.',
    )
    return {
        **_base_result('pasted_text', author, _store_note(note, output_dir, 'pasted text item', should_store), source_url, 'unknown'),
        'analysis': analysis,
        'raw_text': raw_text,
        'note_body': note,
        'metadata': {},
    }


def _research_image(image: Path, output_dir: Path, should_store: bool, lang: str) -> dict[str, Any]:
    raw_ocr = ocr_image(image, lang)
    parsed = parse_screenshot_content(raw_ocr)
    analysis = analyze_text(parsed['body_text'])
    note = render_standard_note(
        source_type='screenshot OCR',
        source_url='N/A',
        author=parsed['author'],
        tweet_time='unknown',
        analysis=analysis,
        raw_text=parsed['raw_text'],
        stored_because='Screenshot fallback produced readable content worth retaining.',
    )
    return {
        **_base_result('screenshot', parsed['author'], _store_note(note, output_dir, 'screenshot item', should_store), str(image), 'unknown'),
        'analysis': analysis,
        'raw_text': parsed['raw_text'],
        'note_body': note,
        'metadata': {
            'ocr_lang': lang,
        },
    }


def main(default_route: str = 'auto', force_store: bool = False, prefer_external_default: bool = False) -> None:
    parser = argparse.ArgumentParser(description='Unified x-research entrypoint.')
    parser.add_argument('input', nargs='?', help='Tweet URL or screenshot image path')
    parser.add_argument('--text', help='Pasted text content')
    parser.add_argument('--file', help='Path to text file')
    parser.add_argument('--author', default='unknown')
    parser.add_argument('--source-url', default='N/A')
    parser.add_argument('--store', action='store_true', help='Append to inbox markdown')
    parser.add_argument('--output-dir', type=Path, help='Inbox directory override')
    parser.add_argument('--lang', default='eng', help='OCR language for screenshot route')
    parser.add_argument('--article-max-chars', type=int, default=12000, help='Max external article text length')
    parser.add_argument('--route', choices=['auto', 'url', 'external', 'text', 'image'], default=default_route)
    parser.add_argument('--prefer-external', action='store_true', default=prefer_external_default, help='Prefer the external article branch when a non-X link exists')
    parser.add_argument('--json', action='store_true', help='Emit standardized JSON result schema')
    args = parser.parse_args()

    output_dir = resolve_output_dir(args.output_dir)
    should_store = force_store or args.store

    if args.text and args.file:
        raise SystemExit('Use only one of --text or --file')

    if args.route == 'text' or args.text or args.file:
        raw = args.text if args.text is not None else Path(args.file).expanduser().read_text()
        if not raw.strip():
            raise SystemExit('No readable text provided')
        result = _research_text(raw.strip(), output_dir, should_store, args.author, args.source_url)
        _print_result(result, args.json)
        return

    if not args.input:
        raise SystemExit('Provide a tweet URL, screenshot path, --text, or --file')

    route = args.route
    if route == 'auto':
        route = infer_input_route(args.input)
        if route == 'unknown':
            raise SystemExit('Could not infer input type; use --route url|image|text|external')

    if route in {'url', 'external'}:
        result = _research_url(
            url=args.input,
            output_dir=output_dir,
            should_store=should_store,
            article_max_chars=args.article_max_chars,
            prefer_external=args.prefer_external or route == 'external',
        )
        _print_result(result, args.json)
        return

    if route == 'image':
        image = Path(args.input).expanduser()
        if not image.exists():
            raise SystemExit(f'Image not found: {image}')
        result = _research_image(image, output_dir, should_store, args.lang)
        _print_result(result, args.json)
        return

    raise SystemExit(f'Unsupported route: {route}')


if __name__ == '__main__':
    main()
