"""
Statusline script: estimate current context fill % for active Claude Code session.
Strategy: find last isMeta (auto-compaction marker) timestamp, count + weight entries
after it as a proxy for the live context window. Falls back to all entries if no isMeta.
Output: single colorized line for statusline display.
"""
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

CONTEXT_LIMIT_TOKENS = 200_000
PROJ_DIR = r"C:/Users/ericp/.claude/projects/C--Users-ericp-Github-epdev"

# Empirical token weights per entry type (from session analysis)
TOKENS_PER_TYPE = {
    'user':       2_500,
    'assistant':  1_500,
    'attachment': 1_200,
    'system':       800,
    'default':      300,
}


def get_most_recent_session():
    try:
        files = [
            os.path.join(PROJ_DIR, f)
            for f in os.listdir(PROJ_DIR)
            if f.endswith('.jsonl')
        ]
        return max(files, key=os.path.getmtime) if files else None
    except Exception:
        return None


def analyze(path):
    entries = []
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        return 0, 0, 0

    # Find the latest isMeta timestamp (Claude Code auto-compaction marker)
    last_compact_ts = None
    for e in entries:
        if e.get('isMeta') and e.get('timestamp'):
            ts = e['timestamp']
            if last_compact_ts is None or ts > last_compact_ts:
                last_compact_ts = ts

    # Count compact events (isMeta entries = auto-compactions)
    compact_count = sum(1 for e in entries if e.get('isMeta'))

    # Live entries = everything after last compaction marker
    if last_compact_ts:
        live = [e for e in entries if e.get('timestamp', '') > last_compact_ts]
    else:
        live = entries

    # Estimate tokens from live entries using empirical weights
    est_tokens = sum(
        TOKENS_PER_TYPE.get(e.get('type', ''), TOKENS_PER_TYPE['default'])
        for e in live
    )

    # Count user turns = user-type entries in live set
    user_turns = sum(1 for e in live if e.get('type') == 'user')

    return est_tokens, compact_count, user_turns


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else get_most_recent_session()
    if not path or not os.path.exists(str(path)):
        print('CTX:?')
        return

    est_tokens, compact_count, user_turns = analyze(path)
    pct = min(99, int(est_tokens / CONTEXT_LIMIT_TOKENS * 100))

    # ASCII bar (10 chars)
    filled = pct // 10
    bar = '#' * filled + '-' * (10 - filled)

    # ANSI color: green <50%, yellow 50-75%, red >=75%
    if pct < 50:
        color = '\033[32m'
    elif pct < 75:
        color = '\033[33m'
    else:
        color = '\033[31m'
    reset = '\033[0m'

    k = est_tokens // 1_000
    limit_k = CONTEXT_LIMIT_TOKENS // 1_000
    compact_str = f' /{compact_count}cx' if compact_count > 0 else ''
    turns_str = f' {user_turns}t'

    print(f'{color}CTX [{bar}] ~{pct}% ~{k}K/{limit_k}K{compact_str}{turns_str}{reset}')


if __name__ == '__main__':
    main()
