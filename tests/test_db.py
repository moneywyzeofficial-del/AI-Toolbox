import os
import pytest
from backend.app.models import RepoModel
from backend.app.db import (
    init_db,
    save_repository,
    get_repository,
    list_repositories,
    toggle_favorite,
    update_repo_category,
    mark_as_cloned,
)

TEST_DB = "test_repos.db"

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_save_and_get_repository():
    repo = RepoModel(
        url="https://github.com/fastapi/fastapi",
        name="fastapi",
        owner="fastapi",
        description_simple="Uma biblioteca moderna e rápida para criar APIs em Python.",
        use_cases=["Criar servidores web", "Desenvolver APIs REST com validação automática"],
        category="Web",
        is_favorite=False,
        is_cloned=False,
    )
    repo_id = save_repository(repo, db_path=TEST_DB)
    assert repo_id > 0

    fetched = get_repository(repo_id, db_path=TEST_DB)
    assert fetched is not None
    assert fetched.name == "fastapi"
    assert fetched.category == "Web"
    assert len(fetched.use_cases) == 2
    assert fetched.is_favorite is False

def test_list_and_filter_repositories():
    repo1 = RepoModel(
        url="https://github.com/psf/requests",
        name="requests",
        owner="psf",
        description_simple="Biblioteca simples para pedidos HTTP em Python.",
        use_cases=["Consultar sites", "Fazer downloads"],
        category="Utilitários",
        is_favorite=True,
    )
    repo2 = RepoModel(
        url="https://github.com/pallets/flask",
        name="flask",
        owner="pallets",
        description_simple="Micro-framework web em Python.",
        use_cases=["Criar páginas web", "Construir APIs simples"],
        category="Web",
        is_favorite=False,
    )
    save_repository(repo1, db_path=TEST_DB)
    save_repository(repo2, db_path=TEST_DB)

    all_repos = list_repositories(db_path=TEST_DB)
    assert len(all_repos) == 2

    web_repos = list_repositories(category="Web", db_path=TEST_DB)
    assert len(web_repos) == 1
    assert web_repos[0].name == "flask"

    fav_repos = list_repositories(favorites_only=True, db_path=TEST_DB)
    assert len(fav_repos) == 1
    assert fav_repos[0].name == "requests"

def test_toggle_favorite():
    repo = RepoModel(
        url="https://github.com/tiago/demo",
        name="demo",
        owner="tiago",
        description_simple="Projeto de teste.",
        use_cases=["Testes"],
        category="Testes",
        is_favorite=False,
    )
    repo_id = save_repository(repo, db_path=TEST_DB)

    new_fav = toggle_favorite(repo_id, db_path=TEST_DB)
    assert new_fav is True
    assert get_repository(repo_id, db_path=TEST_DB).is_favorite is True

    new_fav_again = toggle_favorite(repo_id, db_path=TEST_DB)
    assert new_fav_again is False
    assert get_repository(repo_id, db_path=TEST_DB).is_favorite is False

def test_update_category_and_mark_cloned():
    repo = RepoModel(
        url="https://github.com/tiago/demo2",
        name="demo2",
        owner="tiago",
        description_simple="Projeto de teste 2.",
        use_cases=["Testes"],
        category="Geral",
        is_favorite=False,
    )
    repo_id = save_repository(repo, db_path=TEST_DB)

    success_cat = update_repo_category(repo_id, "Inteligência Artificial", db_path=TEST_DB)
    assert success_cat is True
    assert get_repository(repo_id, db_path=TEST_DB).category == "Inteligência Artificial"

    success_clone = mark_as_cloned(repo_id, "d:\\AI Projects\\Downloaded_Repos\\demo2", db_path=TEST_DB)
    assert success_clone is True
    fetched = get_repository(repo_id, db_path=TEST_DB)
    assert fetched.is_cloned is True
    assert fetched.local_path == "d:\\AI Projects\\Downloaded_Repos\\demo2"

def test_delete_repository():
    from backend.app.db import delete_repository
    repo = RepoModel(
        url="https://github.com/tiago/to-delete",
        name="to-delete",
        owner="tiago",
        description_simple="Para apagar.",
        use_cases=["Apagar"],
        category="Geral",
    )
    repo_id = save_repository(repo, db_path=TEST_DB)
    assert get_repository(repo_id, db_path=TEST_DB) is not None

    deleted = delete_repository(repo_id, db_path=TEST_DB)
    assert deleted is True
    assert get_repository(repo_id, db_path=TEST_DB) is None

