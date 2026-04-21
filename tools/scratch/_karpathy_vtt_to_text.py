"""VTT -> plain text for Karpathy session batch.

Converts all *.en.vtt files in tools/scratch/karpathy/ into matching *.txt files
(strips timestamps, cue indices, tags, collapses duplicate consecutive lines).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCRATCH = Path('tools/scratch/karpathy')

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
        if line.isdigit():
            continue
        line = TAG_RE.sub('', line)
        line = re.sub(r'\s+', ' ', line).strip()
        if line and line != prev:
            lines.append(line)
            prev = line
    text = ' '.join(lines)
    return re.sub(r'\s+', ' ', text).strip()


def main() -> None:
    if not SCRATCH.exists():
        print(f'No scratch dir: {SCRATCH}', file=sys.stderr)
        sys.exit(1)
    for vtt in sorted(SCRATCH.glob('*.en.vtt')):
        text = vtt_to_text(vtt)
        out = vtt.with_suffix('').with_suffix('.txt')
        out.write_text(text, encoding='utf-8')
        print(f'{vtt.name} -> {out.name}  ({len(text.split())} words, {len(text)} chars)')


if __name__ == '__main__':
    main()
