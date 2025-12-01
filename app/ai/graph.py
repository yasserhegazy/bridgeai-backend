from langgraph.graph import StateGraph, END
from app.ai.state import AgentState
from app.ai.nodes.echo_node import echo_node
from app.ai.nodes.clarification import clarification_node, should_request_clarification


def create_graph():
    """
    Create the LangGraph workflow with clarification agent.

    Workflow:
    1. Start with clarification agent
    2. If clarification is needed → END (wait for user)
    3. If no clarification is needed → continue to echo (or next agent)
    """
    graph = StateGraph(AgentState)

    # Nodes
    graph.add_node("clarification", clarification_node)
    graph.add_node("echo", echo_node)

    # Entry point
    graph.set_entry_point("clarification")

    # Conditional routing
    graph.add_conditional_edges(
        "clarification",
        should_request_clarification,   # returns True/False
        {
            True: END,          # need clarification → stop and ask user
            False: "echo"       # proceed to next step
        }
    )

    # Final step after echo
    graph.add_edge("echo", END)

    return graph.compile()
