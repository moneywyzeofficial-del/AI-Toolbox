import os
import subprocess
from typing import Tuple
from backend.app.github_service import parse_github_url

DEFAULT_DOWNLOAD_DIR = r"d:\AI Projects\Downloaded_Repos"

def get_default_download_dir() -> str:
    return os.environ.get("DOWNLOADED_REPOS_DIR", DEFAULT_DOWNLOAD_DIR)

def clone_repository(
    repo_url: str,
    target_dir: str = DEFAULT_DOWNLOAD_DIR
) -> Tuple[bool, str, str]:
    try:
        owner, repo_name = parse_github_url(repo_url)
    except Exception as e:
        return False, "", f"URL do repositório inválido: {str(e)}"

    os.makedirs(target_dir, exist_ok=True)
    destination_path = os.path.join(target_dir, f"{owner}_{repo_name}")

    if os.path.exists(destination_path):
        return True, destination_path, f"O repositório já existe na pasta local: {destination_path}"

    try:
        cmd = ["git", "clone", repo_url, destination_path]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=120
        )
        if result.returncode == 0:
            return True, destination_path, f"Clonado com sucesso para: {destination_path}"
        else:
            err = result.stderr.strip() or result.stdout.strip()
            return False, "", f"Erro ao clonar o repositório: {err}"
    except Exception as e:
        return False, "", f"Falha na execução do Git: {str(e)}"

def check_git_updates(repo_path: str) -> Tuple[bool, str, int]:
    """
    Verifica se o repositório local tem commits novos no repositório remoto.
    Retorna (has_updates, message, behind_count).
    """
    if not os.path.exists(repo_path) or not os.path.exists(os.path.join(repo_path, ".git")):
        return False, "A pasta não é um repositório Git válido.", 0

    try:
        fetch_res = subprocess.run(
            ["git", "fetch"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=15
        )
        if fetch_res.returncode != 0:
            err = fetch_res.stderr.strip() or fetch_res.stdout.strip()
            return False, f"Não foi possível contactar o servidor remoto: {err}", 0

        rev_res = subprocess.run(
            ["git", "rev-list", "HEAD..@{u}", "--count"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=10
        )
        if rev_res.returncode == 0:
            count = int(rev_res.stdout.strip() or "0")
            if count > 0:
                return True, f"Existem {count} atualizações disponíveis no GitHub.", count
            else:
                return False, "O repositório já está atualizado com a versão mais recente.", 0
        else:
            status_res = subprocess.run(
                ["git", "status", "-uno"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
                timeout=10
            )
            out = status_res.stdout
            if "behind" in out:
                return True, "Existem atualizações disponíveis no GitHub.", 1
            return False, "O repositório local está sincronizado.", 0
    except subprocess.TimeoutExpired:
        return False, "Tempo limite excedido ao contactar o servidor remoto.", 0
    except Exception as e:
        return False, f"Erro ao verificar atualizações: {str(e)}", 0

def pull_repository(repo_path: str) -> Tuple[bool, str]:
    """
    Executa git pull para atualizar o repositório local.
    """
    if not os.path.exists(repo_path) or not os.path.exists(os.path.join(repo_path, ".git")):
        return False, "A pasta não é um repositório Git válido."

    try:
        result = subprocess.run(
            ["git", "pull"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=60
        )
        msg = result.stdout.strip() or result.stderr.strip()
        if result.returncode == 0:
            if "Already up to date" in msg or "Já atualizado" in msg:
                return True, "Repositório já se encontra totalmente atualizado."
            return True, f"Atualizado com sucesso: {msg}"
        else:
            return False, f"Erro ao atualizar repositório: {msg}"
    except Exception as e:
        return False, f"Falha na execução do Git pull: {str(e)}"
