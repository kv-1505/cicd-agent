import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
from gh_client.client import fetch_workflow_logs
from agent.graph import agent_graph

mcp = FastMCP("CI/CD Agent")


@mcp.tool()
def diagnose_failure(repo_full_name: str, workflow_run_id: int) -> str:
    """
    Diagnose a GitHub Actions workflow failure.
    Analyses logs, traces the responsible commit, proposes a fix, and returns a report.

    Args:
        repo_full_name: GitHub repo in 'owner/repo' format (e.g. 'kv-1505/cicd-agent-test')
        workflow_run_id: The GitHub Actions workflow run ID to diagnose
    """
    try:
        raw_logs = fetch_workflow_logs(repo_full_name, workflow_run_id)

        initial_state = {
            "repo_full_name": repo_full_name,
            "pr_number": None,
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
        return result["report"]

    except Exception as e:
        return f"Error diagnosing failure: {e}"


@mcp.tool()
def get_recent_failures(repo_full_name: str, limit: int = 5) -> str:
    """
    List recent failed GitHub Actions workflow runs for a repo.

    Args:
        repo_full_name: GitHub repo in 'owner/repo' format
        limit: Number of recent failures to return (default 5)
    """
    try:
        from gh_client.client import get_github_client
        gh = get_github_client()
        repo = gh.get_repo(repo_full_name)
        runs = repo.get_workflow_runs(status="failure")

        lines = [f"Recent failures for {repo_full_name}:\n"]
        for i, run in enumerate(runs):
            if i >= limit:
                break
            lines.append(f"- Run #{run.id} | {run.name} | {run.head_commit.message[:50]} | {run.created_at}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching failures: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
