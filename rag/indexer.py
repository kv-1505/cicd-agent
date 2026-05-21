import os
import ast
import json
import shutil
import tempfile
from git import Repo
from config import FAISS_INDEX_PATH


def chunk_python_file(file_path: str, content: str) -> list[dict]:
    chunks = []
    lines = content.split("\n")

    try:
        tree = ast.parse(content)
        covered_lines = set()

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = node.lineno - 1
                end = node.end_lineno
                chunk_code = "\n".join(lines[start:end])
                chunks.append({
                    "file": file_path,
                    "name": node.name,
                    "type": type(node).__name__,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno,
                    "code": chunk_code
                })
                for i in range(start, end):
                    covered_lines.add(i)

        # Top-level code not inside any function/class
        top_level_lines = []
        for i, line in enumerate(lines):
            if i not in covered_lines and line.strip():
                top_level_lines.append((i + 1, line))

        if top_level_lines:
            group = [top_level_lines[0]]
            for lineno, line in top_level_lines[1:]:
                if lineno == group[-1][0] + 1:
                    group.append((lineno, line))
                else:
                    chunks.append({
                        "file": file_path,
                        "name": f"top_level_lines_{group[0][0]}-{group[-1][0]}",
                        "type": "top_level",
                        "start_line": group[0][0],
                        "end_line": group[-1][0],
                        "code": "\n".join(l for _, l in group)
                    })
                    group = [(lineno, line)]
            chunks.append({
                "file": file_path,
                "name": f"top_level_lines_{group[0][0]}-{group[-1][0]}",
                "type": "top_level",
                "start_line": group[0][0],
                "end_line": group[-1][0],
                "code": "\n".join(l for _, l in group)
            })

        chunks.append({
            "file": file_path,
            "name": f"{os.path.basename(file_path)} (full file)",
            "type": "file",
            "start_line": 1,
            "end_line": len(lines),
            "code": content[:3000]
        })

    except SyntaxError:
        chunks.append({
            "file": file_path,
            "name": f"{os.path.basename(file_path)} (full file - syntax error)",
            "type": "file",
            "start_line": 1,
            "end_line": len(lines),
            "code": content[:3000]
        })

    return chunks


def index_repository(repo_url: str, local_path: str = None):
    temp_dir = None

    if local_path and os.path.exists(local_path):
        repo_path = local_path
    else:
        temp_dir = tempfile.mkdtemp()
        print(f"[RAG] Cloning {repo_url} to {temp_dir}")
        Repo.clone_from(repo_url, temp_dir)
        repo_path = temp_dir

    chunks = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['venv', 'node_modules', '__pycache__']]
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repo_path)
                try:
                    with open(file_path, 'r', errors='replace') as f:
                        content = f.read()
                    file_chunks = chunk_python_file(rel_path, content)
                    chunks.extend(file_chunks)
                except Exception as e:
                    print(f"[RAG] Skipping {rel_path}: {e}")

    if not chunks:
        print("[RAG] No Python files found to index")
        return

    print(f"[RAG] Indexing {len(chunks)} chunks from {len(set(c['file'] for c in chunks))} files")

    os.makedirs(os.path.dirname(FAISS_INDEX_PATH), exist_ok=True)
    with open(FAISS_INDEX_PATH + ".chunks.json", 'w') as f:
        json.dump(chunks, f)

    if temp_dir:
        shutil.rmtree(temp_dir)

    print(f"[RAG] Index saved to {FAISS_INDEX_PATH}")
