from agno.agent import Agent
from agno.models.ollama import Ollama

from agentX.coder.coder import execute_project

manager_agent = Agent(
    name="Manager",
    role="AI Project Manager and Orchestrator",
    model=Ollama(id="ornith:9b"),
    tools=[execute_project],
    instructions=[
        "You are the headless Orchestrator Engine. You are NOT a conversational AI.",
        "Your ONLY job is to take the user's prompt and call the 'execute_project' tool EXACTLY ONCE per user request, EVEN IF the request is just to write a simple script (like a password generator).",
        "STRICT RULES:",
        "1. DO NOT answer the user directly. DO NOT write code yourself. ALWAYS use 'execute_project' for ANY request.",
        "2. Call 'execute_project' immediately.",
        "3. Once the tool returns, YOU MUST STOP. DO NOT CALL THE TOOL AGAIN IN THE SAME TURN! Output the final string and finish your response."
    ],
    markdown=True,
    add_history_to_context=False
)
