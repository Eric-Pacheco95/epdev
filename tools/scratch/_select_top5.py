import json

raw = open('tools/scratch/gopher_playlist.json', 'rb').read()
if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
    text = raw.decode('utf-16')
else:
    text = raw.decode('utf-8')
d = json.loads(text)

with open('tools/scratch/gopher_playlist.json', 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=2)

entries = [e for e in d.get('entries', []) if e.get('view_count') is not None]
entries.sort(key=lambda e: e.get('view_count') or 0, reverse=True)
top5 = entries[:5]

with open('tools/scratch/gopher_top5.json', 'w', encoding='utf-8') as f:
    json.dump(
        [{k: e.get(k) for k in ['id', 'title', 'view_count', 'url', 'duration', 'timestamp']} for e in top5],
        f, ensure_ascii=False, indent=2
    )

print('total with view_count:', len(entries))
for i, e in enumerate(top5, 1):
    print(f"{i}. {e['view_count']:>8}  {e['id']}  {e['title']}")
