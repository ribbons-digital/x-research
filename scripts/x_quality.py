#!/usr/bin/env python3
"""
Rule-based text analysis for x-research notes.
Provides summarization, quality scoring, type classification,
and topic/entity extraction.
"""

import re
from typing import Iterable, Tuple

# ── Topic / Entity extraction ──────────────────────────────────────────────

TOPIC_RULES = {
    'crypto': [r'\bbtc\b', r'\bbitcoin\b', r'\beth\b', r'\bcrypto\b', r'\btoken\b', r'\bweb3\b', r'代币', r'加密'],
    'etf': [r'\betf\b', r'ibit', r'arkb', r'fbtc'],
    'macro': [r'\bfed\b', r'\brates?\b', r'inflation', r'cpi', r'ppi', r'macro', r'通胀', r'利率', r'宏观'],
    'oil': [r'\boil\b', r'\bwti\b', r'\bbrent\b', r'hormuz', r'strait of hormuz', r'原油', r'石油', r'霍尔木兹'],
    'geopolitics': [r'iran', r'israel', r'war', r'geopolit', r'中东', r'地缘', r'战争'],
    'ai': [r'\bai\b', r'agent', r'openai', r'anthropic', r'gemini', r'人工智能', r'智能体'],
    'ai-infra': [r'data center', r'gpu', r'compute', r'inference', r'ai infra', r'数据中心', r'算力'],
    'regulation': [r'sec', r'filing', r'no action', r'regulation', r'监管', r'合规'],
}

ENTITY_PATTERNS = [
    r'@[A-Za-z0-9_]+',
    r'\b[A-Z]{2,6}\b',
    r'\b(?:OpenAI|Anthropic|CoinMarketCap|Binance|BlackRock|Animoca Brands|AnimocaMinds|DTCC|DTC|Fed|SEC)\b',
    r'(?:贝莱德|币安|美国证券交易委员会|美联储|OpenAI|Anthropic)'
]


def extract_topics_and_entities(text: str) -> Tuple[list[str], list[str]]:
    lower = text.lower()
    topics = []
    for topic, patterns in TOPIC_RULES.items():
        for pat in patterns:
            if re.search(pat, lower, re.I):
                topics.append(topic)
                break

    entities = []
    for pat in ENTITY_PATTERNS:
        for m in re.findall(pat, text):
            ent = m.strip()
            if ent and ent not in entities:
                entities.append(ent)

    return topics, entities[:12]


# ── Summarization & Quality ──────────────────────────────────────────────────

def normalize_text(text: str) -> str:
    text = text.replace('\u202f', ' ')
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def sentence_chunks(text: str) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []
    parts = re.split(r'(?<=[.!?。！？])\s+|\n+', text)
    out = []
    for p in parts:
        p = p.strip(' \t-•')
        if len(p) >= 8:
            out.append(p)
    if not out and text:
        out = [text]
    return out


def summarize_note(text: str, source_type: str = 'analysis') -> Tuple[str, str, str, str, str, str]:
    chunks = sentence_chunks(text)
    if not chunks:
        return '', '', source_type, 'Content could not be cleanly extracted.', 'No reliable implication yet.', 'Verify the source content or provide a cleaner input.'

    summary = ' '.join(chunks[:2])
    thesis = chunks[0]

    lower = text.lower()
    source_type_out = source_type
    if any(x in lower for x in ['rumor', 'unconfirmed', 'hearing', '可能', '傳聞']):
        source_type_out = 'rumor'
    elif any(x in lower for x in ['i think', 'imo', '我認為', '我覺得']):
        source_type_out = 'opinion'
    elif any(x in lower for x in ['data', 'flows', 'filing', 'announced', 'according to', '數據', '公告']):
        source_type_out = 'analysis'

    why = 'Useful as a research input for tracking narrative, source views, and possible catalysts.'
    implication = 'If this view is reinforced by other credible sources, it may strengthen a broader thesis or watchlist item.'
    follow_up = 'Compare with related items from other sources and verify whether the claim is factual, opinionated, or early narrative formation.'
    return summary, thesis, source_type_out, why, implication, follow_up


def quality_score(text: str) -> str:
    t = normalize_text(text)
    if len(t) > 280:
        return 'high'
    if len(t) > 80:
        return 'medium'
    return 'low'


# ── CLI (optional) ───────────────────────────────────────────────────────────

def main():
    import argparse
    import sys
    ap = argparse.ArgumentParser(description='Analyze text for x-research quality, topics, and entities.')
    ap.add_argument('--text', help='Input text')
    ap.add_argument('--file', help='Input file path')
    ap.add_argument('--json', action='store_true', help='Emit JSON')
    args = ap.parse_args()

    raw = args.text or (Path(args.file).expanduser().read_text() if args.file else None)
    if not raw:
        print('Provide --text or --file', file=sys.stderr)
        sys.exit(1)

    summary, thesis, typ, why, implication, follow_up = summarize_note(raw)
    confidence = quality_score(raw)
    topics, entities = extract_topics_and_entities(raw)

    if args.json:
        import json
        print(json.dumps({
            'summary': summary,
            'thesis': thesis,
            'type': typ,
            'why': why,
            'implication': implication,
            'follow_up': follow_up,
            'confidence': confidence,
            'topics': topics,
            'entities': entities,
        }, ensure_ascii=False, indent=2))
    else:
        print(f'Summary: {summary}')
        print(f'Thesis: {thesis}')
        print(f'Type: {typ}')
        print(f'Confidence: {confidence}')
        print(f'Topics: {topics}')
        print(f'Entities: {entities}')


if __name__ == '__main__':
    from pathlib import Path
    main()
