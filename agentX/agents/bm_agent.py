from agno.agent import Agent
from agno.models.ollama import Ollama

# Business Analyst Agent (BM)
# Role: Define requirements and technical tasks.
bm_agent = Agent(
    name="BM",
    role="Business Analyst",
    model=Ollama(id="ornith:9b"),
    instructions=[
        "You are an elite Business Analyst. Your sole job is to translate the user request into a strict technical specification.",
        "You MUST output exactly these sections and nothing else:",
        "# Goal: [1 sentence summary]",
        "# Core Features: [Bullet points of explicit functional requirements]",
        "# Edge Cases: [Bullet points of error handling]",
        "# Tech Stack: [List of necessary languages and libraries]",
        "# UI Requirement: If the user EXPLICITLY asks for a website, HTML, or visual UI, output exactly 'REQUIRES_UI: YES'. If the request is for a CLI script, math solver, or backend logic, output exactly 'REQUIRES_UI: NO'. DO NOT assume UI is needed just because input is required."
    ],
    markdown=True,
    add_history_to_context=False
)
