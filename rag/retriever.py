import os
import json
import re
from config import FAISS_INDEX_PATH

_chunks = None


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())


def load_chunks():
    global _chunks
    chunks_file = FAISS_INDEX_PATH + ".chunks.json"
    if not os.path.exists(chunks_file):
        return None
    with open(chunks_file, 'r') as f:
        _chunks = json.load(f)
    return _chunks


def retrieve_context(query: str, top_k: int = 5) -> str:
    from rank_bm25 import BM25Okapi

    chunks = load_chunks()
    if not chunks:
        return "No code index available."

    corpus = [tokenize(f"{c['file']} {c['name']} {c['code']}") for c in chunks]
    bm25 = BM25Okapi(corpus)

    query_tokens = tokenize(query)
    scores = bm25.get_scores(query_tokens)

    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    results = []
    for idx in top_indices:
        chunk = chunks[idx]
        results.append(
            f"# {chunk['file']} - {chunk['name']} (lines {chunk['start_line']}-{chunk['end_line']})\n"
            f"{chunk['code']}"
        )

    return "\n\n---\n\n".join(results)
