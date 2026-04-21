"""VTT -> plain text + keyword/overlap analysis.

Writes one .txt per video and prints an evaluation table to stdout.
"""
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
    # secondary signals
    'mcp': r'\b(model context protocol|mcp)\b',
    'rag': r'\brag\b',
    'embedding': r'\bembeddings?\b',
    'vector db': r'\bvector ?(?:db|database)s?\b',
}

TIMESTAMP_RE = re.compile(r'\d\d:\d\d:\d\d\.\d{3}\s+-->\s+\d\d:\d\d:\d\d\.\d{3}.*')
TAG_RE = re.compile(r'<[^>]+>')


def vtt_to_text(vtt_path: Path) -> str:
    raw = vtt_path.read_text(encoding='utf-8', errors='replace')
    lines: list[str] = []
    prev = ''
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith(('WEBVTT', 'Kind:', 'Language:', 'NOTE')):
            continue
        if TIMESTAMP_RE.match(line):
            continue
        if line.isdigit():  # cue index
            continue
        line = TAG_RE.sub('', line)
        line = re.sub(r'\s+', ' ', line).strip()
        if line and line != prev:  # collapse consecutive duplicates (auto-sub repeat)
            lines.append(line)
            prev = line
    text = ' '.join(lines)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def count_keywords(text: str) -> dict[str, int]:
    t = text.lower()
    return {k: len(re.findall(v, t)) for k, v in KEYWORDS.items()}


def load_ai_infra_corpus() -> str:
    parts = []
    for md in AI_INFRA.glob('*.md'):
        try:
            parts.append(md.read_text(encoding='utf-8', errors='replace').lower())
        except Exception:
            pass
    return '\n'.join(parts)


def overlap_terms(text: str, corpus: str, top_n: int = 20) -> list[tuple[str, int]]:
    """Rough noun/term overlap: find distinctive multi-letter tokens shared with corpus."""
    stop = set(
        ('the a an and or but if then so of to in on at for with from by is are was were be been being '
         'this that these those it its as not no do does did have has had will would can could should '
         'you your we our they them he she his her i me my about into over under than also just one two '
         'very really like kind know going get got make made use used using see want say says said thing '
         'things way ways something someone anything anyone because around right back out up down there '
         'here now then before after while between across through each every any some all most many much '
         'how what why when where who which whom whose other others different same new old good great'
        ).split()
    )
    tokens = re.findall(r"[a-zA-Z][a-zA-Z_+\-]{3,}", text.lower())
    tokens = [t for t in tokens if t not in stop]
    counts = Counter(tokens)
    # Only terms appearing >= 3x in video and also present in ai-infra corpus
    shared = [(term, n) for term, n in counts.most_common(200) if n >= 3 and term in corpus]
    return shared[:top_n]


def main() -> None:
    top5 = json.loads(Path('tools/scratch/gopher_top5.json').read_text(encoding='utf-8'))
    corpus = load_ai_infra_corpus()

    results = []
    for entry in top5:
        vid = entry['id']
        vtt = SCRATCH / f'{vid}.en.vtt'
        if not vtt.exists():
            continue
        text = vtt_to_text(vtt)
        (SCRATCH / f'{vid}.txt').write_text(text, encoding='utf-8')
        kws = count_keywords(text)
        ov = overlap_terms(text, corpus)
        results.append({
            'id': vid,
            'title': entry['title'],
            'views': entry['view_count'],
            'words': len(text.split()),
            'keywords': kws,
            'overlap_terms': ov,
        })

    Path('tools/scratch/gopher_analysis.json').write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8'
    )

    # Console summary
    for r in results:
        print(f"\n=== {r['id']}  {r['views']:,} views  {r['words']} words")
        print(f"    {r['title']}")
        hits = ', '.join(f"{k}={v}" for k, v in r['keywords'].items() if v > 0) or '(no primary AI keywords)'
        print(f"    keywords: {hits}")
        if r['overlap_terms']:
            print(f"    ai-infra shared terms: {', '.join(f'{t}×{n}' for t,n in r['overlap_terms'][:12])}")
        else:
            print('    ai-infra shared terms: none above threshold')


if __name__ == '__main__':
    main()
