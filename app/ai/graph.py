# app/ai/graph.py

from langgraph.graph import StateGraph, END
from app.ai.state import AgentState

# Nodes
from app.ai.nodes.clarification import clarification_node, should_request_clarification
from app.ai.nodes.memory_node import memory_node
from app.ai.nodes.template_filler import template_filler_node
from app.ai.nodes.echo_node import echo_node


def create_graph():
    """
    Create the LangGraph workflow with:
    1. Clarification Agent - Detects ambiguities and asks clarifying questions
    2. Template Filler Agent - Maps clarified requirements to CRS template

    Workflow:
    1. User input → Clarification Agent
    2. If clarification is needed → END (return questions to client)
    3. If no clarification needed → Template Filler Agent
    4. Template Filler fills CRS → END (return CRS to client)
    """

    # Create graph with AgentState as the shared memory type
    graph = StateGraph(AgentState)

    # ----------------------------
    # REGISTER NODES
    # ----------------------------
    graph.add_node("clarification", clarification_node)
    graph.add_node("memory", memory_node)
    graph.add_node("template_filler", template_filler_node)
    graph.add_node("echo", echo_node)  # placeholder for future agent(s)

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
            False: "memory"               # Otherwise continue to memory node
            False: "template_filler"      # Otherwise continue to template filler
        }
    )

    # ----------------------------
    # MEMORY → END
    # ----------------------------
    graph.add_edge("memory", END)
    # TEMPLATE FILLER → END
    # ----------------------------
    graph.add_edge("template_filler", END)

    # ----------------------------
    # COMPILE GRAPH
    # ----------------------------
    return graph.compile()
