import py_compile
import tempfile
import os
from agent.state import AgentState


def validator(state: AgentState) -> AgentState:
    """Validate the proposed fix before posting."""
    proposed_fix = state["proposed_fix"]
    retry_count = state.get("retry_count", 0)

    issues = []

    # Check confidence
    confidence = proposed_fix.get("confidence", 0)
    if confidence < 0.7:
        issues.append(f"Low confidence: {confidence}")

    # Check no placeholders left
    fixed_code = proposed_fix.get("fixed_code", "")
    for placeholder in ["TODO", "FIXME", "...", "<your", "placeholder"]:
        if placeholder.lower() in fixed_code.lower():
            issues.append(f"Placeholder found in fix: {placeholder}")

    # Check fix is not empty (but allow empty if original has content - means delete the line)
    original_code = proposed_fix.get("original_code", "")
    if not fixed_code.strip() and not original_code.strip():
        issues.append("Both original and fix are empty")

    # Syntax check if it's Python
    file = proposed_fix.get("file", "")
    if file.endswith(".py") and fixed_code:
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(fixed_code)
                tmp_path = f.name
            py_compile.compile(tmp_path, doraise=True)
            os.unlink(tmp_path)
        except py_compile.PyCompileError as e:
            issues.append(f"Syntax error in fix: {e}")
        except Exception:
            pass

    if issues:
        validation_result = {
            "valid": False,
            "issues": issues,
            "retry_count": retry_count
        }
        print(f"[Validator] FAILED: {issues}")
    else:
        validation_result = {
            "valid": True,
            "issues": [],
            "retry_count": retry_count
        }
        print(f"[Validator] PASSED with confidence {confidence}")

    return {**state, "validation_result": validation_result, "retry_count": retry_count + 1}
