import subprocess
import os

frontend_dir = r"c:\LNCZ\proyecto-catastro-2026\frontend"

try:
    print("Adding files...")
    subprocess.run(["git", "add", "."], cwd=frontend_dir, check=True)
    
    print("Committing files...")
    subprocess.run(["git", "commit", "-m", "feat: asignar proyectos y fix autofill"], cwd=frontend_dir, check=False)
    
    print("Pushing files...")
    subprocess.run(["git", "push"], cwd=frontend_dir, check=True)
    print("Push successful!")
except subprocess.CalledProcessError as e:
    print(f"Error during git commands: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
