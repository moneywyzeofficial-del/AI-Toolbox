import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
import os
from backend.app.db import init_db

import sqlite3

TEST_API_DB = "test_prompts_api.db"

@pytest.fixture(autouse=True)
def setup_teardown():
    os.environ["REPOS_DB_PATH"] = TEST_API_DB
    init_db(TEST_API_DB)
    with sqlite3.connect(TEST_API_DB) as conn:
        conn.execute("DELETE FROM prompts")
        conn.commit()
    yield
    try:
        with sqlite3.connect(TEST_API_DB) as conn:
            conn.execute("DELETE FROM prompts")
            conn.commit()
    except Exception:
        pass
    os.environ.pop("REPOS_DB_PATH", None)

client = TestClient(app)

def test_prompts_crud_api():
    # 1. Create prompt
    payload = {
        "act": "Conselheiro de Piscinas",
        "prompt": "Explica como fazer o tratamento de choque com cloro numa piscina.",
        "category": "Piscinas",
        "source": "personalizado"
    }
    res = client.post("/api/prompts", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] is not None
    assert data["act"] == "Conselheiro de Piscinas"
    prompt_id = data["id"]

    # 2. List prompts
    list_res = client.get("/api/prompts")
    assert list_res.status_code == 200
    prompts = list_res.json()
    assert len(prompts) == 1

    # 3. Get single prompt
    single_res = client.get(f"/api/prompts/{prompt_id}")
    assert single_res.status_code == 200
    assert single_res.json()["act"] == "Conselheiro de Piscinas"

    # 4. Update prompt
    update_res = client.put(f"/api/prompts/{prompt_id}", json={
        "act": "Especialista em Piscinas",
        "prompt": "Novo texto atualizado",
        "category": "Manutenção"
    })
    assert update_res.status_code == 200
    assert update_res.json()["act"] == "Especialista em Piscinas"
    assert update_res.json()["category"] == "Manutenção"

    # 5. Delete prompt
    del_res = client.delete(f"/api/prompts/{prompt_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Verify deleted
    get_after_del = client.get(f"/api/prompts/{prompt_id}")
    assert get_after_del.status_code == 404

def test_community_prompts_api():
    res = client.get("/api/prompts/community")
    assert res.status_code == 200
    prompts = res.json()
    assert isinstance(prompts, list)
    assert len(prompts) > 0
    first = prompts[0]
    assert "act" in first
    assert "prompt" in first
    assert "target_model" in first
    assert first["target_model"] == "ChatGPT"

def test_prompts_target_model_and_conversion():
    # 1. Create with target_model
    payload = {
        "act": "Conselheiro de Jardinagem",
        "prompt": "Quero que ajas como um jardineiro profissional.",
        "category": "Jardinagem",
        "target_model": "ChatGPT (OpenAI)",
        "source": "personalizado"
    }
    create_res = client.post("/api/prompts", json=payload)
    assert create_res.status_code == 200
    p_data = create_res.json()
    assert p_data["target_model"] == "ChatGPT (OpenAI)"
    p_id = p_data["id"]

    # 2. Update target_model
    update_res = client.put(f"/api/prompts/{p_id}", json={
        "act": "Conselheiro de Jardinagem",
        "prompt": "Quero que ajas como um jardineiro profissional atualizado.",
        "category": "Jardinagem",
        "target_model": "Claude (Anthropic)"
    })
    assert update_res.status_code == 200
    assert update_res.json()["target_model"] == "Claude (Anthropic)"

    # 3. Test prompt conversion to Claude
    conv_claude = client.post("/api/prompts/convert", json={
        "act": "Conselheiro de Jardinagem",
        "prompt_text": "Age como um jardineiro profissional e dá dicas de poda.",
        "current_model": "ChatGPT (OpenAI)",
        "target_model": "Claude (Anthropic)"
    })
    assert conv_claude.status_code == 200
    data_claude = conv_claude.json()
    assert "converted_prompt" in data_claude
    assert "<system>" in data_claude["converted_prompt"] or "Claude" in data_claude["converted_prompt"]

    # 4. Test prompt conversion to DeepSeek
    conv_deepseek = client.post("/api/prompts/convert", json={
        "act": "Analista Python",
        "prompt_text": "Escreve um algoritmo de ordenação rápido.",
        "current_model": "ChatGPT (OpenAI)",
        "target_model": "DeepSeek"
    })
    assert conv_deepseek.status_code == 200
    data_deepseek = conv_deepseek.json()
    assert "converted_prompt" in data_deepseek
    assert len(data_deepseek["converted_prompt"]) > 20

    # 5. Test prompt conversion to Mistral AI (substitute for ChatGPT)
    conv_mistral = client.post("/api/prompts/convert", json={
        "act": "Especialista em Redes",
        "prompt_text": "Configura um servidor SMB seguro para rede local.",
        "current_model": "ChatGPT (OpenAI)",
        "target_model": "Mistral AI"
    })
    assert conv_mistral.status_code == 200
    data_mistral = conv_mistral.json()
    assert "converted_prompt" in data_mistral
    assert len(data_mistral["converted_prompt"]) > 20

    # 6. Clean up
    client.delete(f"/api/prompts/{p_id}")

def test_huggingface_trending_descriptions():
    from backend.app.trending_service import generate_hf_item_description
    
    # Model test
    desc_model = generate_hf_item_description(
        item_id="Qwen/Qwen2.5-Coder-7B-Instruct",
        name="Qwen2.5-Coder-7B-Instruct",
        author="Qwen",
        pipeline_tag="text-generation",
        item_type="model"
    )
    assert isinstance(desc_model, str)
    assert len(desc_model) > 20
    assert "programação" in desc_model.lower() or "código" in desc_model.lower() or "linguagem" in desc_model.lower()

    # Space test
    desc_space = generate_hf_item_description(
        item_id="hugging-apps/bfs-best-face-swap",
        name="bfs-best-face-swap",
        author="hugging-apps",
        pipeline_tag="image-to-image",
        item_type="space",
        sdk="gradio"
    )
    assert isinstance(desc_space, str)
    assert "interativa" in desc_space.lower() or "web" in desc_space.lower()
    assert "gradio" in desc_space.lower()


