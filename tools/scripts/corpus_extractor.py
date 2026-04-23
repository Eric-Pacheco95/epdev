#!/usr/bin/env python3
"""Deterministic helpers for large-corpus YouTube extraction (metadata, subs, VTT cleanup, overlap scan, queue).

LLM judgment stays in `.claude/skills/extract-corpus/SKILL.md`. This module is subprocess + filesystem only.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_CORPUS_DIRS = (
    Path('memory/knowledge/ai-infra'),
    Path('memory/knowledge/foundation-ml'),
)

KEYWORDS: dict[str, str] = {
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

TIMESTAMP_RE = re.compile(
    r'\d{1,2}:\d{2}:\d{2}(\.\d{3})?\s+-->\s+\d{1,2}:\d{2}:\d{2}(\.\d{3})?.*'
)
TAG_RE = re.compile(r'<[^>]+>')

STOPWORDS = set(
    """the a an and or but if then so of to in on at for with from by is are was were be been being
    this that these those it its as not no do does did have has had will would can could should
    you your we our they them he she his her i me my about into over under than also just one two
    very really like kind know going get got make made use used using see want say says said thing
    things way ways something someone anything anyone because around right back out up down there
    here now then before after while between across through each every any some all most many much
    how what why when where who which whom whose other others different same new old good great
    """.split()
)


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


def count_keywords(text: str) -> dict[str, int]:
    t = text.lower()
    return {k: len(re.findall(v, t)) for k, v in KEYWORDS.items()}


def load_corpus_text(corpus_dirs: tuple[Path, ...]) -> str:
    parts: list[str] = []
    for root in corpus_dirs:
        if not root.exists():
            continue
        for md in sorted(root.glob('*.md')):
            try:
                parts.append(md.read_text(encoding='utf-8', errors='replace').lower())
            except OSError:
                continue
    return '\n'.join(parts)


def overlap_terms(text: str, corpus: str, top_n: int = 20) -> list[tuple[str, int]]:
    tokens = re.findall(r'[a-zA-Z][a-zA-Z_+\-]{3,}', text.lower())
    tokens = [t for t in tokens if t not in STOPWORDS]
    counts = Counter(tokens)
    shared = [(term, n) for term, n in counts.most_common(400) if n >= 3 and term in corpus]
    return shared[:top_n]


def _run_ytdlp(args: list[str], timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ['yt-dlp', *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding='utf-8',
        errors='replace',
    )


def cmd_metadata_playlist(url: str, out: Path, playlist_end: int | None = None) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    args: list[str] = ['-q', '--no-progress', '--flat-playlist', '-j']
    if playlist_end is not None:
        args.extend(['--playlist-end', str(playlist_end)])
    args.append(url)
    proc = _run_ytdlp(args)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode
    out.write_text(proc.stdout, encoding='utf-8')
    return 0


def cmd_fetch_subs(video_id: str, out_dir: Path, sleep_interval: float = 2.0) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    url = f'https://www.youtube.com/watch?v={video_id}'
    template = str(out_dir / '%(id)s.%(ext)s')
    proc = _run_ytdlp(
        [
            '-q',
            '--no-progress',
            '--write-auto-sub',
            '--sub-langs',
            'en.*,en',
            '--skip-download',
            '--sleep-interval',
            str(sleep_interval),
            '-o',
            template,
            url,
        ]
    )
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode
    return 0


def cmd_vtt_to_text(in_dir: Path, pattern: str = '*.en.vtt') -> int:
    if not in_dir.exists():
        print(f'Missing directory: {in_dir}', file=sys.stderr)
        return 1
    n = 0
    for vtt in sorted(in_dir.glob(pattern)):
        text = vtt_to_text(vtt)
        out = vtt.with_suffix('').with_suffix('.txt')
        out.write_text(text, encoding='utf-8')
        print(f'{vtt.name} -> {out.name}  ({len(text.split())} words, {len(text)} chars)')
        n += 1
    if not n:
        print(f'No files matched {in_dir}/{pattern}', file=sys.stderr)
        return 1
    return 0


def _analyze_one_transcript(text: str, title: str, vid: str, corpus: str) -> dict[str, Any]:
    kws = count_keywords(text)
    ov = overlap_terms(text, corpus)
    return {
        'id': vid,
        'title': title,
        'words': len(text.split()),
        'keywords': kws,
        'overlap_terms': ov,
    }


def cmd_overlap_scan(
    transcript: Path,
    corpus_dirs: tuple[Path, ...],
    out: Path | None,
) -> int:
    corpus = load_corpus_text(corpus_dirs)
    text = transcript.read_text(encoding='utf-8', errors='replace')
    vid = transcript.stem.split('.')[0] if transcript.suffix == '.txt' else transcript.stem
    row = _analyze_one_transcript(text, title=vid, vid=vid, corpus=corpus)
    payload = json.dumps(row, indent=2, ensure_ascii=False)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload, encoding='utf-8')
    print(payload)
    return 0


def cmd_overlap_scan_dir(
    in_dir: Path,
    corpus_dirs: tuple[Path, ...],
    out: Path,
) -> int:
    corpus = load_corpus_text(corpus_dirs)
    results: list[dict[str, Any]] = []
    for txt in sorted(in_dir.glob('*.txt')):
        text = txt.read_text(encoding='utf-8', errors='replace')
        vid = txt.stem.split('.')[0]
        results.append(_analyze_one_transcript(text, title=txt.stem, vid=vid, corpus=corpus))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Wrote {out} ({len(results)} transcripts)')
    return 0


def _normalize_pending_entry(entry: Any) -> tuple[str, dict[str, Any] | None]:
    if isinstance(entry, str):
        return entry, None
    if isinstance(entry, dict) and 'id' in entry:
        return str(entry['id']), entry
    raise ValueError(f'Unsupported pending entry: {entry!r}')


def cmd_queue_pop(queue_path: Path, n: int, popped_out: Path | None) -> int:
    data = json.loads(queue_path.read_text(encoding='utf-8'))
    popped_ids: list[str] = []
    popped_meta: list[dict[str, Any]] = []

    pending = data.get('pending') or []
    if pending:
        for _ in range(min(n, len(pending))):
            raw = pending.pop(0)
            vid, meta = _normalize_pending_entry(raw)
            popped_ids.append(vid)
            if meta:
                popped_meta.append(meta)
    else:
        meta_list = list(data.get('pending_metadata') or [])
        meta_list.sort(key=lambda m: m.get('priority', 0))
        chunk = meta_list[:n]
        data['pending_metadata'] = meta_list[n:]
        for m in chunk:
            popped_ids.append(str(m['id']))
            popped_meta.append(m)

    proc = data.setdefault('processed', [])
    for vid in popped_ids:
        if vid not in proc:
            proc.append(vid)

    queue_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    summary = {'ids': popped_ids, 'metadata': popped_meta}
    if popped_out:
        popped_out.parent.mkdir(parents=True, exist_ok=True)
        popped_out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(summary, indent=2))
    return 0


def cmd_queue_append_written(queue_path: Path, paths: list[str]) -> int:
    data = json.loads(queue_path.read_text(encoding='utf-8'))
    wf = data.setdefault('written_files', [])
    for p in paths:
        if p not in wf:
            wf.append(p)
    queue_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    return 0


def cmd_scratch_clean(glob_pat: str, apply_delete: bool) -> int:
    paths = sorted(Path().glob(glob_pat))
    if not paths:
        print(f'No matches for glob {glob_pat!r}')
        return 0
    for p in paths:
        if apply_delete:
            p.unlink(missing_ok=True)
            print(f'deleted {p}')
        else:
            print(f'would delete {p}')
    return 0


def _parse_corpus_dirs(raw: list[str] | None) -> tuple[Path, ...]:
    if not raw:
        return DEFAULT_CORPUS_DIRS
    return tuple(Path(p) for p in raw)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description='Corpus extraction helpers (no LLM).')
    sub = p.add_subparsers(dest='cmd', required=True)

    m = sub.add_parser('metadata-playlist', help='yt-dlp flat playlist JSONL to file')
    m.add_argument('--url', required=True)
    m.add_argument('--out', type=Path, required=True)
    m.add_argument(
        '--playlist-end',
        type=int,
        default=None,
        metavar='N',
        help='pass through to yt-dlp --playlist-end (smoke tests / bounded enum)',
    )

    f = sub.add_parser('fetch-subs', help='yt-dlp auto subs for one video id')
    f.add_argument('--id', required=True, dest='video_id')
    f.add_argument('--out-dir', type=Path, required=True)
    f.add_argument('--sleep-interval', type=float, default=2.0)

    v = sub.add_parser('vtt-to-text', help='strip cues from VTT -> sibling .txt')
    v.add_argument('--in-dir', type=Path, required=True)
    v.add_argument('--pattern', default='*.en.vtt')

    o = sub.add_parser('overlap-scan', help='keyword + corpus overlap for one .txt transcript')
    o.add_argument('--transcript', type=Path, required=True)
    o.add_argument('--corpus-dir', action='append', dest='corpus_dirs')
    o.add_argument('--out', type=Path)

    od = sub.add_parser('overlap-scan-dir', help='overlap scan for all *.txt in a directory')
    od.add_argument('--in-dir', type=Path, required=True)
    od.add_argument('--corpus-dir', action='append', dest='corpus_dirs')
    od.add_argument('--out', type=Path, required=True)

    q = sub.add_parser('queue-pop', help='pop N ids from pending or pending_metadata')
    q.add_argument('--queue', type=Path, required=True)
    q.add_argument('--n', type=int, required=True)
    q.add_argument('--popped-out', type=Path)

    qa = sub.add_parser('queue-append-written', help='append paths to written_files')
    qa.add_argument('--queue', type=Path, required=True)
    qa.add_argument('--path', action='append', required=True, dest='paths')

    c = sub.add_parser('scratch-clean', help='delete files matching repo-root glob (dry-run default)')
    c.add_argument('--glob', required=True, dest='glob_pat')
    c.add_argument('--apply', action='store_true')

    args = p.parse_args(argv)
    corpus_dirs = _parse_corpus_dirs(getattr(args, 'corpus_dirs', None))

    if args.cmd == 'metadata-playlist':
        return cmd_metadata_playlist(args.url, args.out, args.playlist_end)
    if args.cmd == 'fetch-subs':
        return cmd_fetch_subs(args.video_id, args.out_dir, args.sleep_interval)
    if args.cmd == 'vtt-to-text':
        return cmd_vtt_to_text(args.in_dir, args.pattern)
    if args.cmd == 'overlap-scan':
        return cmd_overlap_scan(args.transcript, corpus_dirs, args.out)
    if args.cmd == 'overlap-scan-dir':
        return cmd_overlap_scan_dir(args.in_dir, corpus_dirs, args.out)
    if args.cmd == 'queue-pop':
        return cmd_queue_pop(args.queue, args.n, args.popped_out)
    if args.cmd == 'queue-append-written':
        return cmd_queue_append_written(args.queue, args.paths)
    if args.cmd == 'scratch-clean':
        return cmd_scratch_clean(args.glob_pat, args.apply)
    raise AssertionError('unhandled command')


if __name__ == '__main__':
    raise SystemExit(main())
