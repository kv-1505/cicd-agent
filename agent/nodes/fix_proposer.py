import json
from groq import Groq
from agent.state import AgentState
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)


def fix_proposer(state: AgentState) -> AgentState:
    """Propose a fix for the build failure using Groq."""
    error_analysis = state["error_analysis"]
    blame_result = state["blame_result"]
    context = state["retrieved_context"]

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": f"""You are a senior software engineer. Analyse this CI/CD failure and propose a precise fix.

## Build Error
{error_analysis.get('error_message', 'Unknown error')}
File: {error_analysis.get('file', 'unknown')}
Line: {error_analysis.get('line_number', 'unknown')}
Category: {error_analysis.get('root_cause_category', 'unknown')}

## Responsible Commit
SHA: {blame_result.get('commit_sha', 'unknown')}
Author: {blame_result.get('author', 'unknown')}
Message: {blame_result.get('message', 'unknown')}

## Relevant Code Context
{context[:3000]}

Return a JSON object with exactly these fields:
{{
  "file": "path/to/file.py",
  "original_code": "ONLY the single broken line or small snippet that needs to change - NOT the whole file",
  "fixed_code": "ONLY the replacement for that specific line or snippet - NOT the whole file. If the line should be deleted, use empty string.",
  "explanation": "one paragraph explaining what was wrong and how the fix resolves it",
  "confidence": 0.0
}}

IMPORTANT: original_code and fixed_code must be small focused snippets, not entire files.

Return only valid JSON, no explanation."""
            }
        ]
    )

    try:
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        proposed_fix = json.loads(text.strip())
    except json.JSONDecodeError:
        proposed_fix = {
            "file": error_analysis.get("file", "unknown"),
            "original_code": "",
            "fixed_code": "",
            "explanation": response.choices[0].message.content,
            "confidence": 0.3
        }

    print(f"[Fix Proposer] Confidence: {proposed_fix.get('confidence')} | File: {proposed_fix.get('file')}")
    return {**state, "proposed_fix": proposed_fix}
