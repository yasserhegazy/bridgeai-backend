# app/ai/graph.py

from langgraph.graph import END, StateGraph

# Nodes
from app.ai.nodes.clarification import clarification_node, should_request_clarification
from app.ai.nodes.echo_node import echo_node
from app.ai.nodes.memory_node import memory_node
from app.ai.nodes.suggestions import suggestions_node
from app.ai.nodes.suggestions.suggestions_node import should_generate_suggestions
from app.ai.nodes.template_filler import template_filler_node
from app.ai.state import AgentState


def create_graph():
    """
    Create the LangGraph workflow with:
    1. Clarification Agent - Detects ambiguities and asks clarifying questions
    2. Template Filler Agent - Maps clarified requirements to CRS template

    Workflow:
    1. User input → Clarification Agent
    2. If clarification is needed → END (return questions to client)
    3. If no clarification needed → Template Filler Agent
    4. Template Filler fills CRS → Memory (store requirement) → END
    """

    # Create graph with AgentState as the shared memory type
    graph = StateGraph(AgentState)

    # ----------------------------
    # REGISTER NODES
    # ----------------------------
    graph.add_node("clarification", clarification_node)
    graph.add_node("memory", memory_node)
    graph.add_node("template_filler", template_filler_node)
    graph.add_node("suggestions", suggestions_node)
    graph.add_node("echo", echo_node)  # placeholder for future agent(s)

    # ----------------------------
    # ENTRY POINT
    # ----------------------------
    graph.set_entry_point("clarification")

    # ----------------------------
    # CLARIFICATION -> TEMPLATE FILLER or END
    # ----------------------------
    def route_after_clarification(state: AgentState):
        """
        Route after clarification:
        - If needs_clarification is True → END (return questions to client)
        - If intent is not 'requirement' → END (echo or greeting)
        - Otherwise → END (template filler now runs in background)
        """
        needs_clarification = state.get("needs_clarification", False)
        intent = state.get("intent", "requirement")
        
        # Always route to END - background CRS generation handles template filling
        # This prevents output conflicts and allows real-time updates
        return END

    graph.add_conditional_edges(
        "clarification",
        route_after_clarification,
        {
            END: END,
        }
    )

    # Note: Template filler and memory nodes are no longer part of the main graph.
    # CRS generation now runs in background via BackgroundCRSGenerator service.
    # The graph only handles clarification and conversational responses.

    # Return compiled graph
    return graph.compile()
