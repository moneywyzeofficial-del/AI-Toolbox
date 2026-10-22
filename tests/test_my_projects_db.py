import os
import pytest
from backend.app.models import ProjectModel
from backend.app.db import (
    init_db,
    save_project,
    get_project,
    list_projects,
    update_project,
    save_recommendation,
    get_project_recommendations,
    save_repository,
    RepoModel,
)

TEST_DB = "test_my_projects.db"

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_save_and_get_project():
    proj = ProjectModel(
        name="Jardim Inteligente",
        path="d:\\AI Projects\\Jardim",
        summary="Sistema para monitorizar rega e estado das plantas.",
        status="em_desenvolvimento",
        technologies=["Python", "FastAPI", "SQLite"],
        notes="Falta configurar sensores de humidade.",
    )
    proj_id = save_project(proj, db_path=TEST_DB)
    assert proj_id > 0

    fetched = get_project(proj_id, db_path=TEST_DB)
    assert fetched is not None
    assert fetched.name == "Jardim Inteligente"
    assert fetched.path == "d:\\AI Projects\\Jardim"
    assert "Python" in fetched.technologies
    assert fetched.status == "em_desenvolvimento"
    assert fetched.notes == "Falta configurar sensores de humidade."

def test_list_and_update_project():
    proj1 = ProjectModel(
        name="App Piscina",
        path="d:\\AI Projects\\Piscina",
        summary="Gestão de cloro e pH.",
        status="concluido",
        technologies=["HTML", "JavaScript"],
    )
    proj2 = ProjectModel(
        name="Robo Podador",
        path="d:\\AI Projects\\Robo",
        summary="Automação de corte.",
        status="em_desenvolvimento",
        technologies=["Python"],
    )
    save_project(proj1, db_path=TEST_DB)
    proj2_id = save_project(proj2, db_path=TEST_DB)

    all_proj = list_projects(db_path=TEST_DB)
    assert len(all_proj) == 2

    dev_proj = list_projects(status="em_desenvolvimento", db_path=TEST_DB)
    assert len(dev_proj) == 1
    assert dev_proj[0].name == "Robo Podador"

    # Update status and notes
    success = update_project(
        proj2_id,
        status="concluido",
        notes="Concluído com sucesso!",
        db_path=TEST_DB
    )
    assert success is True
    updated = get_project(proj2_id, db_path=TEST_DB)
    assert updated.status == "concluido"
    assert updated.notes == "Concluído com sucesso!"

def test_project_recommendations():
    # Create repo
    repo = RepoModel(
        url="https://github.com/sensors/dht",
        name="dht-sensor",
        owner="sensors",
        description_simple="Biblioteca para leitura de sensores de humidade e temperatura.",
        use_cases=["Ler humidade"],
        category="Hardware",
    )
    repo_id = save_repository(repo, db_path=TEST_DB)

    # Create project
    proj = ProjectModel(
        name="Estufa Automática",
        path="d:\\AI Projects\\Estufa",
        summary="Controlo de estufa.",
        status="em_desenvolvimento",
        technologies=["Python"],
    )
    proj_id = save_project(proj, db_path=TEST_DB)

    # Save recommendation
    rec_id = save_recommendation(
        project_id=proj_id,
        repo_id=repo_id,
        reason="Permite ler a humidade do solo diretamente com sensores DHT22.",
        db_path=TEST_DB
    )
    assert rec_id > 0

    recs = get_project_recommendations(proj_id, db_path=TEST_DB)
    assert len(recs) == 1
    assert recs[0]["repo_name"] == "dht-sensor"
    assert "sensores DHT22" in recs[0]["reason"]
