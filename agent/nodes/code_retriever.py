import os
from rag.retriever import retrieve_context
from rag.indexer import index_repository
from agent.state import AgentState
from config import GITHUB_TOKEN, FAISS_INDEX_PATH


def code_retriever(state: AgentState) -> AgentState:
    """Retrieve relevant code context using RAG."""
    error_analysis = state["error_analysis"]
    repo_full_name = state["repo_full_name"]

    # Only index if no index exists yet (first ever run)
    index_file = FAISS_INDEX_PATH + ".index"
    if not os.path.exists(index_file):
        print(f"[Code Retriever] No index found, indexing for the first time...")
        repo_url = f"https://{GITHUB_TOKEN}@github.com/{repo_full_name}.git"
        try:
            index_repository(repo_url)
        except Exception as e:
            print(f"[Code Retriever] Indexing failed: {e}")
    else:
        print(f"[Code Retriever] Using existing index (re-indexed on last push)")

    # Build search query from error info
    query = f"{error_analysis.get('error_message', '')} {error_analysis.get('file', '')} {error_analysis.get('root_cause_category', '')}"

    # Wait for any in-progress reindex to finish before querying
    from main import reindex_lock
    with reindex_lock:
        context = retrieve_context(query)
    print(f"[Code Retriever] Retrieved {len(context)} chars of context")

    return {**state, "retrieved_context": context}
