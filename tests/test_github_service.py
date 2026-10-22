import pytest
from backend.app.github_service import parse_github_url, fetch_repo_data

def test_parse_github_url_valid():
    owner, repo = parse_github_url("https://github.com/fastapi/fastapi")
    assert owner == "fastapi"
    assert repo == "fastapi"

    owner2, repo2 = parse_github_url("https://github.com/psf/requests/")
    assert owner2 == "psf"
    assert repo2 == "requests"

    owner3, repo3 = parse_github_url("http://github.com/tiago/my-repo.git")
    assert owner3 == "tiago"
    assert repo3 == "my-repo"

def test_parse_github_url_invalid():
    with pytest.raises(ValueError):
        parse_github_url("https://gitlab.com/user/project")

    with pytest.raises(ValueError):
        parse_github_url("https://github.com/justowner")

    with pytest.raises(ValueError):
        parse_github_url("invalid-string")

@pytest.mark.asyncio
async def test_fetch_repo_data_success(monkeypatch):
    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json = json_data

        def json(self):
            return self._json

        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")

    async def mock_get(client, url, *args, **kwargs):
        if "readme" in url:
            import base64
            encoded = base64.b64encode(b"# FastAPI Framework\nFastAPI is a modern web framework.").decode()
            return MockResponse(200, {"content": encoded, "encoding": "base64"})
        else:
            return MockResponse(200, {
                "name": "fastapi",
                "full_name": "fastapi/fastapi",
                "description": "FastAPI framework, high performance",
                "stargazers_count": 80000,
                "topics": ["python", "web", "api"],
            })

    import httpx
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    data = await fetch_repo_data("fastapi", "fastapi")
    assert data["name"] == "fastapi"
    assert data["description"] == "FastAPI framework, high performance"
    assert "FastAPI is a modern web framework" in data["readme_content"]
    assert "python" in data["topics"]
