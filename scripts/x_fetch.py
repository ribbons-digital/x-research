#!/usr/bin/env python3
"""
Fetch a single tweet via xurl CLI and emit a unified JSON payload.
Includes X native article content when available.
"""

from __future__ import annotations

import argparse
import json
import re
from typing import Any, Optional, TypedDict, cast

from x_common import fail, run


ENDPOINT_TEMPLATE = (
    '/2/tweets/{tweet_id}'
    '?tweet.fields=article,created_at,entities,attachments,note_tweet,referenced_tweets'
    '&expansions=author_id,referenced_tweets.id,referenced_tweets.id.author_id,'
    'attachments.media_keys,article.cover_media,article.media_entities'
    '&user.fields=username,name'
    '&media.fields=type,url,preview_image_url,alt_text'
)


class UrlItem(TypedDict, total=False):
    url: str | None
    expanded_url: str | None
    display_url: str | None
    media_key: str | None


class MediaItem(TypedDict, total=False):
    media_key: str
    type: str | None
    url: str | None
    alt_text: str | None


class ArticlePayload(TypedDict):
    title: str
    preview_text: str
    plain_text: str
    cover_media_key: str | None
    cover_media_url: str | None
    media_entities: list[MediaItem]
    urls: list[str]


class ReferencedTweetPayload(TypedDict):
    type: str | None
    id: str | None
    author_handle: str
    author_name: str
    text: str
    note_tweet_text: str
    created_at: str | None


class FetchPayload(TypedDict):
    source_type: str
    source_url: str
    tweet_id: str | None
    author_handle: str
    author_name: str
    tweet_timestamp: str | None
    raw_text: str
    note_tweet_text: str
    urls: list[UrlItem]
    has_media: bool
    media_items: list[MediaItem]
    native_article_url: str | None
    article: ArticlePayload | None
    referenced_tweets: list[ReferencedTweetPayload]


class XurlResponse(TypedDict, total=False):
    data: dict[str, Any]
    includes: dict[str, list[dict[str, Any]]]
    errors: list[dict[str, Any]]


def extract_tweet_id(url: str) -> str:
    match = re.search(r'/status/(\d+)', url)
    if not match:
        fail('Could not parse tweet id from URL')
    return match.group(1)


def fetch_via_xurl(tweet_id: str) -> XurlResponse:
    endpoint = ENDPOINT_TEMPLATE.format(tweet_id=tweet_id)
    code, stdout, stderr = run(['xurl', endpoint])
    if code != 0:
        fail(f'xurl request failed (exit {code})', stderr)
    try:
        return cast(XurlResponse, json.loads(stdout))
    except json.JSONDecodeError as exc:
        fail('Failed to parse xurl JSON output', str(exc))


def _extract_native_article_url(urls: list[UrlItem]) -> str | None:
    for url_item in urls:
        expanded = (url_item.get('expanded_url') or '').strip()
        if 'x.com/i/article/' in expanded or 'twitter.com/i/article/' in expanded:
            return expanded
    return None


def _collect_media(media_keys: list[str], media_by_key: dict[str, dict[str, Any]]) -> list[MediaItem]:
    items: list[MediaItem] = []
    for key in media_keys or []:
        media = media_by_key.get(key, {})
        items.append(
            {
                'media_key': key,
                'type': cast(Optional[str], media.get('type')),
                'url': cast(Optional[str], media.get('url') or media.get('preview_image_url')),
                'alt_text': cast(Optional[str], media.get('alt_text')),
            }
        )
    return items


def _build_article(article_data: dict[str, Any], media_by_key: dict[str, dict[str, Any]]) -> ArticlePayload | None:
    if not article_data:
        return None

    cover_media_key = cast(Optional[str], article_data.get('cover_media'))
    media_entity_keys = cast(list[str], article_data.get('media_entities') or [])

    article: ArticlePayload = {
        'title': cast(str, article_data.get('title') or ''),
        'preview_text': cast(str, article_data.get('preview_text') or ''),
        'plain_text': cast(str, article_data.get('plain_text') or ''),
        'cover_media_key': cover_media_key,
        'cover_media_url': None,
        'media_entities': _collect_media(media_entity_keys, media_by_key),
        'urls': [entry.get('text', '') for entry in (article_data.get('entities', {}) or {}).get('urls', []) if entry.get('text')],
    }

    if cover_media_key:
        cover_media = media_by_key.get(cover_media_key, {})
        article['cover_media_url'] = cast(Optional[str], cover_media.get('url') or cover_media.get('preview_image_url'))

    return article


def build_payload(data: dict[str, Any], includes: dict[str, list[dict[str, Any]]], source_url: str) -> FetchPayload:
    users = {user.get('id'): user for user in includes.get('users', [])}
    media_by_key = {media.get('media_key'): media for media in includes.get('media', [])}
    ref_tweets = {tweet.get('id'): tweet for tweet in includes.get('tweets', [])}

    author = users.get(data.get('author_id'), {})
    urls: list[UrlItem] = []
    for url_item in data.get('entities', {}).get('urls', []) or []:
        urls.append(
            {
                'url': cast(Optional[str], url_item.get('url')),
                'expanded_url': cast(Optional[str], url_item.get('expanded_url')),
                'display_url': cast(Optional[str], url_item.get('display_url')),
                'media_key': cast(Optional[str], url_item.get('media_key')),
            }
        )

    media_items = _collect_media(cast(list[str], data.get('attachments', {}).get('media_keys', []) or []), media_by_key)
    native_article_url = _extract_native_article_url(urls)

    referenced: list[ReferencedTweetPayload] = []
    for ref in data.get('referenced_tweets', []) or []:
        ref_tweet = ref_tweets.get(ref.get('id'), {})
        if not ref_tweet:
            continue
        ref_author = users.get(ref_tweet.get('author_id'), {})
        referenced.append(
            {
                'type': cast(Optional[str], ref.get('type')),
                'id': cast(Optional[str], ref.get('id')),
                'author_handle': ('@' + ref_author.get('username')) if ref_author.get('username') else 'unknown',
                'author_name': cast(str, ref_author.get('name') or 'unknown'),
                'text': cast(str, ref_tweet.get('text', '')),
                'note_tweet_text': cast(str, (ref_tweet.get('note_tweet') or {}).get('text', '')),
                'created_at': cast(Optional[str], ref_tweet.get('created_at')),
            }
        )

    article = _build_article(cast(dict[str, Any], data.get('article') or {}), media_by_key)
    note_tweet_text = cast(str, ((data.get('note_tweet') or {}).get('text') or '').strip())

    return {
        'source_type': 'xurl_api',
        'source_url': source_url,
        'tweet_id': cast(Optional[str], data.get('id')),
        'author_handle': ('@' + author.get('username')) if author.get('username') else 'unknown',
        'author_name': cast(str, author.get('name') or 'unknown'),
        'tweet_timestamp': cast(Optional[str], data.get('created_at')),
        'raw_text': cast(str, data.get('text') or ''),
        'note_tweet_text': note_tweet_text,
        'urls': urls,
        'has_media': bool(media_items),
        'media_items': media_items,
        'native_article_url': native_article_url,
        'article': article,
        'referenced_tweets': referenced,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Fetch a tweet via xurl CLI and emit unified JSON.')
    parser.add_argument('url', help='Tweet URL')
    parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON')
    args = parser.parse_args()

    tweet_id = extract_tweet_id(args.url)
    raw = fetch_via_xurl(tweet_id)
    payload = build_payload(raw.get('data', {}), raw.get('includes', {}), args.url)
    print(json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None))


if __name__ == '__main__':
    main()
