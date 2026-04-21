"""Analyze the 4 expand-slice AI videos — same approach as _vtt_to_text.py."""
from __future__ import annotations

import json
import re
from pathlib import Path
from collections import Counter

SCRATCH = Path('tools/scratch/gopher')
AI_INFRA = Path('memory/knowledge/ai-infra')

KEYWORDS = {
    'agent': r'\bagents?\b',
    'harness': r'\bharness\b',
    'llm': r'\bllms?\b',
    'claude': r'\bclaude\b',
    'orchestration': r'\borchestrat(?:ion|e|or|ing)\b',
    'mcp': r'\b(model context protocol|mcp)\b',
    'rag': r'\brag\b',
    'embedding': r'\bembeddings?\b',
    'vector db': r'\bvector ?(?:db|database)s?\b',
}

VIDEOS = [
    ('Kq8Iz9tTcSo', 'Large Language Models (LLMs) Explained', 9600),
    ('j3RmMc9wkbM', 'Meta now has the most insane AI agent', 4994),
    ('IieuQlnrgT8', 'How RAG Changed The World (In 2025)', 1280),
    ('Ps913CUN1Tw', 'Vector Databases: The Secret Weapon for AI Search', 883),
]

TIMESTAMP_RE = re.compile(r'\d\d:\d\d:\d\d\.\d{3}\s+-->\s+\d\d:\d\d:\d\d\.\d{3}.*')
TAG_RE = re.compile(r'<[^>]+>')


def vtt_to_text(p: Path) -> str:
    raw = p.read_text(encoding='utf-8', errors='replace')
    out: list[str] = []
    prev = ''
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith(('WEBVTT', 'Kind:', 'Language:', 'NOTE')):
            continue
        if TIMESTAMP_RE.match(line) or line.isdigit():
            continue
        line = re.sub(r'\s+', ' ', TAG_RE.sub('', line)).strip()
        if line and line != prev:
            out.append(line)
            prev = line
    return re.sub(r'\s+', ' ', ' '.join(out)).strip()


def count_kw(t: str) -> dict[str, int]:
    low = t.lower()
    return {k: len(re.findall(v, low)) for k, v in KEYWORDS.items()}


def overlap(text: str, corpus: str, top_n: int = 15) -> list[tuple[str, int]]:
    stop = set((
        'the a an and or but if then so of to in on at for with from by is are was were be been being '
        'this that these those it its as not no do does did have has had will would can could should '
        'you your we our they them he she his her i me my about into over under than also just one two '
        'very really like kind know going get got make made use used using see want say says said thing '
        'things way ways something someone anything anyone because around right back out up down there '
        'here now then before after while between across through each every any some all most many much '
        'how what why when where who which whom whose other others different same new old good great'
    ).split())
    toks = re.findall(r"[a-zA-Z][a-zA-Z_+\-]{3,}", text.lower())
    toks = [t for t in toks if t not in stop]
    c = Counter(toks)
    return [(w, n) for w, n in c.most_common(200) if n >= 3 and w in corpus][:top_n]


def main() -> None:
    corpus = '\n'.join(
        p.read_text(encoding='utf-8', errors='replace').lower() for p in AI_INFRA.glob('*.md')
    )
    results = []
    for vid, title, views in VIDEOS:
        vtt = SCRATCH / f'{vid}.en.vtt'
        if not vtt.exists():
            print(f'MISSING: {vid}')
            continue
        text = vtt_to_text(vtt)
        (SCRATCH / f'{vid}.txt').write_text(text, encoding='utf-8')
        kws = count_kw(text)
        ov = overlap(text, corpus)
        results.append(dict(id=vid, title=title, views=views, words=len(text.split()),
                            keywords=kws, overlap_terms=ov))
    Path('tools/scratch/gopher_expand_analysis.json').write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
    for r in results:
        print(f"\n=== {r['id']}  {r['views']:,} views  {r['words']} words")
        print(f"    {r['title']}")
        hits = ', '.join(f"{k}={v}" for k, v in r['keywords'].items() if v > 0) or '(no primary AI keywords)'
        print(f"    keywords: {hits}")
        if r['overlap_terms']:
            tops = ', '.join(f"{w}x{n}" for w, n in r['overlap_terms'][:10])
            print(f"    ai-infra shared terms: {tops}")
        else:
            print('    ai-infra shared terms: none above threshold')


if __name__ == '__main__':
    main()
