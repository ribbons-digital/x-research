import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS_DIR))

import x_common  # noqa: E402
import x_fetch  # noqa: E402
import x_research  # noqa: E402


class XResearchTests(unittest.TestCase):
    def test_build_payload_extracts_article_body(self):
        data = {
            'id': '123',
            'author_id': 'u1',
            'text': 'https://t.co/abc',
            'created_at': '2026-05-22T00:00:00.000Z',
            'entities': {
                'urls': [
                    {
                        'url': 'https://t.co/abc',
                        'expanded_url': 'https://x.com/i/article/999',
                        'display_url': 'x.com/i/article/999',
                    }
                ]
            },
            'article': {
                'title': 'Native article title',
                'preview_text': 'Preview body',
                'plain_text': 'Full native article body',
                'cover_media': 'm1',
                'media_entities': ['m2'],
                'entities': {'urls': [{'text': 'https://example.com/source'}]},
            },
            'attachments': {'media_keys': ['m3']},
            'referenced_tweets': [],
        }
        includes = {
            'users': [{'id': 'u1', 'username': 'alice', 'name': 'Alice'}],
            'media': [
                {'media_key': 'm1', 'type': 'photo', 'url': 'https://img/cover.jpg'},
                {'media_key': 'm2', 'type': 'photo', 'preview_image_url': 'https://img/embedded.jpg'},
                {'media_key': 'm3', 'type': 'photo', 'url': 'https://img/tweet.jpg'},
            ],
            'tweets': [],
        }

        payload = x_fetch.build_payload(data, includes, 'https://x.com/alice/status/123')

        self.assertEqual(payload['author_handle'], '@alice')
        self.assertEqual(payload['native_article_url'], 'https://x.com/i/article/999')
        self.assertEqual(payload['article']['plain_text'], 'Full native article body')
        self.assertEqual(payload['article']['cover_media_url'], 'https://img/cover.jpg')
        self.assertEqual(payload['article']['media_entities'][0]['url'], 'https://img/embedded.jpg')

    def test_extract_first_external_url_ignores_x_links(self):
        item = {
            'urls': [
                {'expanded_url': 'https://x.com/i/article/123'},
                {'expanded_url': 'https://example.com/post'},
            ]
        }
        self.assertEqual(x_common.extract_first_external_url(item), 'https://example.com/post')

    def test_build_combined_text_prefers_native_article_body(self):
        item = {
            'raw_text': 'short tweet',
            'article': {'title': 'Deep dive', 'plain_text': 'Long article body'},
            'referenced_tweets': [{'author_handle': '@bob', 'text': 'quoted context'}],
        }
        combined = x_common.build_combined_text(item)
        self.assertIn('Deep dive', combined)
        self.assertIn('Long article body', combined)
        self.assertIn('quoted context', combined)
        self.assertNotEqual(combined.splitlines()[0], 'short tweet')

    def test_infer_input_route_detects_url_and_image(self):
        self.assertEqual(x_common.infer_input_route('https://x.com/alice/status/123'), 'url')
        self.assertEqual(x_common.infer_input_route('/tmp/post.jpg'), 'image')
        self.assertEqual(x_common.infer_input_route('not-a-route'), 'unknown')

    def test_parse_screenshot_content_extracts_author_and_body(self):
        raw = '\n'.join([
            'Alice Research',
            '@alice',
            'This is the first line of the post.',
            'Second line of the post.',
            'Post your reply',
        ])
        parsed = x_common.parse_screenshot_content(raw)
        self.assertEqual(parsed['author'], '@alice (Alice Research)')
        self.assertIn('This is the first line of the post.', parsed['body_text'])
        self.assertNotIn('Post your reply', parsed['raw_text'])

    def test_base_result_schema_is_stable(self):
        result = x_research._base_result(
            'tweet',
            '@alice (Alice)',
            None,
            'https://x.com/alice/status/123',
            '2026-05-22T00:00:00.000Z',
        )
        self.assertEqual(
            result,
            {
                'route': 'tweet',
                'author': '@alice (Alice)',
                'tweet_time': '2026-05-22T00:00:00.000Z',
                'source_url': 'https://x.com/alice/status/123',
                'stored_to': None,
            },
        )


if __name__ == '__main__':
    unittest.main()
