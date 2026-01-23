from app.ai.state import AgentState


def echo_node(state: AgentState):
    user_input = state["user_input"]
    return {"output": f"Echo: {user_input}"}
