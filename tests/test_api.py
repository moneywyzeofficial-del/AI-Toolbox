import os
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db import init_db

TEST_API_DB = "test_api.db"

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    if os.path.exists(TEST_API_DB):
        os.remove(TEST_API_DB)
    monkeypatch.setenv("REPOS_DB_PATH", TEST_API_DB)
    init_db(TEST_API_DB)
    yield
    if os.path.exists(TEST_API_DB):
        os.remove(TEST_API_DB)

client = TestClient(app)

def test_analyze_endpoint_mocked(monkeypatch):
    async def mock_fetch(owner, repo, token=None):
        return {
            "name": "fastapi",
            "full_name": "fastapi/fastapi",
            "owner": "fastapi",
            "description": "FastAPI framework",
            "stars": 80000,
            "topics": ["python", "web"],
            "readme_content": "# FastAPI",
        }

    from backend.app.gemini_service import AnalysisResult
    async def mock_analyze(repo_name, repo_description, topics, readme_text, api_key=None):
        return AnalysisResult(
            description_simple="Uma biblioteca para criar APIs rapidamente.",
            use_cases=["Criar um serviço web", "Conectar apps móveis"],
            category="Web"
        )

    from backend.app import main
    monkeypatch.setattr(main, "fetch_repo_data", mock_fetch)
    monkeypatch.setattr(main, "analyze_repo_content", mock_analyze)

    resp = client.post("/api/analyze", json={"url": "https://github.com/fastapi/fastapi"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "fastapi"
    assert data["category"] == "Web"
    assert len(data["use_cases"]) == 2

    # Query repos list
    list_resp = client.get("/api/repos")
    assert list_resp.status_code == 200
    repos = list_resp.json()
    assert len(repos) == 1
    repo_id = repos[0]["id"]

    # Toggle favorite
    fav_resp = client.post(f"/api/repos/{repo_id}/favorite")
    assert fav_resp.status_code == 200
    assert fav_resp.json()["is_favorite"] is True

    # Update category
    cat_resp = client.patch(f"/api/repos/{repo_id}/category", json={"category": "Backend"})
    assert cat_resp.status_code == 200
    assert cat_resp.json()["category"] == "Backend"

    # Clone endpoint test
    def mock_clone(url, target_dir):
        return True, "d:\\AI Projects\\Downloaded_Repos\\fastapi_fastapi", "Clonado com sucesso"

    monkeypatch.setattr(main, "clone_repository", mock_clone)
    clone_resp = client.post(f"/api/repos/{repo_id}/clone")
    assert clone_resp.status_code == 200
    assert clone_resp.json()["success"] is True

def test_analyze_invalid_url():
    resp = client.post("/api/analyze", json={"url": "not-a-valid-url"})
    assert resp.status_code == 400
    assert "URL inválido" in resp.json()["detail"]

def test_network_info_endpoint():
    resp = client.get("/api/network-info")
    assert resp.status_code == 200
    data = resp.json()
    assert "local_ip" in data
    assert "port" in data
    assert "url" in data
    assert "http://" in data["url"]

def test_delete_repo_endpoint():
    from backend.app.models import RepoModel
    from backend.app.db import save_repository
    repo = RepoModel(
        url="https://github.com/tiago/delete-me",
        name="delete-me",
        owner="tiago",
        description_simple="Para teste de delecao",
        use_cases=["Teste"],
        category="Testes",
    )
    repo_id = save_repository(repo, db_path=TEST_API_DB)
    del_resp = client.delete(f"/api/repos/{repo_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    del_again = client.delete(f"/api/repos/{repo_id}")
    assert del_again.status_code == 404

def test_repo_git_status_and_pull(monkeypatch, tmp_path):
    from backend.app.models import RepoModel
    from backend.app.db import save_repository
    repo_dir = tmp_path / "my_repo"
    repo_dir.mkdir()

    repo = RepoModel(
        url="https://github.com/tiago/local-repo",
        name="local-repo",
        owner="tiago",
        description_simple="Repo no disco",
        use_cases=["Teste"],
        category="Testes",
        is_cloned=True,
        local_path=str(repo_dir)
    )
    repo_id = save_repository(repo, db_path=TEST_API_DB)

    from backend.app import main
    monkeypatch.setattr(main, "check_git_updates", lambda p: (True, "1 commit atrás", 1))
    monkeypatch.setattr(main, "pull_repository", lambda p: (True, "Atualizado com sucesso"))

    # Git status
    status_resp = client.post(f"/api/repos/{repo_id}/git-status")
    assert status_resp.status_code == 200
    assert status_resp.json()["has_updates"] is True
    assert status_resp.json()["behind_count"] == 1

    # Git pull
    pull_resp = client.post(f"/api/repos/{repo_id}/git-pull")
    assert pull_resp.status_code == 200
    assert pull_resp.json()["success"] is True

def test_reanalyze_repo_endpoint(monkeypatch):
    from backend.app.models import RepoModel
    from backend.app.db import save_repository
    repo = RepoModel(
        url="https://github.com/karpathy/reanalyze-test",
        name="reanalyze-test",
        owner="karpathy",
        description_simple="Descricao antiga",
        use_cases=["Teste antigo"],
        category="Geral",
    )
    repo_id = save_repository(repo, db_path=TEST_API_DB)

    async def mock_fetch(owner, repo, token=None):
        return {
            "name": repo,
            "full_name": f"{owner}/{repo}",
            "owner": owner,
            "description": "Nova descricao",
            "stars": 200,
            "topics": ["ai"],
            "readme": "# Novo Readme",
        }

    async def mock_analyze(name, description, readme_content, api_key=None):
        return {
            "description_simple": "Nova explicacao super detalhada",
            "use_cases": ["Caso 1", "Caso 2"],
            "category": "Inteligência Artificial"
        }

    from backend.app import main
    monkeypatch.setattr(main, "fetch_repo_data", mock_fetch)
    monkeypatch.setattr(main, "analyze_repo_content", mock_analyze)

    resp = client.post(f"/api/repos/{repo_id}/reanalyze")
    assert resp.status_code == 200
    data = resp.json()
    assert data["description_simple"] == "Nova explicacao super detalhada"
    assert data["category"] == "Inteligência Artificial"
    assert len(data["use_cases"]) == 2


