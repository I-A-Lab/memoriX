from agno.agent import Agent
from agno.models.ollama import Ollama

from agentX.tools.docker_tools import run_tests_in_docker

# QA Agent (Tester)
# Role: Validate the generated code and the Docker environment.
qa_agent = Agent(
    name="QA",
    role="Quality Assurance Engineer",
    model=Ollama(id="ornith:9b"),
    tools=[run_tests_in_docker],
    instructions=[
        "You are a strict QA Engineer. Your job is to test the code using 'run_tests_in_docker'.",
        "You MUST output exactly these sections:",
        "# Environment: [What was tested]",
        "# Execution Logs: [Summary of stdout/stderr]",
        "# Defect Analysis: [Explain any errors, tracebacks, or logical flaws]",
        "# Final Verdict: [MUST be exactly 'SUCCESS' or 'FAILURE']",
        "STRICT RULES:",
        "1. If the tool reports exit code 0 and no exceptions, output 'SUCCESS'.",
        "2. If the tool reports a non-zero exit code, crashes, or timeout, output 'FAILURE' and detail the error."
    ],
    markdown=True,
    add_history_to_context=False
)
