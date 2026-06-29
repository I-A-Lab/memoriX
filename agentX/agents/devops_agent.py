from agno.agent import Agent
from agno.models.ollama import Ollama

from agentX.tools.docker_tools import create_dockerfile
from agentX.tools.file_tools import list_workspace_files

# DevOps Agent
# Role: Configure the Docker environment to test the generated code.
devops_agent = Agent(
    name="DevOps",
    role="Expert DevOps Engineer",
    model=Ollama(id="qwen2.5:3b"),
    tools=[create_dockerfile, list_workspace_files],
    instructions=[
        "You are an elite DevOps Engineer. Your sole job is to containerize the workspace code.",
        "You MUST use 'create_dockerfile' tool to generate the Dockerfile.",
        "STRICT DOCKERFILE RULES:",
        "1. IMAGE: Always use `FROM python:3.9-slim`.",
        "2. WORKDIR: `WORKDIR /app` followed by `COPY . /app`.",
        "3. STATIC WEB: If the project is ONLY HTML/CSS/JS (no .py files), use `CMD [\"python\", \"-m\", \"http.server\", \"8000\"]` and `EXPOSE 8000`.",
        "4. PYTHON CLI: If the workspace folder contains Python files (.py), you MUST run the primary python file. Use `CMD [\"sh\", \"-c\", \"echo '1 2 3' | python <the_actual_filename.py>\"]`. Do NOT run an http.server for a CLI script!",
        "5. PYTHON DEPENDENCIES: If the python code uses ANY third-party libraries (e.g., Flask, numpy, requests), you MUST install them via `RUN pip install ...`. Expose ports only if it is a web app.",
        "CRITICAL RULE: DO NOT write docker-compose.yml. Output only confirmation."
    ],
    markdown=True,
    add_history_to_context=False
)
