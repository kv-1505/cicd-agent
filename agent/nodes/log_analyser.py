import json
import anthropic
from agent.state import AgentState
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def log_analyser(state: AgentState) -> AgentState:
    """Analyse build logs and extract error information."""
    raw_logs = state["raw_logs"]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""You are a CI/CD expert. Analyse these build logs and return a JSON object with exactly these fields:
{{
  "error_message": "the exact error message",
  "file": "the file where the error occurred or null",
  "line_number": "the line number or null",
  "root_cause_category": "one of: dependency, syntax, test, config, infra",
  "summary": "one sentence summary of what went wrong",
  "confidence": 0.0
}}

Build logs:
{raw_logs}

Return only valid JSON, no explanation."""
            }
        ]
    )

    try:
        text = response.content[0].text.strip()
        # Strip markdown code block if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        error_analysis = json.loads(text.strip())
    except json.JSONDecodeError:
        error_analysis = {
            "error_message": response.content[0].text,
            "file": None,
            "line_number": None,
            "root_cause_category": "unknown",
            "summary": "Could not parse structured error",
            "confidence": 0.3
        }

    print(f"[Log Analyser] Error: {error_analysis.get('summary')}")
    return {**state, "error_analysis": error_analysis}
