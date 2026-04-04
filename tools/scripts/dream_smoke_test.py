"""
Smoke test for nomic-embed-text semantic similarity on Jarvis memory files.
Uses Ollama REST API + numpy only -- no new dependencies.

Tests:
1. Can we embed memory files?
2. Do semantically related files score higher than unrelated ones?
3. What threshold separates duplicates from distinct memories?
"""
import json
import os
import sys
import requests
import numpy as np
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/embed"
MODEL = "nomic-embed-text"
MEMORY_DIR = Path(os.environ.get("MEMORY_DIR", r"C:\Users\ericp\.claude\projects\C--Users-ericp-Github-epdev\memory"))

# --- helpers ---

def embed(text: str) -> np.ndarray:
    resp = requests.post(OLLAMA_URL, json={"model": MODEL, "input": text}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # Ollama returns {"embeddings": [[...]]} for /api/embed
    vecs = data.get("embeddings") or data.get("embedding")
    if isinstance(vecs[0], list):
        return np.array(vecs[0], dtype=np.float32)
    return np.array(vecs, dtype=np.float32)

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")[:3000]  # cap at 3K chars
    except Exception:
        return ""

def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

# --- test files: pick a diverse set ---
TEST_FILES = [
    "feedback_think_before_build.md",       # ADHD / build discipline
    "user_adhd_session_patterns.md",        # ADHD / Eric's patterns
    "feedback_idle_is_success_dispatch.md", # dispatcher / autonomous
    "project_unified_pipeline_vision.md",   # dispatcher / pipeline
    "feedback_claude_max_no_cursor.md",     # tooling / Claude Max
    "project_workdir.md",                   # workdir / paths
    "user_car_ev_research.md",              # EV / car purchase
    "user_prediction_philosophy.md",        # predictions / philosophy
]

def main():
    section("STEP 1: Verify Ollama connectivity")
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        print(f"  Ollama running. Models: {models}")
        if not any("nomic-embed-text" in m for m in models):
            print("  ERROR: nomic-embed-text not found in Ollama models")
            sys.exit(1)
        print("  nomic-embed-text: FOUND")
    except Exception as e:
        print(f"  ERROR: Cannot reach Ollama -- {e}")
        sys.exit(1)

    section("STEP 2: Embed all test files")
    embeddings = {}
    for fname in TEST_FILES:
        fpath = MEMORY_DIR / fname
        if not fpath.exists():
            print(f"  SKIP (not found): {fname}")
            continue
        text = read_file(fpath)
        if not text.strip():
            print(f"  SKIP (empty): {fname}")
            continue
        vec = embed(text)
        embeddings[fname] = vec
        print(f"  OK  {fname} ({len(text)} chars, dim={len(vec)})")

    if not embeddings:
        print("  ERROR: No files embedded")
        sys.exit(1)

    section("STEP 3: Pairwise similarity matrix")
    names = list(embeddings.keys())
    print(f"  {'':40s}", end="")
    short = [n.replace("feedback_","f_").replace("project_","p_").replace("user_","u_")[:18] for n in names]
    for s in short:
        print(f"  {s:18s}", end="")
    print()
    for i, na in enumerate(names):
        print(f"  {short[i]:40s}", end="")
        for j, nb in enumerate(names):
            score = cosine(embeddings[na], embeddings[nb])
            marker = " **" if i != j and score > 0.85 else ("  >" if i != j and score > 0.75 else "   ")
            print(f"  {score:.2f}{marker:3s}      ", end="")
        print()

    section("STEP 4: Semantic query test")
    queries = [
        "ADHD focus and build discipline",
        "autonomous pipeline dispatcher",
        "car purchase electric vehicle",
    ]
    for query in queries:
        qvec = embed(query)
        scores = {n: cosine(qvec, v) for n, v in embeddings.items()}
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        print(f"\n  Query: '{query}'")
        for fname, score in ranked[:4]:
            bar = "#" * int(score * 30)
            print(f"    {score:.3f} {bar:25s} {fname}")

    section("STEP 5: Duplicate candidate detection (threshold scan)")
    pairs = []
    for i, na in enumerate(names):
        for j, nb in enumerate(names):
            if j <= i:
                continue
            score = cosine(embeddings[na], embeddings[nb])
            pairs.append((score, na, nb))
    pairs.sort(reverse=True)

    print("\n  Top 5 most similar pairs:")
    for score, na, nb in pairs[:5]:
        flag = " << DUPLICATE CANDIDATE" if score > 0.85 else (" << RELATED" if score > 0.75 else "")
        print(f"    {score:.3f}  {na}")
        print(f"           {nb}{flag}")

    print("\n  Threshold summary:")
    for thresh in [0.95, 0.90, 0.85, 0.80, 0.75]:
        count = sum(1 for s, _, _ in pairs if s >= thresh)
        print(f"    >= {thresh:.2f}: {count} pairs would be flagged as duplicates")

    section("VERDICT")
    top_score = pairs[0][0] if pairs else 0
    related_pairs = [(s, a, b) for s, a, b in pairs if s > 0.80]
    print(f"  Embedding model: OK")
    print(f"  Dimension: {len(list(embeddings.values())[0])}")
    print(f"  Highest similarity pair: {top_score:.3f}")
    print(f"  Pairs above 0.80: {len(related_pairs)}")
    if top_score > 0.90:
        print("  -> Strong semantic signal. 0.88-0.90 threshold recommended for dedup.")
    elif top_score > 0.80:
        print("  -> Good semantic signal. 0.82-0.85 threshold recommended for dedup.")
    else:
        print("  -> Weak signal at this file set -- these files may be too distinct to test dedup.")
    print("\n  READY FOR /dream IMPLEMENTATION: YES" if embeddings else "\n  READY: NO -- fix errors above")

if __name__ == "__main__":
    main()
