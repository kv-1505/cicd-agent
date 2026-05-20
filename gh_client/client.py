import io
import zipfile
import requests
from github import Github
from config import GITHUB_TOKEN


def get_github_client():
    return Github(GITHUB_TOKEN)


def fetch_workflow_logs(repo_full_name: str, workflow_run_id: int) -> str:
    """Fetch and decode logs for a workflow run."""
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    url = f"https://api.github.com/repos/{repo_full_name}/actions/runs/{workflow_run_id}/logs"
    response = requests.get(url, headers=headers, allow_redirects=True)

    if response.status_code == 200:
        try:
            # GitHub returns a zip file
            zip_data = io.BytesIO(response.content)
            with zipfile.ZipFile(zip_data) as z:
                log_parts = []
                for name in z.namelist():
                    with z.open(name) as f:
                        content = f.read().decode("utf-8", errors="replace")
                        log_parts.append(f"=== {name} ===\n{content}")
                full_log = "\n".join(log_parts)
                return full_log[:15000]
        except zipfile.BadZipFile:
            return response.text[:15000]

    # Fallback: use GitHub API to get job steps
    gh = get_github_client()
    repo = gh.get_repo(repo_full_name)
    run = repo.get_workflow_run(workflow_run_id)

    logs = []
    for job in run.jobs():
        logs.append(f"=== Job: {job.name} (status: {job.conclusion}) ===")
        for step in job.steps:
            logs.append(f"  Step: {step.name} - {step.conclusion}")

    return "\n".join(logs)
