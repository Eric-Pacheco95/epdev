import json, re
d = json.load(open('tools/scratch/gopher_playlist.json', encoding='utf-8'))
KEYS = re.compile(r'\b(llm|rag|vector|mcp|agent|claude|gpt|anthropic|meta|deepagent|embedding|ai search|model context)\b', re.I)
rows = []
for e in d.get('entries', []):
    title = e.get('title') or ''
    if KEYS.search(title):
        rows.append((e.get('view_count') or 0, e.get('id'), title))
rows.sort(key=lambda r: r[0], reverse=True)
for v, i, t in rows[:20]:
    print(f'{v:>8}  {i}  {t}')
