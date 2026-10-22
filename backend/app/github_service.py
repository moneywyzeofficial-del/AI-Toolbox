import re
import base64
import httpx
from typing import Tuple, Dict, Any, Optional

GITHUB_URL_PATTERN = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$"
)

def parse_github_url(url: str) -> Tuple[str, str]:
    cleaned = url.strip()
    match = GITHUB_URL_PATTERN.match(cleaned)
    if not match:
        raise ValueError(
            "URL inválido do GitHub. Formato esperado: https://github.com/proprietario/repositorio"
        )
    owner = match.group(1)
    repo = match.group(2)
    return owner, repo

async def fetch_repo_data(
    owner: str,
    repo: str,
    token: Optional[str] = None
) -> Dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Repo-Organizer/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    base_api = f"https://api.github.com/repos/{owner}/{repo}"

    async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
        repo_resp = await client.get(base_api)
        if repo_resp.status_code == 404:
            raise ValueError(f"O repositório '{owner}/{repo}' não foi encontrado ou é privado no GitHub.")
        repo_resp.raise_for_status()
        repo_json = repo_resp.json()

        readme_text = ""
        try:
            readme_resp = await client.get(f"{base_api}/readme")
            if readme_resp.status_code == 200:
                readme_json = readme_resp.json()
                encoding = readme_json.get("encoding", "")
                content_b64 = readme_json.get("content", "")
                if encoding == "base64" and content_b64:
                    readme_bytes = base64.b64decode(content_b64)
                    readme_text = readme_bytes.decode("utf-8", errors="replace")
        except Exception:
            readme_text = ""

    return {
        "name": repo_json.get("name", repo),
        "full_name": repo_json.get("full_name", f"{owner}/{repo}"),
        "owner": owner,
        "description": repo_json.get("description") or "",
        "stars": repo_json.get("stargazers_count", 0),
        "topics": repo_json.get("topics", []),
        "readme_content": readme_text,
    }
