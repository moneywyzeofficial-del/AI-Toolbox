import pytest
from backend.app.gemini_service import analyze_repo_content, AnalysisResult

@pytest.mark.asyncio
async def test_analyze_repo_content_mocked(monkeypatch):
    mock_json = """
    {
        "description_simple": "O FastAPI é uma ferramenta moderna em Python que permite criar sites e serviços na web de forma muito rápida e sem complicações.",
        "use_cases": [
            "Criar uma API para ligar uma aplicação móvel a uma base de dados.",
            "Construir um serviço web que responde rapidamente a pedidos de utilizadores."
        ],
        "category": "Web"
    }
    """

    async def mock_call_gemini(*args, **kwargs):
        return mock_json

    from backend.app import gemini_service
    monkeypatch.setattr(gemini_service, "_call_gemini_api", mock_call_gemini)

    result = await analyze_repo_content(
        repo_name="fastapi",
        repo_description="FastAPI framework, high performance",
        topics=["python", "web"],
        readme_text="# FastAPI\nA fast web framework.",
        api_key="fake-test-key"
    )

    assert isinstance(result, AnalysisResult)
    assert "FastAPI é uma ferramenta" in result.description_simple
    assert len(result.use_cases) == 2
    assert result.category == "Web"
