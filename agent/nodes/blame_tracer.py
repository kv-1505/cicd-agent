from github import Github
from agent.state import AgentState
from config import GITHUB_TOKEN


def blame_tracer(state: AgentState) -> AgentState:
    """Find the commit responsible for the build failure."""
    error_analysis = state["error_analysis"]
    repo_full_name = state["repo_full_name"]
    workflow_run_id = state["workflow_run_id"]

    gh = Github(GITHUB_TOKEN)
    repo = gh.get_repo(repo_full_name)

    try:
        # Get the workflow run to find associated commits
        run = repo.get_workflow_run(workflow_run_id)
        head_commit = run.head_sha

        # Get commit details
        commit = repo.get_commit(head_commit)

        blame_result = {
            "commit_sha": head_commit[:7],
            "full_sha": head_commit,
            "author": commit.commit.author.name,
            "author_email": commit.commit.author.email,
            "message": commit.commit.message,
            "timestamp": commit.commit.author.date.isoformat(),
            "files_changed": [f.filename for f in commit.files],
            "url": commit.html_url
        }

        # If we have a specific file from log analyser, check if it's in the diff
        error_file = error_analysis.get("file")
        if error_file:
            blame_result["error_file_in_commit"] = any(
                error_file in f for f in blame_result["files_changed"]
            )

        print(f"[Blame Tracer] Commit: {blame_result['commit_sha']} by {blame_result['author']}")

    except Exception as e:
        print(f"[Blame Tracer] Error: {e}")
        blame_result = {
            "commit_sha": "unknown",
            "author": "unknown",
            "message": "Could not trace blame",
            "error": str(e)
        }

    return {**state, "blame_result": blame_result}
