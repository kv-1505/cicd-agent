from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes.log_analyser import log_analyser
from agent.nodes.blame_tracer import blame_tracer
from agent.nodes.code_retriever import code_retriever
from agent.nodes.fix_proposer import fix_proposer
from agent.nodes.validator import validator
from agent.nodes.pr_reporter import pr_reporter

MAX_RETRIES = 2


def should_retry(state: AgentState) -> str:
    """Route back to fix_proposer if validation failed and retries remain."""
    validation = state.get("validation_result", {})
    retry_count = state.get("retry_count", 0)

    if not validation.get("valid") and retry_count < MAX_RETRIES:
        print(f"[Graph] Retrying fix proposer (attempt {retry_count + 1}/{MAX_RETRIES})")
        return "retry"
    return "done"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("log_analyser", log_analyser)
    graph.add_node("blame_tracer", blame_tracer)
    graph.add_node("code_retriever", code_retriever)
    graph.add_node("fix_proposer", fix_proposer)
    graph.add_node("validator", validator)
    graph.add_node("pr_reporter", pr_reporter)

    graph.set_entry_point("log_analyser")
    graph.add_edge("log_analyser", "blame_tracer")
    graph.add_edge("blame_tracer", "code_retriever")
    graph.add_edge("code_retriever", "fix_proposer")
    graph.add_edge("fix_proposer", "validator")

    # Conditional: retry fix or proceed to report
    graph.add_conditional_edges(
        "validator",
        should_retry,
        {
            "retry": "fix_proposer",
            "done": "pr_reporter"
        }
    )

    graph.add_edge("pr_reporter", END)

    return graph.compile()


agent_graph = build_graph()
