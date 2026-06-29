import logging
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live

from agentX.agents.bm_agent import bm_agent
from agentX.agents.designer_agent import designer_agent
from agentX.agents.dev_agent import dev_agent
from agentX.agents.devops_agent import devops_agent
from agentX.agents.qa_agent import qa_agent
from agentX.agents.evaluator_agent import evaluator_agent

from agentX.tools.file_tools import cleanup_workspace_useless_files

logger = logging.getLogger("TeamLogger")
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
    prompt = f"Requirements:\n{requirements}\n\nDesign Specs:\n{design_specs}\n\nCRITICAL: You MUST write your final code directly into the workspace using your file tools. Do NOT just output code in markdown blocks. The evaluator will fail if the files are empty.\n\n{extra_prompt}"
    response = dev_agent.run(prompt)
    
    # Fallback for 3B models: if they output markdown instead of calling the tool
    content = response.content
    if "```" in content:
        import re
        from agentX.tools.file_tools import write_code_to_workspace
        
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
            write_code_to_workspace(filename, aggregated_code)
            logger.info(f"DEV fallback: automatically saved markdown to workspace/{filename}")
            
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
    prompt = f"Requirements:\n{requirements}\n\nDesign Specs:\n{design_specs}\n\nQA Report:\n{qa_report}\n\nEvaluate the code in workspace and return APPROVED or REJECTED with feedback."
    response = evaluator_agent.run(prompt)
    logger.info("EVALUATOR finished its task.")
    return response.content

def execute_project(prompt: str, **kwargs) -> str:
    """Executes the entire project pipeline sequentially: BM -> Designer -> Dev -> DevOps -> QA -> Evaluator -> Publish.
    This guarantees that the workspace is delivered to the user.
    USE THIS TOOL FOR ANY USER REQUEST, NO MATTER HOW SIMPLE OR COMPLEX (e.g. 'make a password generator', 'build a website', etc.)
    
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
            ask_devops("Create a Dockerfile to run the code in workspace.")
            
            # 5. QA
            qa_report = ask_qa("Run the code in Docker and verify it works.")
            
            # 6. Evaluator
            evaluator_result = ask_evaluator(requirements, design_specs, qa_report)
            
            # 7. Feedback Loop (Retry up to 5 times if failed)
            max_retries = 10
            for attempt in range(max_retries):
                if "APPROVED" in evaluator_result and "REJECTED" not in evaluator_result:
                    break
                    
                console.print(Panel(evaluator_result, title=f"[bold red]Evaluator Feedback (Attempt {attempt+1}/{max_retries})[/bold red]", border_style="red"))
                logger.warning(f"Evaluator rejected the code (Attempt {attempt+1}/{max_retries}). Giving the Dev a chance to fix it...")
                ask_dev(requirements, design_specs, f"The Evaluator rejected the code. Here is the feedback:\n{evaluator_result}\nCRITICAL: Fix any syntax errors and write the code again to workspace.")
                qa_report = ask_qa("Run the fixed code in Docker and verify it works.")
                evaluator_result = ask_evaluator(requirements, design_specs, qa_report)
            
            # 8. Publish / Cleanup
            if "APPROVED" not in evaluator_result or "REJECTED" in evaluator_result:
                console.print(Panel(evaluator_result, title="[bold red]Final Evaluator Rejection[/bold red]", border_style="red"))
                logger.warning("Evaluator rejected the code again, finishing anyway.")
            else:
                console.print(Panel(evaluator_result, title="[bold green]Final Evaluator Approval[/bold green]", border_style="green"))
                logger.info("Code was approved by Evaluator.")
                
            cleanup_result = cleanup_workspace_useless_files()
            
            estimate_and_progress(0, 'DONE', 100)
            logger.info("PIPELINE FINISHED.")
            return f"Project execution complete. {cleanup_result}"
        finally:
            live_display = None
