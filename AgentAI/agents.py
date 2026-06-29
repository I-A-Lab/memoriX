import os
import logging
from pathlib import Path
from agno.agent import Agent
from agno.models.ollama import Ollama

# Log configuration
LOG_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / "agent_team.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("TeamLogger")

# Import custom tools
from tools.memory_tools import store_fact, retrieve_fact
from tools.docker_tools import create_dockerfile, run_tests_in_docker
from tools.file_tools import write_code_to_staging, list_staging_files, publish_to_workspace, clear_workspace

# Business Analyst Agent (BM)
# Role: Define requirements and technical tasks.
bm_agent = Agent(
    name="BM",
    role="Business Analyst",
    model=Ollama(id="qwen2.5:3b"),
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

# Designer Agent
# Role: Design UI/UX specifications.
designer_agent = Agent(
    name="Designer",
    role="UI/UX Designer",
    model=Ollama(id="qwen2.5:3b"),
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

# Developer Agent (Dev)
# Role: Write source code (Web + Backend) and associated unit tests in staging.
dev_agent = Agent(
    name="Dev",
    role="Full-Stack Developer",
    model=Ollama(id="qwen2.5:3b"),
    tools=[write_code_to_staging, list_staging_files],
    instructions=[
        "You are an elite Polyglot Developer.",
        "You MUST write production-ready code based on requirements and save it using 'write_code_to_staging'.",
        "If unable to use the tool, wrap your raw code in standard markdown blocks (e.g., ```python, ```html).",
        "STRICT RULES:",
        "1. LANGUAGES: Respect the requested languages EXACTLY. DO NOT write HTML/CSS/JS unless specifically requested. If asked for a Python CLI script, write ONLY Python.",
        "2. PURE NATIVE CODE: NEVER add markdown frontmatter (e.g. `--- title: ... ---`) inside HTML files. NEVER wrap CSS in <style> or JS in <script> tags when saving to their own files.",
        "3. STATIC WEB: IF generating a web project, YOU MUST create index.html, style.css, and script.js, and link them properly (`<link rel=\"stylesheet\" href=\"style.css\">` and `<script src=\"script.js\"></script>`).",
        "4. PYTHON SCRIPTS: YOU MUST, MUST, MUST include `if __name__ == '__main__':` at the very bottom and `print()` the final result! If you only define functions, the script will do nothing and YOU WILL FAIL! Do not worry about `EOFError`.",
        "5. FLASK/FASTAPI: Must bind to host '0.0.0.0' and expose the port.",
        "6. COMPLETE CODE: Never use placeholders like 'logic goes here'. Write complete logic. DO NOT unpack complex objects (e.g., `a, b = complex(...)` is invalid Python and will crash). Test your math logic mentally."
    ],
    markdown=True,
    add_history_to_context=False
)

# DevOps Agent
# Role: Configure the Docker environment to test the generated code.
from tools.docker_tools import create_dockerfile
devops_agent = Agent(
    name="DevOps",
    role="Expert DevOps Engineer",
    model=Ollama(id="qwen2.5:3b"),
    tools=[create_dockerfile, list_staging_files],
    instructions=[
        "You are an elite DevOps Engineer. Your sole job is to containerize the staging code.",
        "You MUST use 'create_dockerfile' tool to generate the Dockerfile.",
        "STRICT DOCKERFILE RULES:",
        "1. IMAGE: Always use `FROM python:3.9-slim`.",
        "2. WORKDIR: `WORKDIR /app` followed by `COPY . /app`.",
        "3. STATIC WEB: If the project is ONLY HTML/CSS/JS (no .py files), use `CMD [\"python\", \"-m\", \"http.server\", \"8000\"]` and `EXPOSE 8000`.",
        "4. PYTHON CLI: If the staging folder contains Python files (.py), you MUST run the primary python file. Use `CMD [\"sh\", \"-c\", \"echo '1 2 3' | python <the_actual_filename.py>\"]`. Do NOT run an http.server for a CLI script!",
        "5. PYTHON DEPENDENCIES: If the python code uses ANY third-party libraries (e.g., Flask, numpy, requests), you MUST install them via `RUN pip install ...`. Expose ports only if it is a web app.",
        "CRITICAL RULE: DO NOT write docker-compose.yml. Output only confirmation."
    ],
    markdown=True,
    add_history_to_context=False
)

# QA Agent (Tester)
# Role: Validate the generated code and the Docker environment.
qa_agent = Agent(
    name="QA",
    role="Quality Assurance Engineer",
    model=Ollama(id="qwen2.5:3b"),
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

# Evaluator Agent
# Role: Evaluate the final code against requirements, UI/UX specs, and norms.
evaluator_agent = Agent(
    name="Evaluator",
    role="Code Quality Evaluator",
    model=Ollama(id="qwen2.5:3b"),
    tools=[list_staging_files],
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

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live

console = Console()
live_display = None

def estimate_and_progress(eta_minutes: int = 0, current_step: str = "PROCESSING", percentage: int = 0) -> str:
    """Use this tool to update the progress bar in the user interface.
    Args:
        eta_minutes (int): Estimated time in minutes.
        current_step (str): The current step (e.g., 'PLANNING', 'DEV', 'DOCKER', 'TEST', 'EVALUATION').
        percentage (int): Progress percentage (0 to 100).
    """
    bar_length = 40
    filled = int(bar_length * percentage // 100)
    
    step_colors = {
        'REQUIREMENTS': 'cyan',
        'DESIGN': 'magenta',
        'DEV': 'yellow',
        'DOCKER': 'blue',
        'QA': 'yellow',
        'EVALUATION': 'magenta',
        'DONE': 'green'
    }
    
    color = step_colors.get(current_step, 'white')
    bar_filled = "━" * filled
    bar_empty = "╌" * (bar_length - filled)
    
    progress_text = Text()
    progress_text.append(f"[{current_step.center(12)}]", style=f"bold {color}")
    progress_text.append(f"  {bar_filled}", style=f"bold {color}")
    progress_text.append(bar_empty, style="dim")
    progress_text.append(f"  {percentage:>3}%", style="bold white")
    
    panel = Panel(progress_text, border_style="dim", expand=False)
    
    if live_display is not None:
        live_display.update(panel)
    else:
        console.print(panel)
        
    msg_log = f"[{'='*filled}{'-'*(bar_length-filled)}] {percentage:>3}% | STEP: {current_step}"
    logger.info(msg_log)
    return "Progress updated and displayed to the user."

def ask_bm(prompt: str) -> str:
    """Delegates a requirement analysis task to the Business Analyst (BM)."""
    estimate_and_progress(0, 'REQUIREMENTS', 10)
    logger.info(f"MANAGER delegates to BM: {prompt}")
    response = bm_agent.run(prompt)
    logger.info("BM finished its task.")
    return response.content

def ask_designer(requirements: str) -> str:
    """Delegates UI/UX specs creation to the Designer."""
    estimate_and_progress(0, 'DESIGN', 25)
    logger.info("MANAGER delegates to DESIGNER.")
    response = designer_agent.run(f"Create design specs based on these requirements:\n{requirements}")
    logger.info("DESIGNER finished its task.")
    return response.content

def ask_dev(requirements: str, design_specs: str, extra_prompt: str = "") -> str:
    """Delegates a coding task to the Developer Agent."""
    estimate_and_progress(0, 'DEV', 40)
    logger.info("MANAGER delegates to DEV.")
    prompt = f"Requirements:\n{requirements}\n\nDesign Specs:\n{design_specs}\n\n{extra_prompt}"
    response = dev_agent.run(prompt)
    
    # Fallback for 3B models: if they output markdown instead of calling the tool
    content = response.content
    if "```" in content:
        import re
        from tools.file_tools import write_code_to_staging
        
        # Match all code blocks: ```language\n code \n```
        matches = re.findall(r"```([a-zA-Z0-9_+#]+)\n(.*?)\n```", content, re.DOTALL)
        
        file_contents = {}
        
        for lang, code in matches:
            lang = lang.lower()
            
            # Clean up stubborn 3B model artifacts
            code = re.sub(r"^---[\s\S]*?---\n+", "", code) # Strip frontmatter
            if lang in ["css"]:
                code = re.sub(r"^<style.*?>\n?", "", code, flags=re.IGNORECASE)
                code = re.sub(r"\n?</style>$", "", code, flags=re.IGNORECASE)
            elif lang in ["javascript", "js"]:
                code = re.sub(r"^<script.*?>\n?", "", code, flags=re.IGNORECASE)
                code = re.sub(r"\n?</script>$", "", code, flags=re.IGNORECASE)
                
            ext = "txt"
            filename = "file.txt"
            
            if lang in ["python", "py"]:
                filename = "main.py"
            elif lang in ["html"]:
                filename = "index.html"
            elif lang in ["css"]:
                filename = "style.css"
            elif lang in ["javascript", "js"]:
                filename = "script.js"
            elif lang in ["typescript", "ts"]:
                filename = "main.ts"
            elif lang in ["java"]:
                filename = "Main.java"
            elif lang in ["c", "cpp", "c++", "cxx"]:
                filename = "main.cpp" if lang != "c" else "main.c"
            elif lang in ["rust", "rs"]:
                filename = "main.rs"
            elif lang in ["go"]:
                filename = "main.go"
            elif lang in ["ruby", "rb"]:
                filename = "main.rb"
            elif lang in ["php"]:
                filename = "index.php"
            elif lang in ["sh", "bash"]:
                filename = "script.sh"
            else:
                filename = f"snippet.{lang}"
                
            if filename in file_contents:
                file_contents[filename] += "\n\n" + code
            else:
                file_contents[filename] = code
                
        for filename, aggregated_code in file_contents.items():
            write_code_to_staging(filename, aggregated_code)
            logger.info(f"DEV fallback: automatically saved markdown to staging/{filename}")
            
    logger.info("DEV finished its task.")
    return response.content

def ask_devops(prompt: str) -> str:
    """Delegates a deployment/Docker task to the DevOps Agent."""
    estimate_and_progress(0, 'DOCKER', 60)
    logger.info(f"MANAGER delegates to DEVOPS: {prompt}")
    response = devops_agent.run(prompt)
    logger.info("DEVOPS finished its task.")
    return response.content

def ask_qa(prompt: str) -> str:
    """Delegates a testing task to the QA Agent."""
    estimate_and_progress(0, 'QA', 80)
    logger.info(f"MANAGER delegates to QA: {prompt}")
    response = qa_agent.run(prompt)
    logger.info("QA finished its task.")
    return response.content

def ask_evaluator(requirements: str, design_specs: str, qa_report: str) -> str:
    """Delegates code evaluation to the Evaluator Agent."""
    estimate_and_progress(0, 'EVALUATION', 90)
    logger.info("MANAGER delegates to EVALUATOR.")
    prompt = f"Requirements:\n{requirements}\n\nDesign Specs:\n{design_specs}\n\nQA Report:\n{qa_report}\n\nEvaluate the code in staging and return APPROVED or REJECTED with feedback."
    response = evaluator_agent.run(prompt)
    logger.info("EVALUATOR finished its task.")
    return response.content

def execute_project(prompt: str) -> str:
    """Executes the entire project pipeline sequentially: BM -> Designer -> Dev -> DevOps -> QA -> Evaluator -> Publish.
    This guarantees that the workspace is delivered to the user.
    
    Args:
        prompt (str): The user's original request.
    """
    global live_display
    logger.info("PIPELINE STARTED.")
    
    with Live(console=console, refresh_per_second=4, transient=False) as live:
        live_display = live
        try:
            # 1. BM (Requirements)
            requirements = ask_bm(prompt)
    
            # 2. Designer
            if "REQUIRES_UI: YES" in requirements.upper():
                design_specs = ask_designer(requirements)
            else:
                logger.info("MANAGER skips DESIGNER (No UI required).")
                estimate_and_progress(0, 'DESIGN', 25)
                design_specs = "No UI required. Focus on backend logic and CLI functionality."
            
            # 3. Dev
            ask_dev(requirements, design_specs)
            
            # 4. DevOps
            ask_devops("Create a Dockerfile to run the code in staging.")
            
            # 5. QA
            qa_report = ask_qa("Run the code in Docker and verify it works.")
            
            # 6. Evaluator
            evaluator_result = ask_evaluator(requirements, design_specs, qa_report)
            
            # 7. Feedback Loop (Retry up to 3 times if failed)
            max_retries = 3
            for attempt in range(max_retries):
                if "REJECTED" not in evaluator_result:
                    break
                    
                logger.warning(f"Evaluator rejected the code (Attempt {attempt+1}/{max_retries}). Giving the Dev a chance to fix it...")
                ask_dev(requirements, design_specs, f"The Evaluator rejected the code. Here is the feedback:\n{evaluator_result}\nCRITICAL: Fix any syntax errors and write the code again to staging.")
                qa_report = ask_qa("Run the fixed code in Docker and verify it works.")
                evaluator_result = ask_evaluator(requirements, design_specs, qa_report)
            
            # 8. Publish
            if "REJECTED" in evaluator_result:
                logger.warning("Evaluator rejected the code again, publishing anyway.")
            else:
                logger.info("Code was approved by Evaluator.")
                
            publish_result = publish_to_workspace()
            
            from tools.file_tools import clear_workspace
            # Notice: we don't clear workspace here, it's done by publish_to_workspace filtering.
            
            estimate_and_progress(0, 'DONE', 100)
            logger.info("PIPELINE FINISHED.")
            return f"Project execution complete. {publish_result}"
        finally:
            live_display = None

manager_agent = Agent(
    name="Manager",
    role="AI Project Manager and Orchestrator",
    model=Ollama(id="qwen2.5:3b"),
    tools=[execute_project],
    instructions=[
        "You are the headless Orchestrator Engine. You are NOT a conversational AI.",
        "Your ONLY job is to take the user's prompt and call 'execute_project' EXACTLY ONCE per user request.",
        "STRICT RULES:",
        "1. DO NOT ask the user any questions. DO NOT use conversational fillers (e.g., 'Sure, I will do that').",
        "2. Call 'execute_project' immediately.",
        "3. Once the tool returns, YOU MUST STOP. DO NOT CALL THE TOOL AGAIN IN THE SAME TURN! Output the final string and finish your response."
    ],
    markdown=True,
    add_history_to_context=False
)
