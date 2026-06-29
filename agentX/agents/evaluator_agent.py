from agno.agent import Agent
from agno.models.ollama import Ollama

from agentX.tools.file_tools import list_workspace_files

# Evaluator Agent
# Role: Evaluate the final code against requirements, UI/UX specs, and norms.
evaluator_agent = Agent(
    name="Evaluator",
    role="Code Quality Evaluator",
    model=Ollama(id="qwen2.5:3b"),
    tools=[list_workspace_files],
    instructions=[
        "You are the final Code Evaluator.",
        "You MUST output exactly these sections:",
        "# Analysis: [Does the code meet requirements? Are there syntax errors?]",
        "# Verdict: [MUST be exactly 'APPROVED' or 'REJECTED']",
        "# Feedback for Dev: [If rejected, provide EXACT, actionable steps to fix the code.]",
        "STRICT RULES:",
        "1. If QA verdict is 'FAILURE', you MUST output 'REJECTED'.",
        "2. If core requirements are missing, you MUST output 'REJECTED'.",
        "3. If QA verdict is 'SUCCESS' and requirements are met, output 'APPROVED'."
    ],
    markdown=True,
    add_history_to_context=False
)
