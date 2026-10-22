import os
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db import init_db

TEST_API_DB = "test_my_projects_api.db"

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

def test_scan_folder_api(tmp_path):
    p = tmp_path / "AppTest"
    p.mkdir()
    (p / "README.md").write_text("# Test App\nApp for testing", encoding="utf-8")
    (p / "main.py").write_text("print('test')", encoding="utf-8")

    resp = client.post("/api/my-projects/scan", json={"path": str(p)})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "AppTest"
    assert "Python" in data["technologies"]
    assert "App for testing" in data["summary"]

def test_create_and_manage_my_projects(tmp_path):
    # 1. Create project
    proj_payload = {
        "name": "Gestor Jardim",
        "path": str(tmp_path / "GestorJardim"),
        "summary": "Gestão de rega e jardinagem.",
        "status": "em_desenvolvimento",
        "technologies": ["Python", "FastAPI"],
        "notes": "Iniciar fase 1"
    }
    create_resp = client.post("/api/my-projects", json=proj_payload)
    assert create_resp.status_code == 200
    proj_id = create_resp.json()["id"]

    # 2. List projects
    list_resp = client.get("/api/my-projects")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # 3. Get single project
    get_resp = client.get(f"/api/my-projects/{proj_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["project"]["name"] == "Gestor Jardim"

    # 4. Patch notes and status
    patch_resp = client.patch(
        f"/api/my-projects/{proj_id}",
        json={"status": "concluido", "notes": "Fase 1 completa"}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "concluido"
    assert patch_resp.json()["notes"] == "Fase 1 completa"

def test_browse_folder_api(monkeypatch):
    import backend.app.folder_browser as fb
    monkeypatch.setattr(fb, "open_folder_picker", lambda initial_dir=None: "D:\\AI Projects\\MeuProjeto")
    resp = client.post("/api/browse-folder")
    assert resp.status_code == 200
    assert resp.json()["path"] == "D:\\AI Projects\\MeuProjeto"

def test_link_and_unlink_repo_api(tmp_path):
    from backend.app.models import RepoModel
    from backend.app.db import save_repository, save_recommendation

    # Create dummy project folder & project
    proj_dir = tmp_path / "ProjA"
    proj_dir.mkdir()
    proj_resp = client.post("/api/my-projects", json={
        "name": "Proj A",
        "path": str(proj_dir),
        "summary": "Summary",
        "status": "em_desenvolvimento",
        "technologies": ["Python"]
    })
    proj_id = proj_resp.json()["id"]

    # Create dummy repo installed
    repo_dir = tmp_path / "InstalledRepo"
    repo_dir.mkdir()
    repo = RepoModel(
        url="https://github.com/test/repo",
        name="repo",
        owner="test",
        description_simple="Desc",
        use_cases=["AI"],
        category="LLM",
        is_cloned=True,
        local_path=str(repo_dir)
    )
    repo_id = save_repository(repo, db_path=TEST_API_DB)

    # Save recommendation
    save_recommendation(
        project_id=proj_id,
        repo_id=repo_id,
        reason="Ótimo para o projeto",
        db_path=TEST_API_DB
    )

    # Test link-repo
    link_resp = client.post(f"/api/my-projects/{proj_id}/link-repo", json={"repo_id": repo_id})
    assert link_resp.status_code == 200
    link_data = link_resp.json()
    assert link_data["success"] is True
    assert link_data["is_linked"] is True

    # Check project details has recommendation with is_linked
    proj_detail = client.get(f"/api/my-projects/{proj_id}").json()
    recs = proj_detail["recommendations"]
    assert len(recs) == 1
    assert recs[0]["is_linked"] == 1

    # Test unlink-repo
    unlink_resp = client.post(f"/api/my-projects/{proj_id}/unlink-repo", json={"repo_id": repo_id})
    assert unlink_resp.status_code == 200
    assert unlink_resp.json()["is_linked"] is False

    proj_detail_after = client.get(f"/api/my-projects/{proj_id}").json()
    assert proj_detail_after["recommendations"][0]["is_linked"] == 0


