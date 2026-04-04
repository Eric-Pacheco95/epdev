#!/usr/bin/env python3
"""embedding_service.py -- Semantic search and similarity for Jarvis memory.

Embeds all Jarvis memory/signal/synthesis/decision files using nomic-embed-text
(via Ollama) and stores vectors in a persistent ChromaDB collection. Used by
/dream for duplicate detection and by /research for prior-brief lookup.

Usage (CLI):
    python tools/scripts/embedding_service.py index [--scope auto|full]
    python tools/scripts/embedding_service.py search "<query>" [--top-k 5]
    python tools/scripts/embedding_service.py similar [--threshold 0.92]
    python tools/scripts/embedding_service.py update <file_path>
    python tools/scripts/embedding_service.py stats

Scope dirs:
    auto  -- ~/.claude/projects/.../memory/*.md (auto-memory files only)
    full  -- auto + memory/learning/signals/ + memory/learning/synthesis/ + history/decisions/

Outputs:
    ~/.jarvis/vectorstore/   -- ChromaDB persistent collection (never in git repo)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests

# --- Constants ---

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
CHROMA_DIR = Path.home() / ".jarvis" / "vectorstore"
COLLECTION_NAME = "jarvis_memory"

REPO_ROOT = Path(__file__).resolve().parents[2]

AUTO_MEMORY_DIR = (
    Path.home()
    / ".claude"
    / "projects"
    / "C--Users-ericp-Github-epdev"
    / "memory"
)

FULL_SCOPE_DIRS = [
    AUTO_MEMORY_DIR,
    REPO_ROOT / "memory" / "learning" / "signals",
    REPO_ROOT / "memory" / "learning" / "signals" / "processed",
    REPO_ROOT / "memory" / "learning" / "synthesis",
    REPO_ROOT / "history" / "decisions",
]

AUTO_SCOPE_DIRS = [AUTO_MEMORY_DIR]

SNIPPET_LEN = 200
MAX_FILE_CHARS = 6000  # nomic-embed-text 2048-token context; ~6K chars is safe


# --- Ollama helpers ---

def _check_ollama() -> None:
    """Fail fast if Ollama is unreachable or model is missing."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
    except Exception as e:
        print(f"ERROR: Cannot reach Ollama at {OLLAMA_URL} -- {e}")
        print("  Ensure Ollama is running: ollama serve")
        sys.exit(1)
    if not any(EMBED_MODEL in m for m in models):
        print(f"ERROR: {EMBED_MODEL} not found in Ollama.")
        print(f"  Fix: ollama pull {EMBED_MODEL}")
        sys.exit(1)


def _embed(text: str) -> list[float]:
    """Return embedding vector for text via Ollama REST API."""
    payload = {"model": EMBED_MODEL, "input": text[:MAX_FILE_CHARS]}
    r = requests.post(f"{OLLAMA_URL}/api/embed", json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    vecs = data.get("embeddings") or data.get("embedding")
    if isinstance(vecs[0], list):
        return vecs[0]
    return vecs


# --- ChromaDB helpers ---

def _get_collection():
    """Return (or create) the persistent ChromaDB collection."""
    import chromadb
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def _file_id(path: Path) -> str:
    """Stable document ID from absolute path."""
    return str(path.resolve())


# --- Core API ---

def index(scope: str = "auto", verbose: bool = True) -> dict:
    """Embed all .md files in scope dirs, skipping up-to-date files.

    Returns summary dict: {indexed, skipped, errors, duration_s}
    """
    _check_ollama()
    col = _get_collection()

    dirs = AUTO_SCOPE_DIRS if scope == "auto" else FULL_SCOPE_DIRS
    dirs = [d for d in dirs if d.exists()]

    # Fetch existing metadata to detect stale files
    existing = {}
    try:
        results = col.get(include=["metadatas"])
        for doc_id, meta in zip(results["ids"], results["metadatas"]):
            existing[doc_id] = meta.get("mtime", 0)
    except Exception:
        pass

    indexed = skipped = errors = 0
    t0 = time.time()

    for d in dirs:
        for fpath in sorted(d.glob("*.md")):
            if fpath.name == "MEMORY.md":
                # Index MEMORY.md too -- useful for search but low priority
                pass
            doc_id = _file_id(fpath)
            mtime = fpath.stat().st_mtime

            if doc_id in existing and existing[doc_id] == mtime:
                skipped += 1
                continue

            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
                if len(text.strip()) < 50:
                    skipped += 1
                    continue
                vec = _embed(text)
                snippet = text[:SNIPPET_LEN].replace("\n", " ")
                col.upsert(
                    ids=[doc_id],
                    embeddings=[vec],
                    metadatas=[{
                        "file_path": str(fpath),
                        "file_name": fpath.name,
                        "scope_dir": str(d),
                        "mtime": mtime,
                        "snippet": snippet,
                    }],
                    documents=[text[:MAX_FILE_CHARS]],
                )
                indexed += 1
                if verbose:
                    print(f"  indexed: {fpath.name}")
            except Exception as e:
                errors += 1
                if verbose:
                    print(f"  ERROR {fpath.name}: {e}")

    duration = round(time.time() - t0, 1)
    summary = {
        "indexed": indexed,
        "skipped": skipped,
        "errors": errors,
        "duration_s": duration,
        "scope": scope,
        "dirs_scanned": [str(d) for d in dirs],
    }
    if verbose:
        print(f"\nIndex complete: {indexed} indexed, {skipped} skipped, "
              f"{errors} errors in {duration}s")
    return summary


def search(query: str, top_k: int = 5, scope: str = "full") -> list[dict]:
    """Semantic search across indexed files.

    Returns list of {file_path, file_name, score, snippet} sorted by score desc.
    Score is cosine similarity (0-1, higher = more similar).
    """
    _check_ollama()
    col = _get_collection()

    q_vec = _embed(query)
    try:
        results = col.query(
            query_embeddings=[q_vec],
            n_results=min(top_k, col.count()),
            include=["metadatas", "distances"],
        )
    except Exception as e:
        print(f"ERROR: search failed -- {e}")
        return []

    hits = []
    ids = results.get("ids", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    for meta, dist in zip(metas, dists):
        # ChromaDB cosine distance: 0 = identical, 2 = opposite
        # Convert to similarity: 1 - (dist/2)
        score = round(1.0 - dist / 2.0, 4)
        hits.append({
            "file_path": meta.get("file_path", ""),
            "file_name": meta.get("file_name", ""),
            "score": score,
            "snippet": meta.get("snippet", ""),
        })

    return sorted(hits, key=lambda x: x["score"], reverse=True)


def find_similar(threshold: float = 0.92) -> dict:
    """Find all file pairs with cosine similarity >= threshold.

    Returns {
        "duplicates": [(score, path_a, path_b), ...],   # >= threshold
        "related":    [(score, path_a, path_b), ...],   # 0.82-0.91
    }
    """
    col = _get_collection()
    count = col.count()
    if count < 2:
        return {"duplicates": [], "related": []}

    all_data = col.get(include=["embeddings", "metadatas"])
    ids = all_data["ids"]
    embeddings = all_data["embeddings"]
    metas = all_data["metadatas"]

    import numpy as np

    vecs = np.array(embeddings, dtype=np.float32)
    # Normalize for cosine similarity
    norms = np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9
    vecs_norm = vecs / norms

    duplicates = []
    related = []

    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            score = float(np.dot(vecs_norm[i], vecs_norm[j]))
            if score >= threshold:
                duplicates.append((
                    round(score, 4),
                    metas[i].get("file_path", ids[i]),
                    metas[j].get("file_path", ids[j]),
                ))
            elif score >= 0.82:
                related.append((
                    round(score, 4),
                    metas[i].get("file_path", ids[i]),
                    metas[j].get("file_path", ids[j]),
                ))

    duplicates.sort(reverse=True)
    related.sort(reverse=True)
    return {"duplicates": duplicates, "related": related}


def update(file_path: str) -> bool:
    """Re-embed a single file and upsert into the index.

    Returns True on success, False on error.
    """
    _check_ollama()
    col = _get_collection()
    fpath = Path(file_path)

    if not fpath.exists():
        print(f"ERROR: File not found: {file_path}")
        return False

    try:
        text = fpath.read_text(encoding="utf-8", errors="replace")
        if len(text.strip()) < 50:
            print(f"SKIP: {fpath.name} (too short)")
            return True
        vec = _embed(text)
        snippet = text[:SNIPPET_LEN].replace("\n", " ")
        col.upsert(
            ids=[_file_id(fpath)],
            embeddings=[vec],
            metadatas=[{
                "file_path": str(fpath.resolve()),
                "file_name": fpath.name,
                "scope_dir": str(fpath.parent),
                "mtime": fpath.stat().st_mtime,
                "snippet": snippet,
            }],
            documents=[text[:MAX_FILE_CHARS]],
        )
        print(f"Updated: {fpath.name}")
        return True
    except Exception as e:
        print(f"ERROR updating {fpath.name}: {e}")
        return False


def stats() -> dict:
    """Return index health summary."""
    col = _get_collection()
    count = col.count()

    # Detect stale files (on disk but mtime changed since last index)
    all_data = col.get(include=["metadatas"])
    stale = 0
    last_indexed_ts = 0.0

    for meta in all_data.get("metadatas", []):
        mtime_indexed = meta.get("mtime", 0)
        if mtime_indexed > last_indexed_ts:
            last_indexed_ts = mtime_indexed
        fpath = Path(meta.get("file_path", ""))
        if fpath.exists():
            current_mtime = fpath.stat().st_mtime
            if current_mtime > mtime_indexed + 1:  # 1s tolerance
                stale += 1

    last_indexed = (
        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_indexed_ts))
        if last_indexed_ts else "never"
    )

    # Estimate ChromaDB size
    size_mb = 0.0
    if CHROMA_DIR.exists():
        size_mb = round(
            sum(f.stat().st_size for f in CHROMA_DIR.rglob("*") if f.is_file())
            / 1_048_576,
            2,
        )

    return {
        "file_count": count,
        "last_indexed": last_indexed,
        "stale_count": stale,
        "collection_size_mb": size_mb,
        "vectorstore_path": str(CHROMA_DIR),
    }


# --- CLI ---

def _cmd_index(args) -> None:
    scope = args.scope if hasattr(args, "scope") else "auto"
    index(scope=scope, verbose=True)


def _cmd_search(args) -> None:
    query = " ".join(args.query)
    top_k = args.top_k if hasattr(args, "top_k") else 5
    hits = search(query, top_k=top_k)
    if not hits:
        print("No results.")
        return
    print(f"\nResults for: '{query}'")
    for i, h in enumerate(hits, 1):
        print(f"  {i}. [{h['score']:.3f}] {h['file_name']}")
        print(f"       {h['snippet'][:120]}...")


def _cmd_similar(args) -> None:
    threshold = args.threshold if hasattr(args, "threshold") else 0.92
    print(f"Scanning for pairs with similarity >= {threshold}...")
    result = find_similar(threshold=threshold)
    dupes = result["duplicates"]
    related = result["related"]

    if not dupes:
        print(f"  No duplicate candidates found at >= {threshold}")
    else:
        print(f"\n  DUPLICATE CANDIDATES ({len(dupes)}):")
        for score, a, b in dupes:
            print(f"    {score:.3f}  {Path(a).name}")
            print(f"           {Path(b).name}")

    if related:
        print(f"\n  RELATED (0.82-{threshold-0.01:.2f}) -- {len(related)} pairs, no action needed")
        for score, a, b in related[:5]:
            print(f"    {score:.3f}  {Path(a).name}  <->  {Path(b).name}")
        if len(related) > 5:
            print(f"    ... and {len(related) - 5} more")


def _cmd_update(args) -> None:
    update(args.file_path)


def _cmd_stats(args) -> None:
    s = stats()
    print("\nEmbedding Service Stats")
    print(f"  Files indexed : {s['file_count']}")
    print(f"  Last indexed  : {s['last_indexed']}")
    print(f"  Stale files   : {s['stale_count']}")
    print(f"  Store size    : {s['collection_size_mb']} MB")
    print(f"  Store path    : {s['vectorstore_path']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Jarvis embedding service -- semantic search for memory files"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_index = sub.add_parser("index", help="Index memory files")
    p_index.add_argument(
        "--scope", choices=["auto", "full"], default="auto",
        help="auto=auto-memory only; full=all tiers"
    )
    p_index.set_defaults(func=_cmd_index)

    p_search = sub.add_parser("search", help="Semantic search")
    p_search.add_argument("query", nargs="+", help="Search query")
    p_search.add_argument("--top-k", type=int, default=5)
    p_search.set_defaults(func=_cmd_search)

    p_sim = sub.add_parser("similar", help="Find duplicate/related file pairs")
    p_sim.add_argument("--threshold", type=float, default=0.92)
    p_sim.set_defaults(func=_cmd_similar)

    p_upd = sub.add_parser("update", help="Re-embed a single file")
    p_upd.add_argument("file_path", help="Path to the file to re-embed")
    p_upd.set_defaults(func=_cmd_update)

    p_stats = sub.add_parser("stats", help="Index health stats")
    p_stats.set_defaults(func=_cmd_stats)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
