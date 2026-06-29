import os
import subprocess
from pathlib import Path

STAGING_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "staging"
WORKSPACE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "workspace"

def create_dockerfile(content: str, **kwargs) -> str:
    """Creates a Dockerfile in the staging folder for the test environment.
    
    Args:
        content (str): The full content of the Dockerfile.
    """
    try:
        # Strip markdown tags just in case
        import re
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```[a-zA-Z]*\n", "", content)
            content = re.sub(r"\n```$", "", content)
            
        with open(STAGING_DIR / "Dockerfile", "w", encoding="utf-8") as f:
            f.write(content)
            
        # Automatically generate a standard docker-compose.yml so the AI doesn't have to
        compose_content = """version: '3.8'
services:
  testapp:
    build: .
"""
        with open(STAGING_DIR / "docker-compose.yml", "w", encoding="utf-8") as f:
            f.write(compose_content)
            
        return "Dockerfile and docker-compose.yml successfully created in staging."
    except Exception as e:
        return f"Error creating Docker files: {e}"

def run_tests_in_docker(**kwargs) -> str:
    """Builds and runs Docker containers in staging to launch tests.
    Returns the execution logs so the tester can evaluate the code.
    
    Returns:
        str: The full execution logs (stdout and stderr).
    """
    try:
        import time
        # Start the container in detached mode
        subprocess.run(
            ["docker", "compose", "up", "-d", "--build"],
            cwd=str(STAGING_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        
        # Wait 5 seconds to let it crash if it's going to crash, or start serving
        time.sleep(5)
        
        # Check if the container is still running
        ps_result = subprocess.run(
            ["docker", "compose", "ps", "--services", "--filter", "status=running"],
            cwd=str(STAGING_DIR),
            capture_output=True,
            text=True
        )
        
        is_running = "testapp" in ps_result.stdout
        
        # Fetch the logs
        logs_result = subprocess.run(
            ["docker", "compose", "logs", "--no-log-prefix"],
            cwd=str(STAGING_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        
        stdout_str = logs_result.stdout[-4000:] if logs_result.stdout and len(logs_result.stdout) > 4000 else logs_result.stdout
        stderr_str = logs_result.stderr[-4000:] if logs_result.stderr and len(logs_result.stderr) > 4000 else logs_result.stderr

        if is_running:
            # It's a web server!
            output = "Return code: 0 (SUCCESS)\n\n"
            output += "SUCCESS: The container is running continuously. Web Server detected.\n\n"
        else:
            # It exited. Let's get the exit code.
            exit_code_result = subprocess.run(
                ["docker", "compose", "ps", "-a", "--format", "{{.ExitCode}}"],
                cwd=str(STAGING_DIR),
                capture_output=True,
                text=True
            )
            exit_code_str = exit_code_result.stdout.strip()
            
            # If multiple containers, we take the first line
            if '\n' in exit_code_str:
                exit_code_str = exit_code_str.split('\n')[0]
                
            try:
                exit_code = int(exit_code_str) if exit_code_str else 1
            except ValueError:
                exit_code = 1
                
            output = f"Return code: {exit_code}\n\n"
            if exit_code != 0:
                output += "CRITICAL ERROR: The Docker container exited with a non-zero status code! The code crashed or failed to run. YOU MUST REJECT THIS!\n\n"
            
        output += f"--- STDOUT/STDERR LOGS (truncated) ---\n{stdout_str}\n"
        if stderr_str:
            output += f"{stderr_str}\n"
            
        # Cleanup
        subprocess.run(["docker", "compose", "down"], cwd=str(STAGING_DIR), capture_output=True)
        
        return output
    except Exception as e:
        subprocess.run(["docker", "compose", "down"], cwd=str(STAGING_DIR), capture_output=True)
        return f"Docker execution error: {e}"
