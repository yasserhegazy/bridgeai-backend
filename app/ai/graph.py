# app/ai/graph.py

from langgraph.graph import StateGraph, END
from app.ai.state import AgentState

# Nodes
from app.ai.nodes.clarification import clarification_node, should_request_clarification
from app.ai.nodes.echo_node import echo_node


def create_graph():
    """
    Create the LangGraph workflow with the LLM-powered Clarification Agent.

    Workflow:
    1. User input → Clarification Agent
    2. If clarification is needed → END (return questions to client)
    3. If no clarification needed → Continue to next nodes (echo for now)
    """

    # Create graph with AgentState as the shared memory type
    graph = StateGraph(AgentState)

    # ----------------------------
    # REGISTER NODES
    # ----------------------------
    graph.add_node("clarification", clarification_node)
    graph.add_node("echo", echo_node)  # placeholder for next agent(s)

    # ----------------------------
    # ENTRY POINT
    # ----------------------------
    graph.set_entry_point("clarification")

    # ----------------------------
    # CONDITIONAL ROUTING LOGIC
    # ----------------------------
    graph.add_conditional_edges(
        "clarification",
        should_request_clarification,     # function returns: True or False
        {
            True: END,                    # If clarification needed → stop workflow
            False: "echo"                 # Otherwise continue to echo or next node
        }
    )

    # ----------------------------
    # ECHO → END
    # ----------------------------
    graph.add_edge("echo", END)

    # ----------------------------
    # COMPILE GRAPH
    # ----------------------------
    return graph.compile()
