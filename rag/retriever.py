import os
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL, FAISS_INDEX_PATH

model = SentenceTransformer(EMBEDDING_MODEL)

_index = None
_chunks = None


def load_index():
    global _index, _chunks
    index_file = FAISS_INDEX_PATH + ".index"
    chunks_file = FAISS_INDEX_PATH + ".chunks.json"

    if not os.path.exists(index_file):
        return None, None

    _index = faiss.read_index(index_file)
    with open(chunks_file, 'r') as f:
        _chunks = json.load(f)

    return _index, _chunks


def retrieve_context(query: str, top_k: int = 5) -> str:
    """Search FAISS index for most relevant code chunks."""
    index, chunks = load_index()
    if index is None:
        return "No code index available."

    query_embedding = model.encode([query]).astype('float32')
    distances, indices = index.search(query_embedding, top_k)

    results = []
    for i, idx in enumerate(indices[0]):
        if idx < len(chunks):
            chunk = chunks[idx]
            results.append(
                f"# {chunk['file']} - {chunk['name']} (lines {chunk['start_line']}-{chunk['end_line']})\n"
                f"{chunk['code']}"
            )

    return "\n\n---\n\n".join(results)
