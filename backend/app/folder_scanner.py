import os
import re
from typing import Dict, Any, List, Optional

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".idea", ".vscode", "dist", "build"
}

TECH_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".html": "HTML",
    ".css": "CSS",
    ".dart": "Dart",
    ".rs": "Rust",
    ".go": "Go",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".php": "PHP",
    ".sql": "SQL",
}

TECH_FILES = {
    "package.json": "Node.js",
    "requirements.txt": "Python",
    "pyproject.toml": "Python",
    "Pipfile": "Python",
    "pubspec.yaml": "Flutter",
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
}

def extract_git_remote_url(git_dir: str) -> Optional[str]:
    config_path = os.path.join(git_dir, "config")
    if not os.path.isfile(config_path):
        return None
    try:
        with open(config_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        match = re.search(r'\[remote\s+"origin"\][^\[]*?url\s*=\s*([^\r\n]+)', content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return None

def scan_local_folder(folder_path: str) -> Dict[str, Any]:
    folder_path = os.path.abspath(folder_path.strip())
    if not os.path.isdir(folder_path):
        raise FileNotFoundError(f"A pasta '{folder_path}' não foi encontrada no computador.")

    folder_name = os.path.basename(folder_path) or "Projeto"
    readme_content = None
    technologies = set()
    code_snippets = []
    internal_repos = []

    # Check for README directly in root folder
    for fname in os.listdir(folder_path):
        if fname.lower() in ("readme.md", "readme.txt", "readme"):
            fpath = os.path.join(folder_path, fname)
            if os.path.isfile(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        readme_content = f.read(15000)
                except Exception:
                    pass
                break

    # Scan directory tree (max depth 3)
    root_depth = folder_path.rstrip(os.path.sep).count(os.path.sep)

    for root, dirs, files in os.walk(folder_path):
        current_depth = root.rstrip(os.path.sep).count(os.path.sep) - root_depth
        if current_depth > 3:
            dirs.clear()
            continue

        # Check for sub-repositories (.git) inside subfolders (not root)
        if root != folder_path and ".git" in dirs:
            git_path = os.path.join(root, ".git")
            remote_url = extract_git_remote_url(git_path)
            sub_name = os.path.basename(root)
            internal_repos.append({
                "name": sub_name,
                "path": root,
                "url": remote_url or f"local://{sub_name}"
            })
            # Do not traverse inside sub-repo further
            dirs.remove(".git")

        # Skip unwanted directories
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS and not d.startswith(".")]

        for f in files:
            # Detect technologies by special file names
            if f in TECH_FILES:
                technologies.add(TECH_FILES[f])

            # Detect technologies by extensions
            _, ext = os.path.splitext(f)
            if ext.lower() in TECH_EXTENSIONS:
                technologies.add(TECH_EXTENSIONS[ext.lower()])

            # Collect representative code snippets if no README
            if not readme_content and len(code_snippets) < 4:
                if ext.lower() in (".py", ".js", ".ts", ".dart", ".go", ".html"):
                    snippet_path = os.path.join(root, f)
                    try:
                        with open(snippet_path, "r", encoding="utf-8", errors="replace") as sf:
                            sample = sf.read(1500)
                            if sample.strip():
                                rel_path = os.path.relpath(snippet_path, folder_path)
                                code_snippets.append({"file": rel_path, "content": sample})
                    except Exception:
                        pass

    return {
        "name": folder_name,
        "path": folder_path,
        "readme_content": readme_content,
        "technologies": sorted(list(technologies)),
        "code_snippets": code_snippets,
        "internal_repos": internal_repos
    }
