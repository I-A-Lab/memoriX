import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich.prompt import Prompt
from dotenv import load_dotenv

# Ensure we can import from agentX
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from agentX.agents.slm_breakdown_agent import slm_breakdown_agent

load_dotenv()
console = Console()

def display_breakdown(breakdown_data) -> None:
    """Displays the breakdown data using rich Tree."""
    
    # The agent returns the Pydantic object directly because structured_outputs=True
    project_tree = Tree(f"[bold cyan]Project: {breakdown_data.project_name}[/bold cyan]\n[dim]{breakdown_data.summary}[/dim]")
    
    for module in breakdown_data.modules:
        module_node = project_tree.add(f"[bold blue] Module: {module.name}[/bold blue] - {module.description}")
        
        # Display Standalone Functions
        if module.functions:
            func_tree = module_node.add("[bold magenta]Functions[/bold magenta]")
            for func in module.functions:
                params = ", ".join(func.parameters) if func.parameters else "None"
                func_tree.add(f"[green]ƒ {func.name}({params}) -> {func.return_type}[/green]\n   [dim]{func.description}[/dim]")
                
        # Display Classes
        if module.classes:
            class_tree = module_node.add("[bold yellow]Classes[/bold yellow]")
            for cls in module.classes:
                cls_node = class_tree.add(f"[bold yellow]C {cls.name}[/bold yellow] - {cls.description}")
                for method in cls.methods:
                    params = ", ".join(method.parameters) if method.parameters else "None"
                    cls_node.add(f"[green]m {method.name}({params}) -> {method.return_type}[/green]\n   [dim]{method.description}[/dim]")
                    
    console.print(Panel(project_tree, title="[bold green]SLM Breakdown Output[/bold green]", border_style="green"))

def main():
    console.print(Panel("[bold cyan]HYBRID SLM BREAKDOWN SIMULATOR[/bold cyan]", title="[bold]STEP 1 & 2[/bold]", border_style="dim", expand=False))
    console.print("[dim]This script simulates taking a user request and breaking it down into Modules -> Classes -> Functions using the SLM.[/dim]\n")
    
    user_input = Prompt.ask("[bold cyan]Enter your software request[/bold cyan]")
    
    if not user_input.strip():
        console.print("[red]Request cannot be empty.[/red]")
        return
        
    console.print("\n[yellow] Analyzing request and generating algorithmic breakdown...[/yellow]")
    
    try:
        # Run the agent to get the structured response
        response = slm_breakdown_agent.run(user_input)
        
        # response.content will be the Pydantic model instance if structured_outputs=True
        # Check if response.content is the model directly
        if hasattr(response, 'content') and hasattr(response.content, 'project_name'):
            breakdown_data = response.content
            display_breakdown(breakdown_data)
        else:
            console.print("[red]Failed to generate valid structured output.[/red]")
            console.print(response)
            
    except Exception as e:
        console.print(f"[bold red]Error during breakdown:[/bold red] {e}")

if __name__ == "__main__":
    main()
