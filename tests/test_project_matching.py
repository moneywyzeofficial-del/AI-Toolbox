import pytest
from backend.app.models import ProjectModel
from backend.app.gemini_service import (
    generate_project_summary_from_code,
    match_repo_with_projects
)

@pytest.mark.asyncio
async def test_generate_project_summary_from_code_mocked(monkeypatch):
    mock_json = '{"summary": "Este projeto é um sistema em Python para automação de rega que lê sensores e aciona válvulas elétricas."}'

    async def mock_call(*args, **kwargs):
        return mock_json

    from backend.app import gemini_service
    monkeypatch.setattr(gemini_service, "_call_gemini_api", mock_call)

    summary = await generate_project_summary_from_code(
        project_name="RegaSmart",
        technologies=["Python"],
        code_snippets=[{"file": "main.py", "content": "import time\ndef regar(): pass"}],
        api_key="test-key"
    )

    assert "automação de rega" in summary

@pytest.mark.asyncio
async def test_match_repo_with_projects_mocked(monkeypatch):
    mock_json = """
    [
        {
            "project_id": 1,
            "project_name": "Jardim Inteligente",
            "relevance_explanation": "Fornece a biblioteca exata para comunicar com os sensores de solo e automatizar as leituras de humidade."
        }
    ]
    """

    async def mock_call(*args, **kwargs):
        return mock_json

    from backend.app import gemini_service
    monkeypatch.setattr(gemini_service, "_call_gemini_api", mock_call)

    projects = [
        ProjectModel(
            id=1,
            name="Jardim Inteligente",
            path="d:\\AI Projects\\Jardim",
            summary="Sistema para monitorizar rega e plantas.",
            technologies=["Python"]
        ),
        ProjectModel(
            id=2,
            name="Gestor Finanças",
            path="d:\\AI Projects\\Financas",
            summary="Controlo de despesas e faturas.",
            technologies=["JavaScript"]
        )
    ]

    matches = await match_repo_with_projects(
        repo_name="dht-sensor-python",
        repo_description="Biblioteca para ler sensores de humidade e temperatura.",
        repo_use_cases=["Ler sensores de humidade", "Automação agrícola"],
        projects=projects,
        api_key="test-key"
    )

    assert len(matches) == 1
    assert matches[0]["project_id"] == 1
    assert matches[0]["project_name"] == "Jardim Inteligente"
    assert "sensores de solo" in matches[0]["relevance_explanation"]

@pytest.mark.asyncio
async def test_match_repo_empty_projects():
    matches = await match_repo_with_projects(
        repo_name="cool-lib",
        repo_description="Some lib",
        repo_use_cases=[],
        projects=[],
        api_key="test-key"
    )
    assert matches == []
