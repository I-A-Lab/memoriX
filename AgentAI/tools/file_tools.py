import os
import shutil
from pathlib import Path

STAGING_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "staging"
WORKSPACE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "workspace"

def write_code_to_staging(filename: str, content: str, **kwargs) -> str:
    """Writes a code file to the staging folder (temporary working memory).
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
            
        file_path = STAGING_DIR / filename
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
        return f"Code successfully written to staging/{filename}"
    except Exception as e:
        return f"Error writing to staging: {e}"

def list_staging_files(**kwargs) -> str:
    """Lists all files present in the staging folder."""
    try:
        files = []
        for root, dirs, filenames in os.walk(STAGING_DIR):
            for f in filenames:
                files.append(os.path.relpath(os.path.join(root, f), STAGING_DIR))
        if not files:
            return "The staging folder is empty."
        return "Files in staging:\n" + "\n".join(files)
    except Exception as e:
        return f"Error listing staging folder: {e}"

def clear_workspace(**kwargs) -> str:
    """Deletes all files present in the workspace folder.
    To be used if the user has given their permission to clean the folder.
    """
    try:
        for item in os.listdir(WORKSPACE_DIR):
            item_path = WORKSPACE_DIR / item
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
        return "The workspace has been completely cleaned."
    except Exception as e:
        return f"Error cleaning workspace: {e}"

def clear_staging(**kwargs) -> str:
    """Deletes all files present in the staging folder to start fresh."""
    try:
        for item in os.listdir(STAGING_DIR):
            item_path = STAGING_DIR / item
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
        return "The staging area has been completely cleaned."
    except Exception as e:
        return f"Error cleaning staging: {e}"

def publish_to_workspace(useful_files: list = None, **kwargs) -> str:
    """Moves files from the staging folder to the workspace.
    If useful_files is provided, only these files (e.g., ['main.py', 'utils.py']) will be moved.
    If not provided, it automatically filters out test files and Docker files, keeping only the strict minimum.
    The staging folder is then cleaned. To be used by the Manager after final validation.
    
    Args:
        useful_files (list, optional): List of file or folder names to keep for the user.
    """
    try:
        from agents import estimate_and_progress
        estimate_and_progress(0, 'DONE', 100)
        moved_files = []
        for item in os.listdir(STAGING_DIR):
            s = STAGING_DIR / item
            d = WORKSPACE_DIR / item
            
            # Always ignore Docker technical files
            if item in ["Dockerfile", "docker-compose.yml"]:
                continue
                
            # Automatically filter if no useful_files specified
            if useful_files is None:
                if item.startswith("test_") or item.endswith("_test.py") or item.endswith(".sh"):
                    continue
            else:
                if item not in useful_files:
                    continue
                
            if os.path.exists(d):
                if os.path.isdir(d):
                    shutil.rmtree(d)
                else:
                    os.remove(d)
            shutil.move(str(s), str(WORKSPACE_DIR))
            moved_files.append(item)
            
        # Completely clean staging
        for item in os.listdir(STAGING_DIR):
            item_path = STAGING_DIR / item
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
                
        return f"Success: {len(moved_files)} truly useful files ({', '.join(moved_files)}) were published to the workspace. Staging cleaned."
    except Exception as e:
        return f"Error publishing to workspace: {e}"
