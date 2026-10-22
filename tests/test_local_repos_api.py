import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db import init_db, save_repository
from backend.app.models import RepoModel

TEST_LOCAL_DB = "test_local_api.db"

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    if os.path.exists(TEST_LOCAL_DB):
        os.remove(TEST_LOCAL_DB)
    monkeypatch.setenv("REPOS_DB_PATH", TEST_LOCAL_DB)
    init_db(TEST_LOCAL_DB)
    yield
    if os.path.exists(TEST_LOCAL_DB):
        os.remove(TEST_LOCAL_DB)

client = TestClient(app)

def test_scan_local_repos_api(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        repo1_dir = os.path.join(tmpdir, "RepoUm")
        os.makedirs(os.path.join(repo1_dir, ".git"))

        repo2_dir = os.path.join(tmpdir, "RepoDois")
        os.makedirs(os.path.join(repo2_dir, ".git"))

        # Inserir RepoUm antecipadamente na BD
        repo_saved = RepoModel(
            url="https://github.com/teste/RepoUm",
            name="RepoUm",
            owner="teste",
            description_simple="Repo já guardado",
            use_cases=["Teste"],
            category="Geral",
            is_cloned=True,
            local_path=repo1_dir
        )
        save_repository(repo_saved, db_path=TEST_LOCAL_DB)

        def mock_remote(folder):
            if "RepoUm" in folder:
                return "https://github.com/teste/RepoUm"
            return ""

        monkeypatch.setattr("backend.app.local_scanner.get_git_remote_url", mock_remote)

        resp = client.post("/api/local-repos/scan", json={"folder": tmpdir})
        assert resp.status_code == 200
        data = resp.json()
        assert data["search_folder"] == tmpdir
        repos = data["repos"]
        assert len(repos) == 2

        item1 = next(r for r in repos if r["name"] == "RepoUm")
        assert item1["is_cataloged"] is True
        assert item1["catalog_id"] is not None

        item2 = next(r for r in repos if r["name"] == "RepoDois")
        assert item2["is_cataloged"] is False
        assert item2["catalog_id"] is None

def test_scan_local_repos_not_found():
    resp = client.post("/api/local-repos/scan", json={"folder": "C:\\inexistente_xyz_12345"})
    assert resp.status_code == 404

def test_import_local_repo_basic():
    with tempfile.TemporaryDirectory() as tmpdir:
        readme_path = os.path.join(tmpdir, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write("# Meu Projeto Local\nUm projeto fantastico em Python.")

        req_payload = {
            "name": "Meu Projeto Local",
            "path": tmpdir,
            "remote_url": "",
            "auto_analyze": False
        }

        resp = client.post("/api/local-repos/import", json=req_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Meu Projeto Local"
        assert data["is_cloned"] is True
        assert data["local_path"] == tmpdir
        assert "Meu Projeto Local" in data["description_simple"]

def test_import_local_repo_with_auto_analyze(monkeypatch):
    async def mock_fetch(owner, repo, token=None):
        return {
            "name": repo,
            "full_name": f"{owner}/{repo}",
            "owner": owner,
            "description": "Descricao do Github",
            "stars": 100,
            "topics": ["ai"],
            "readme": "# Karpathy Autoresearch\nTreino autonomo de IA.",
        }

    async def mock_analyze(name, description, readme_content, api_key=None):
        return {
            "description_simple": "Agente de IA que treina modelos em loop fechado.",
            "use_cases": ["Pesquisa autonoma de IA", "Otimizacao de hiperparametros"],
            "category": "Inteligência Artificial"
        }

    from backend.app import main
    monkeypatch.setattr(main, "fetch_repo_data", mock_fetch)
    monkeypatch.setattr(main, "analyze_repo_content", mock_analyze)

    with tempfile.TemporaryDirectory() as tmpdir:
        req_payload = {
            "name": "autoresearch",
            "path": tmpdir,
            "remote_url": "https://github.com/karpathy/autoresearch",
            "auto_analyze": True
        }

        resp = client.post("/api/local-repos/import", json=req_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "autoresearch"
        assert data["category"] == "Inteligência Artificial"
        assert len(data["use_cases"]) == 2
        assert data["is_cloned"] is True
        assert data["local_path"] == tmpdir

def test_import_batch_local_repos():
    with tempfile.TemporaryDirectory() as tmpdir:
        dir1 = os.path.join(tmpdir, "Batch1")
        dir2 = os.path.join(tmpdir, "Batch2")
        os.makedirs(dir1)
        os.makedirs(dir2)

        payload = {
            "repos": [
                {"name": "Batch1", "path": dir1, "remote_url": "", "auto_analyze": False},
                {"name": "Batch2", "path": dir2, "remote_url": "", "auto_analyze": False}
            ]
        }
        resp = client.post("/api/local-repos/import-batch", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["imported_count"] == 2
        assert len(data["imported"]) == 2

def test_open_folder_api(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        opened = []
        if os.name == 'nt':
            monkeypatch.setattr(os, "startfile", lambda p: opened.append(p))
        else:
            import subprocess
            monkeypatch.setattr(subprocess, "Popen", lambda cmd: opened.append(cmd))

        resp = client.post("/api/open-folder", json={"path": tmpdir})
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert len(opened) == 1

def test_open_folder_not_found():
    resp = client.post("/api/open-folder", json={"path": "C:\\inexistente_xyz_99999"})
    assert resp.status_code == 404

def test_open_in_editor_api(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        import subprocess
        executed = []
        monkeypatch.setattr(subprocess, "Popen", lambda cmd, **kwargs: executed.append(cmd))

        resp = client.post("/api/open-in-editor", json={"path": tmpdir})
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert len(executed) == 1
        assert "code" in executed[0]

def test_open_in_editor_not_found():
    resp = client.post("/api/open-in-editor", json={"path": "C:\\inexistente_xyz_88888"})
    assert resp.status_code == 404
