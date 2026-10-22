import os
import subprocess
from typing import List, Dict, Any, Optional

def get_git_remote_url(folder: str) -> str:
    """
    Obtém o URL remoto 'origin' de um repositório Git local, se existir.
    Converte URLs SSH para HTTPS e remove a extensão .git.
    """
    try:
        out = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=folder,
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()
        if out.startswith("git@github.com:"):
            out = "https://github.com/" + out[len("git@github.com:"):]
        if out.endswith(".git"):
            out = out[:-4]
        return out
    except Exception:
        return ""

def scan_installed_repositories(base_dir: str, max_depth: int = 2) -> List[Dict[str, Any]]:
    """
    Varre a pasta base no disco à procura de repositórios Git instalados.
    Evita pastas de dependências (node_modules, venv, cache).
    """
    if not os.path.isdir(base_dir):
        return []

    found: List[Dict[str, Any]] = []
    ignored_dirs = {
        ".git", "node_modules", "venv", ".venv", "__pycache__", 
        ".pytest_cache", "build", "dist", ".idea", ".vscode"
    }

    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]

        if ".git" in os.listdir(root):
            rel = os.path.relpath(root, base_dir)
            depth = 0 if rel == "." else rel.count(os.sep) + 1
            if depth <= max_depth:
                has_readme = False
                readme_name = None
                for f in files:
                    if f.lower().startswith("readme"):
                        has_readme = True
                        readme_name = f
                        break

                remote_url = get_git_remote_url(root)
                found.append({
                    "name": os.path.basename(root),
                    "path": os.path.abspath(root),
                    "remote_url": remote_url,
                    "has_readme": has_readme,
                    "readme_name": readme_name
                })
                # Não procurar sub-repositórios dentro deste repositório
                dirs.clear()

    found.sort(key=lambda r: r["name"].lower())
    return found
