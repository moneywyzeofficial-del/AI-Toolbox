import pytest
import os
from backend.app.models import PromptModel
from backend.app.db import (
    init_db,
    save_prompt,
    get_prompt,
    list_prompts,
    update_prompt,
    delete_prompt
)

TEST_DB = "test_prompts.db"

@pytest.fixture(autouse=True)
def cleanup():
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except Exception:
            pass
    init_db(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except Exception:
            pass

def test_save_and_get_prompt():
    p = PromptModel(
        act="Assistente de Jardinagem",
        prompt="Age como um jardineiro experiente e explica como podar árvores de fruto.",
        category="Jardinagem",
        source="personalizado"
    )
    prompt_id = save_prompt(p, db_path=TEST_DB)
    assert prompt_id > 0

    fetched = get_prompt(prompt_id, db_path=TEST_DB)
    assert fetched is not None
    assert fetched.act == "Assistente de Jardinagem"
    assert "podar árvores" in fetched.prompt
    assert fetched.category == "Jardinagem"
    assert fetched.source == "personalizado"

def test_list_and_search_prompts():
    save_prompt(PromptModel(act="Linux Terminal", prompt="Act as a Linux terminal", category="Dev"), db_path=TEST_DB)
    save_prompt(PromptModel(act="Python Interpreter", prompt="Act as a Python interactive console", category="Dev"), db_path=TEST_DB)
    save_prompt(PromptModel(act="Poeta", prompt="Escreve poemas rimados", category="Criatividade"), db_path=TEST_DB)

    all_prompts = list_prompts(db_path=TEST_DB)
    assert len(all_prompts) == 3

    dev_prompts = list_prompts(category="Dev", db_path=TEST_DB)
    assert len(dev_prompts) == 2

    search_prompts = list_prompts(search="terminal", db_path=TEST_DB)
    assert len(search_prompts) == 1
    assert search_prompts[0].act == "Linux Terminal"

def test_update_and_delete_prompt():
    pid = save_prompt(PromptModel(act="Original", prompt="Texto original"), db_path=TEST_DB)
    
    updated = update_prompt(pid, act="Editado", prompt="Novo texto", category="Atualizado", db_path=TEST_DB)
    assert updated is True

    fetched = get_prompt(pid, db_path=TEST_DB)
    assert fetched.act == "Editado"
    assert fetched.prompt == "Novo texto"
    assert fetched.category == "Atualizado"

    deleted = delete_prompt(pid, db_path=TEST_DB)
    assert deleted is True
    assert get_prompt(pid, db_path=TEST_DB) is None
