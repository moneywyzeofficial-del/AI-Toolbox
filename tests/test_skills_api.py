from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_api_get_skills_mocked(monkeypatch):
    import backend.app.skills_scanner as ss

    mock_skills = [
        {
            "id": "1",
            "name": "firecrawl-scrape",
            "description": "Extrair conteudo de uma pagina web.",
            "program": "OpenCode",
            "source": "OpenCode",
            "plugin": None,
            "directory": "C:/mock/firecrawl-scrape",
            "file_path": "C:/mock/firecrawl-scrape/SKILL.md"
        },
        {
            "id": "2",
            "name": "flutter-a11y",
            "description": "Testar acessibilidade em Flutter.",
            "program": "Google Antigravity",
            "source": "Plugin: flutter",
            "plugin": "flutter",
            "directory": "C:/mock/flutter-a11y",
            "file_path": "C:/mock/flutter-a11y/SKILL.md"
        }
    ]

    monkeypatch.setattr(ss, "scan_all_skills", lambda user_home=None: mock_skills)

    # 1. Sem filtros
    resp = client.get("/api/skills")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # 2. Filtro por programa
    resp_opencode = client.get("/api/skills?program=OpenCode")
    assert resp_opencode.status_code == 200
    data = resp_opencode.json()
    assert len(data) == 1
    assert data[0]["name"] == "firecrawl-scrape"

    # 3. Filtro por pesquisa
    resp_search = client.get("/api/skills?search=acessibilidade")
    assert resp_search.status_code == 200
    assert len(resp_search.json()) == 1
    assert resp_search.json()[0]["name"] == "flutter-a11y"

def test_api_get_skill_content(tmp_path):
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("# Instrucoes detalhadas do skill", encoding="utf-8")

    resp = client.get(f"/api/skills/content?path={str(skill_file)}")
    assert resp.status_code == 200
    data = resp.json()
    assert "Instrucoes detalhadas" in data["content"]
    assert data["file_path"] == str(skill_file)

    # 404 para caminho inexistente
    resp_404 = client.get(f"/api/skills/content?path={str(tmp_path / 'nao-existe.md')}")
    assert resp_404.status_code == 404

def test_detect_model_for_skill():
    from backend.app.skills_scanner import detect_model_for_skill

    # Explicit in frontmatter
    assert detect_model_for_skill("content", {"target_model": "ChatGPT"}) == "ChatGPT"
    assert detect_model_for_skill("content", {"model": "Gemini 1.5 Pro"}) == "Google Gemini"
    assert detect_model_for_skill("content", {"ai_model": "deepseek-r1"}) == "DeepSeek"

    # Content detection
    assert detect_model_for_skill("This uses mcp_gemini tool", {}) == "Google Gemini"
    assert detect_model_for_skill("Optimized for DeepSeek reasoning", {}) == "DeepSeek"
    assert detect_model_for_skill("Default skill instructions", {}) == "Claude"

def test_custom_skills_crud_and_convert(tmp_path, monkeypatch):
    import os
    from backend.app import db

    # Use a temp DB
    test_db = str(tmp_path / "test_skills.db")
    monkeypatch.setenv("REPOS_DB_PATH", test_db)
    db.init_db(test_db)

    # 1. Create a custom skill
    payload = {
        "name": "meu-skill-teste",
        "description": "Um skill de teste para automação",
        "target_model": "Claude",
        "content": "# Test Skill\nRole: Tester\nExecuta testes com rigor."
    }
    create_resp = client.post("/api/skills", json=payload)
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["name"] == "meu-skill-teste"
    assert created["target_model"] == "Claude"
    assert created["is_custom"] is True
    skill_id = created["id"]

    # 2. List my custom skills
    my_resp = client.get("/api/skills/my")
    assert my_resp.status_code == 200
    my_skills = my_resp.json()
    assert len(my_skills) >= 1
    assert any(s["id"] == skill_id for s in my_skills)

    # 3. Update the custom skill
    update_payload = {
        "name": "meu-skill-teste-atualizado",
        "description": "Descricao atualizada",
        "target_model": "Google Gemini",
        "content": "# Test Skill Atualizado\nRole: Tester Gemini."
    }
    update_resp = client.put(f"/api/skills/{skill_id}", json=update_payload)
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["name"] == "meu-skill-teste-atualizado"
    assert updated["target_model"] == "Google Gemini"

    # 4. Convert skill
    convert_payload = {
        "skill_content": "# Test Skill\nFaça X e Y",
        "skill_name": "meu-skill-teste",
        "current_model": "Google Gemini",
        "target_model": "ChatGPT"
    }
    convert_resp = client.post("/api/skills/convert", json=convert_payload)
    assert convert_resp.status_code == 200
    converted = convert_resp.json()
    assert converted["target_model"] == "ChatGPT"
    assert "converted_content" in converted
    assert len(converted["converted_content"]) > 10

    # 5. Delete the custom skill
    del_resp = client.delete(f"/api/skills/{skill_id}")
    assert del_resp.status_code == 200

    # Verify it is deleted from my skills
    my_resp_after = client.get("/api/skills/my")
    assert not any(s["id"] == skill_id for s in my_resp_after.json())

