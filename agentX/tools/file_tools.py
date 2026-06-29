import os
import shutil
from pathlib import Path

WORKSPACE_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) / "agentX" / "workspace"

def write_code_to_workspace(filename: str, content: str, **kwargs) -> str:
    """Writes a code file to the workspace folder (temporary and final working memory).
    The Coder Agent uses this tool to create source and test files.
    
    Args:
        filename (str): The name of the file (e.g., 'main.py' or 'test_main.py').
        content (str): The source code.
    """
    try:
        import re
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```[a-zA-Z]*\n", "", content)
            content = re.sub(r"\n```$", "", content)
            
        # Clean up stubborn 3B model artifacts
        content = content.replace("\\n", "\n")
        content = re.sub(r"^---[\s\S]*?---\n+", "", content) # Strip frontmatter
        if filename.endswith(".css"):
            content = re.sub(r"^<style.*?>\n?", "", content, flags=re.IGNORECASE)
            content = re.sub(r"\n?</style>$", "", content, flags=re.IGNORECASE)
        elif filename.endswith(".js"):
            content = re.sub(r"^<script.*?>\n?", "", content, flags=re.IGNORECASE)
            content = re.sub(r"\n?</script>$", "", content, flags=re.IGNORECASE)
            
        file_path = WORKSPACE_DIR / filename
        # Ensure subdirectories exist if filename contains a path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Auto-import hack for 3B model
        if filename.endswith(".py"):
            missing_imports = ""
            if "random" in content or "choices" in content or "choice" in content:
                if "import random" not in content and "from random" not in content:
                    missing_imports += "import random\n"
            if "string" in content and "import string" not in content:
                missing_imports += "import string\n"
            if "secrets" in content and "import secrets" not in content:
                missing_imports += "import secrets\n"
            
            if missing_imports:
                content = missing_imports + "\n" + content

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Code successfully written to workspace/{filename}"
    except Exception as e:
        return f"Error writing to workspace: {e}"

def list_workspace_files(**kwargs) -> str:
    """Lists all files present in the workspace folder."""
    try:
        files = []
        for root, dirs, filenames in os.walk(WORKSPACE_DIR):
            for f in filenames:
                files.append(os.path.relpath(os.path.join(root, f), WORKSPACE_DIR))
        if not files:
            return "The workspace folder is empty."
        return "Files in workspace:\n" + "\n".join(files)
    except Exception as e:
        return f"Error listing workspace folder: {e}"

def read_file_from_workspace(filename: str, **kwargs) -> str:
    """Reads the contents of a file from the workspace folder.
    Use this to read a file before modifying it.
    
    Args:
        filename (str): The name of the file (e.g., 'main.py').
    """
    try:
        file_path = WORKSPACE_DIR / filename
        if not file_path.exists():
            return f"Error: File '{filename}' not found in workspace."
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file from workspace: {e}"

def clear_workspace(**kwargs) -> str:
    """Deletes all files present in the workspace folder."""
    try:
        if not os.path.exists(WORKSPACE_DIR):
            WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
            return "Workspace created."
            
        for item in os.listdir(WORKSPACE_DIR):
            item_path = WORKSPACE_DIR / item
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
        return "The workspace has been completely cleaned."
    except Exception as e:
        return f"Error cleaning workspace: {e}"

def cleanup_workspace_useless_files(useful_files: list = None, **kwargs) -> str:
    """Cleans up the workspace by removing test files, docker configurations, and unnecessary scripts.
    To be used by the Manager after final validation.
    
    Args:
        useful_files (list, optional): List of file or folder names to keep for the user.
    """
    try:
        from agentX.coder.coder import estimate_and_progress
        estimate_and_progress(0, 'DONE', 100)
        removed_files = []
        
        if not os.path.exists(WORKSPACE_DIR):
            return "Workspace not found."
            
        for item in os.listdir(WORKSPACE_DIR):
            item_path = WORKSPACE_DIR / item
            
            # Always remove Docker technical files
            if item in ["Dockerfile", "docker-compose.yml"]:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
                removed_files.append(item)
                continue
                
            # Automatically filter if no useful_files specified
            if useful_files is None:
                if item.startswith("test_") or item.endswith("_test.py") or item.endswith(".sh"):
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                    removed_files.append(item)
            else:
                if item not in useful_files:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                    removed_files.append(item)
                
        return f"Success: Cleaned up {len(removed_files)} useless files ({', '.join(removed_files)}). The workspace is ready."
    except Exception as e:
        return f"Error cleaning up workspace files: {e}"
