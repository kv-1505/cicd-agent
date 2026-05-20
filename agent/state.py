from typing import TypedDict, Optional


class AgentState(TypedDict):
    repo_full_name: str
    pr_number: Optional[int]
    workflow_run_id: int
    raw_logs: str
    error_analysis: dict        # from Log Analyser
    blame_result: dict          # from Blame Tracer
    retrieved_context: str      # from Code Retriever
    proposed_fix: dict          # from Fix Proposer
    validation_result: dict     # from Validator
    report: str                 # final PR comment
    retry_count: int            # for validator retry logic
