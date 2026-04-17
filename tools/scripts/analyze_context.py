"""Analyze Claude Code session JSONL to rank context consumers by estimated token weight."""
import json
import os
import sys
from collections import defaultdict

def est_tokens(text):
    return len(str(text)) // 4

def analyze(jsonl_path):
    entries = []
    with open(jsonl_path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                pass

    file_size = os.path.getsize(jsonl_path)
    print(f"File: {os.path.basename(jsonl_path)}")
    print(f"Entries: {len(entries)} | Size: {file_size:,} bytes (~{file_size//4:,} raw tokens)")
    print()

    buckets = defaultdict(int)
    message_counts = defaultdict(int)

    for entry in entries:
        etype = entry.get('type', '')
        msg = entry.get('message', {})
        role = msg.get('role', etype)
        content = msg.get('content', '')

        if etype == 'system':
            sys_content = entry.get('content', '')
            tok = est_tokens(sys_content)
            buckets['[SYS] system_prompt'] += tok
            message_counts['[SYS] system_prompt'] += 1
            continue

        if isinstance(content, str):
            buckets[f'[{role}] raw_text'] += est_tokens(content)
            message_counts[f'[{role}] raw_text'] += 1
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get('type', '')

                if btype == 'text':
                    text = block.get('text', '') or ''
                    tok = est_tokens(text)

                    # Classify by content fingerprint
                    if 'JARVIS :: NEURAL LINK' in text:
                        key = '[hook] session_start_banner'
                    elif 'SKILL.md' in text and 'IDENTITY and PURPOSE' in text:
                        # Estimate which skill
                        for skill_name in ['synthesize-signals', 'learning-capture', 'commit',
                                           'update-steering-rules', 'architecture-review',
                                           'implement-prd', 'create-prd', 'quality-gate',
                                           'research', 'security-audit']:
                            if skill_name in text:
                                key = f'[skill_inline] {skill_name}'
                                break
                        else:
                            key = '[skill_inline] unknown'
                    elif 'CLAUDE.md' in text or 'claudeMd' in etype or entry.get('isMeta'):
                        key = '[sys] CLAUDE.md_content'
                    elif 'MEMORY.md' in text or 'auto-memory' in text:
                        key = '[sys] memory_index'
                    elif role == 'user':
                        key = '[user] message'
                    elif role == 'assistant':
                        key = '[assistant] response'
                    else:
                        key = f'[{role}] text'

                    buckets[key] += tok
                    message_counts[key] += 1

                elif btype == 'tool_use':
                    name = block.get('name', 'unknown')
                    tok = est_tokens(json.dumps(block.get('input', '')))
                    buckets[f'[tool_use] {name}'] += tok
                    message_counts[f'[tool_use] {name}'] += 1

                elif btype == 'tool_result':
                    inner = block.get('content', '')
                    tok = est_tokens(inner)
                    buckets['[tool_result] all'] += tok
                    message_counts['[tool_result] all'] += 1

    total = sum(buckets.values())
    print(f"{'Category':<45} {'Est.Tokens':>10}  {'% Total':>8}  {'Count':>6}")
    print("-" * 75)
    for k, v in sorted(buckets.items(), key=lambda x: -x[1]):
        if v > 200:
            pct = v / total * 100 if total else 0
            print(f"  {k:<43} {v:>10,}  {pct:>7.1f}%  {message_counts[k]:>6}")
    print("-" * 75)
    print(f"  {'TOTAL':<43} {total:>10,}  {'100.0%':>8}")

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        # Default: most recent session
        proj_dir = r"C:/Users/ericp/.claude/projects/C--Users-ericp-Github-epdev"
        files = sorted(
            [os.path.join(proj_dir, f) for f in os.listdir(proj_dir) if f.endswith('.jsonl')],
            key=os.path.getmtime, reverse=True
        )
        path = files[0]
        print(f"Using most recent session: {os.path.basename(path)}\n")
    analyze(path)
