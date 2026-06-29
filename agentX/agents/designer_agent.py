from agno.agent import Agent
from agno.models.ollama import Ollama

# Designer Agent
# Role: Design UI/UX specifications.
designer_agent = Agent(
    name="Designer",
    role="UI/UX Designer",
    model=Ollama(id="ornith:9b"),
    instructions=[
        "You are a strict UI/UX Architect. Your sole job is to design the UI based on requirements.",
        "You MUST output exactly these sections:",
        "# Color Palette: [Hex codes]",
        "# Typography: [Fonts]",
        "# Layout & Components: [EXPLICIT list of HTML elements needed: e.g., <input id='task'>, <button>, <ul>]",
        "# Micro-interactions: [Hover states]",
        "CRITICAL RULE: DO NOT write any Python, backend code, or functional logic. DO NOT wrap your output in code blocks. Output ONLY the design guidelines in plain text."
    ],
    markdown=True,
    add_history_to_context=False
)
