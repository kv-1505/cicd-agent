import json
import asyncio
import threading
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from gh_client.webhook import verify_webhook_signature
from gh_client.client import fetch_workflow_logs
from agent.graph import agent_graph
from config import GITHUB_WEBHOOK_SECRET

app = FastAPI(title="CI/CD Agent")

reindex_lock = threading.Lock()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    # Validate signature
    body = await verify_webhook_signature(request, GITHUB_WEBHOOK_SECRET)
    payload = json.loads(body)

    event = request.headers.get("X-GitHub-Event")
    action = payload.get("action", "no-action")
    conclusion = payload.get("workflow_run", {}).get("conclusion", "no-conclusion")

    print(f"[Webhook] Event: {event} | Action: {action} | Conclusion: {conclusion}")

    # Re-index on every push (code changed)
    if event == "push":
        repo_full_name = payload["repository"]["full_name"]
        background_tasks.add_task(reindex_repo, repo_full_name)
        return {"status": "reindexing"}

    # Only handle workflow_run failures
    if event == "workflow_run" and action == "completed":
        workflow_run = payload["workflow_run"]

        if workflow_run["conclusion"] == "failure":
            repo_full_name = payload["repository"]["full_name"]
            workflow_run_id = workflow_run["id"]
            pr_number = None

            pull_requests = workflow_run.get("pull_requests", [])
            if pull_requests:
                pr_number = pull_requests[0]["number"]

            print(f"[Webhook] Queuing agent for run #{workflow_run_id}")
            background_tasks.add_task(
                run_agent_sync,
                repo_full_name,
                workflow_run_id,
                pr_number
            )
            print(f"[Webhook] Agent queued!")

            return {"status": "processing", "run_id": workflow_run_id}

    return {"status": "ignored"}


def reindex_repo(repo_full_name: str):
    try:
        from rag.indexer import index_repository
        from config import GITHUB_TOKEN as token
        print(f"[Reindex] Push detected, re-indexing {repo_full_name}")
        repo_url = f"https://{token}@github.com/{repo_full_name}.git"
        with reindex_lock:
            index_repository(repo_url)
        print(f"[Reindex] Done!")
    except Exception as e:
        import traceback
        print(f"[Reindex] ERROR: {e}")
        print(traceback.format_exc())


def run_agent_sync(repo_full_name: str, workflow_run_id: int, pr_number: int | None):
    try:
        print(f"\n[Agent] Starting for {repo_full_name} run #{workflow_run_id}")

        raw_logs = fetch_workflow_logs(repo_full_name, workflow_run_id)
        print(f"[Agent] Fetched {len(raw_logs)} chars of logs")

        initial_state = {
            "repo_full_name": repo_full_name,
            "pr_number": pr_number,
            "workflow_run_id": workflow_run_id,
            "raw_logs": raw_logs,
            "error_analysis": {},
            "blame_result": {},
            "retrieved_context": "",
            "proposed_fix": {},
            "validation_result": {},
            "report": "",
            "retry_count": 0
        }

        result = agent_graph.invoke(initial_state)

        print("\n=== AGENT RESULT ===")
        print(f"Error: {result['error_analysis'].get('summary')}")
        print(f"Blame: {result['blame_result'].get('commit_sha')} by {result['blame_result'].get('author')}")
        print("===================\n")

    except Exception as e:
        import traceback
        print(f"[Agent] ERROR: {e}")
        print(traceback.format_exc())
