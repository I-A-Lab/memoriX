import logging
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.tree import Tree
from rich.prompt import Confirm

from agentX.agents.bm_agent import bm_agent
from agentX.agents.designer_agent import designer_agent
from agentX.agents.dev_agent import dev_agent
from agentX.agents.devops_agent import devops_agent
from agentX.agents.qa_agent import qa_agent
from agentX.agents.evaluator_agent import evaluator_agent
from agentX.agents.slm_breakdown_agent import slm_breakdown_agent

from agentX.tools.file_tools import cleanup_workspace_useless_files

import time

logger = logging.getLogger("TeamLogger")
console = Console()
live_display = None
pipeline_start_time = None

current_pipeline_step = "PROCESSING"
current_pipeline_percentage = 0

class PipelineProgress:
    def __rich__(self):
        bar_length = 40
        percentage = current_pipeline_percentage
        current_step = current_pipeline_step
        filled = int(bar_length * percentage // 100)
        
        step_colors = {
            'BREAKDOWN': 'cyan',
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
        
        global pipeline_start_time
        if pipeline_start_time is not None:
            elapsed = int(time.time() - pipeline_start_time)
            mins, secs = divmod(elapsed, 60)
            progress_text.append(f"  [{mins:02}:{secs:02}]", style="bold cyan")
            
        return Panel(progress_text, border_style="dim", expand=False)

def estimate_and_progress(eta_minutes: int = 0, current_step: str = "PROCESSING", percentage: int = 0) -> str:
    """Use this tool to update the progress bar in the user interface.
    Args:
        eta_minutes (int): Estimated time in minutes.
        current_step (str): The current step (e.g., 'PLANNING', 'DEV', 'DOCKER', 'TEST', 'EVALUATION').
        percentage (int): Progress percentage (0 to 100).
    """
    global current_pipeline_step, current_pipeline_percentage, live_display
    current_pipeline_step = current_step
    current_pipeline_percentage = percentage
    
    if live_display is None:
        console.print(PipelineProgress())
        
    bar_length = 40
    filled = int(bar_length * percentage // 100)
    msg_log = f"[{'='*filled}{'-'*(bar_length-filled)}] {percentage:>3}% | STEP: {current_step}"
    logger.info(msg_log)
    return "Progress updated and displayed to the user."

def ask_slm_breakdown(prompt: str) -> tuple[str, any]:
    """Delegates a breakdown task to the SLM Breakdown Agent."""
    estimate_and_progress(0, 'BREAKDOWN', 5)
    logger.info("MANAGER delegates to SLM BREAKDOWN.")
    
    response = slm_breakdown_agent.run(prompt)
    if hasattr(response, 'content') and hasattr(response.content, 'project_name'):
        breakdown_data = response.content
        project_tree = Tree(f"[bold cyan]Project: {breakdown_data.project_name}[/bold cyan]\n[dim]{breakdown_data.summary}[/dim]")
        
        for module in breakdown_data.modules:
            module_node = project_tree.add(f"[bold blue] Module: {module.name}[/bold blue] - {module.description}")
            if module.functions:
                func_tree = module_node.add("[bold magenta]Functions[/bold magenta]")
                for func in module.functions:
                    params = ", ".join(func.parameters) if func.parameters else "None"
                    func_tree.add(f"[green]ƒ {func.name}({params}) -> {func.return_type}[/green]\n   [dim]{func.description}[/dim]")
            if module.classes:
                class_tree = module_node.add("[bold yellow]Classes[/bold yellow]")
                for cls in module.classes:
                    cls_node = class_tree.add(f"[bold yellow]C {cls.name}[/bold yellow] - {cls.description}")
                    for method in cls.methods:
                        params = ", ".join(method.parameters) if method.parameters else "None"
                        cls_node.add(f"[green]m {method.name}({params}) -> {method.return_type}[/green]\n   [dim]{method.description}[/dim]")
                        
        console.print(Panel(project_tree, title="[bold green]SLM Breakdown Output[/bold green]", border_style="green"))
        
        # Convert breakdown to a textual representation for the prompt
        breakdown_text = f"Architecture Breakdown:\nProject: {breakdown_data.project_name}\n"
        for module in breakdown_data.modules:
            breakdown_text += f"\nModule: {module.name} - {module.description}\n"
            for cls in module.classes:
                breakdown_text += f"  Class: {cls.name} - {cls.description}\n"
                for method in cls.methods:
                    params = ", ".join(method.parameters) if method.parameters else "None"
                    breakdown_text += f"    Method: {method.name}({params}) -> {method.return_type}\n"
            for func in module.functions:
                params = ", ".join(func.parameters) if func.parameters else "None"
                breakdown_text += f"  Function: {func.name}({params}) -> {func.return_type}\n"
        
        return breakdown_text, breakdown_data
    else:
        console.print("[red]Failed to generate valid structured output.[/red]")
        return "", None

def ask_bm(prompt: str, architecture: str = "") -> str:
    """Delegates a requirement analysis task to the Business Analyst (BM)."""
    estimate_and_progress(0, 'REQUIREMENTS', 10)
    logger.info(f"MANAGER delegates to BM: {prompt}")
    
    full_prompt = prompt
    if architecture:
        full_prompt += f"\n\nHere is the validated architectural breakdown to strictly follow:\n{architecture}"
        
    response = bm_agent.run(full_prompt)
    logger.info("BM finished its task.")
    return response.content

def ask_designer(requirements: str) -> str:
    """Delegates UI/UX specs creation to the Designer."""
    estimate_and_progress(0, 'DESIGN', 25)
    logger.info("MANAGER delegates to DESIGNER.")
    response = designer_agent.run(f"Create design specs based on these requirements:\n{requirements}")
    logger.info("DESIGNER finished its task.")
    return response.content

def ask_dev(requirements: str, design_specs: str, architecture: str = "", extra_prompt: str = "") -> str:
    """Delegates a coding task to the Developer Agent."""
    estimate_and_progress(0, 'DEV', 40)
    logger.info("MANAGER delegates to DEV.")
    prompt = f"Requirements:\n{requirements}\n\nDesign Specs:\n{design_specs}\n\n"
    if architecture:
        prompt += f"Architecture Blueprint (STRICTLY FOLLOW THIS):\n{architecture}\n\n"
    prompt += f"CRITICAL: You MUST write your final code directly into the workspace using your file tools. Do NOT just output code in markdown blocks. The evaluator will fail if the files are empty.\n\n{extra_prompt}"
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
    """Delegates infrastructure tasks to DevOps."""
    estimate_and_progress(0, 'DOCKER', 60)
    logger.info("MANAGER delegates to DEVOPS.")
    response = devops_agent.run(prompt)
    logger.info("DEVOPS finished its task.")
    return response.content

def run_fragmented_dev(requirements: str, design_specs: str, architecture_breakdown_text: str, architecture_breakdown_data: any, extra_feedback: str = ""):
    """Runs the Dev agent sequentially on each module to prevent context hallucination."""
    if architecture_breakdown_data and architecture_breakdown_data.modules:
        for module in architecture_breakdown_data.modules:
            estimate_and_progress(0, 'DEV', 40)
            logger.info(f"MANAGER delegates module '{module.name}' to DEV.")
            module_instruction = f"CRITICAL FOCUS: Implement ONLY the module '{module.name}'. Do NOT implement other modules right now.\n"
            module_instruction += f"Module Description: {module.description}\n"
            if module.classes:
                module_instruction += "Classes to implement:\n"
                for cls in module.classes:
                    module_instruction += f"- {cls.name}: {cls.description}\n"
            if module.functions:
                module_instruction += "Functions to implement:\n"
                for func in module.functions:
                    module_instruction += f"- {func.name}: {func.description}\n"
            
            if extra_feedback:
                module_instruction += f"\nEVALUATOR FEEDBACK TO FIX (Only apply to this module if relevant):\n{extra_feedback}\n"
                
            ask_dev(requirements, design_specs, architecture=architecture_breakdown_text, extra_prompt=module_instruction)
    else:
        ask_dev(requirements, design_specs, architecture=architecture_breakdown_text, extra_prompt=extra_feedback)

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

def execute_project(prompt: str = "", **kwargs) -> str:
    """Executes the entire project pipeline sequentially: BM -> Designer -> Dev -> DevOps -> QA -> Evaluator -> Publish.
    This guarantees that the workspace is delivered to the user.
    USE THIS TOOL FOR ANY USER REQUEST, NO MATTER HOW SIMPLE OR COMPLEX (e.g. 'make a password generator', 'build a website', etc.)
    
    Args:
        prompt (str): The user's original request.
    """
    if not prompt:
        prompt = kwargs.get("prompt", "")
    if not prompt:
        return "Error: You must provide a 'prompt' string argument."
        
    global live_display, pipeline_start_time
    pipeline_start_time = time.time()
    logger.info("PIPELINE STARTED.")
    
    # 0. SLM Breakdown (Inside Live display, but stopped before prompt)
    with Live(PipelineProgress(), console=console, refresh_per_second=4, transient=False) as live:
        live_display = live
        architecture_breakdown_text, architecture_breakdown_data = ask_slm_breakdown(prompt)
    live_display = None
    
    while architecture_breakdown_text:
        if not Confirm.ask("\n[bold yellow]Do you want to proceed with this architecture?[/bold yellow]"):
            logger.info("User rejected the architecture. Generating a new one.")
            console.print("\n[yellow] Generating an alternative architecture breakdown...[/yellow]")
            prompt += "\n\nCRITICAL: The user rejected your previous architectural proposal. Please provide a DIFFERENT architecture breakdown, with alternative module names, structures, or approaches."
            with Live(PipelineProgress(), console=console, refresh_per_second=4, transient=False) as live:
                live_display = live
                architecture_breakdown_text, architecture_breakdown_data = ask_slm_breakdown(prompt)
            live_display = None
        else:
            break
            
    if not architecture_breakdown_text:
        return "Project cancelled: SLM Breakdown failed."
            
    with Live(PipelineProgress(), console=console, refresh_per_second=4, transient=False) as live:
        live_display = live
        try:
            # 1. BM (Requirements)
            requirements = ask_bm(prompt, architecture_breakdown_text)
    
            # 2. Designer
            if "REQUIRES_UI: YES" in requirements.upper():
                design_specs = ask_designer(requirements)
            else:
                logger.info("MANAGER skips DESIGNER (No UI required).")
                estimate_and_progress(0, 'DESIGN', 25)
                design_specs = "No UI required. Focus on backend logic and CLI functionality."
            
            # 3. Dev
            run_fragmented_dev(requirements, design_specs, architecture_breakdown_text, architecture_breakdown_data)
            
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
                
                feedback = f"The Evaluator rejected the code. Here is the feedback:\n{evaluator_result}\nCRITICAL: Fix any errors mentioned. Modify ONLY what needs to be fixed in your module."
                run_fragmented_dev(requirements, design_specs, architecture_breakdown_text, architecture_breakdown_data, extra_feedback=feedback)
                
                ask_devops("Recreate or fix the Dockerfile to run the code in workspace if needed.")
                qa_report = ask_qa("Run the fixed code in Docker and verify it works.")
                evaluator_result = ask_evaluator(requirements, design_specs, qa_report)
            
            # 8. Publish / Cleanup
            if "APPROVED" not in evaluator_result or "REJECTED" in evaluator_result:
                console.print(Panel(evaluator_result, title="[bold red]Final Evaluator Rejection[/bold red]", border_style="red"))
                logger.warning("Evaluator rejected the code again, finishing anyway.")
                cleanup_result = "Cleanup skipped due to rejection (for debugging)."
            else:
                console.print(Panel(evaluator_result, title="[bold green]Final Evaluator Approval[/bold green]", border_style="green"))
                logger.info("Code was approved by Evaluator.")
                cleanup_result = cleanup_workspace_useless_files()
            
            estimate_and_progress(0, 'DONE', 100)
            logger.info("PIPELINE FINISHED.")
            return f"Project execution complete. {cleanup_result}"
        finally:
            live_display = None
