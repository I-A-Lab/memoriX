import os
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

# Load environment variables (API keys, e.g., GOOGLE_API_KEY for Gemini)
load_dotenv()

from agents import manager_agent

from tools.file_tools import WORKSPACE_DIR, clear_workspace, clear_staging

def main():
    console = Console()
    console.print()
    console.print(Panel(
        "[bold cyan]AGNO CODER AGENTS TEAM WITH TITAN MEMORY[/bold cyan]", 
        title="[bold]SYSTEM START[/bold]", 
        border_style="dim", 
        expand=False
    ))
    console.print()
    
    # Always wipe staging clean on launch
    clear_staging()
    
    # Verify if workspace is empty
    if WORKSPACE_DIR.exists() and any(WORKSPACE_DIR.iterdir()):
        from rich.prompt import Confirm
        console.print()
        if Confirm.ask("[bold yellow]⚠️ The 'workspace' folder is not empty. Do you want to clear it before starting?[/bold yellow]"):
            clear_workspace()
            console.print("[bold green]Workspace cleared successfully.[/bold green]\n")
        else:
            console.print("[dim]Keeping old files in the workspace.[/dim]\n")

    from rich.prompt import Prompt
    from rich.markdown import Markdown
    
    console.print(Panel(
        "[bold green]Manager:[/bold green] Ready! I orchestrate Coder, DevOps, and Tester.\nType 'exit' or 'quit' to exit.",
        border_style="green"
    ))
    
    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]User[/bold cyan]")
            if user_input.lower() in ['exit', 'quit']:
                console.print("\n[bold yellow]System shutting down.[/bold yellow]")
                break
            if not user_input.strip():
                continue
                
            response = manager_agent.run(user_input)
            
            console.print()
            console.print(Panel(
                Markdown(response.content),
                title="[bold green]Manager[/bold green]",
                border_style="green"
            ))
            
        except KeyboardInterrupt:
            console.print("\n[bold yellow]System shutting down.[/bold yellow]")
            break

if __name__ == "__main__":
    main()
