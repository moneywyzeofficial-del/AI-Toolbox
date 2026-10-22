import os
import pytest
from backend.app.skills_scanner import parse_frontmatter, _parse_skill_file, scan_all_skills, read_skill_content

def test_parse_frontmatter():
    text = """---
name: my-skill
description: |
  Primeira linha de descricao.
  Segunda linha de descricao.
---
# Conteudo"""
    fm = parse_frontmatter(text)
    assert fm["name"] == "my-skill"
    assert "Primeira linha" in fm["description"]
    assert "Segunda linha" in fm["description"]

def test_parse_frontmatter_folded_scalar():
    text = """---
name: folded-skill
description: >-
  Linha A.
  Linha B.
---
# Body"""
    fm = parse_frontmatter(text)
    assert fm["name"] == "folded-skill"
    assert "Linha A" in fm["description"]

def test_scan_all_skills_mock_tree(tmp_path):
    # Setup mock home
    # 1. OpenCode skill
    opencode_dir = tmp_path / ".config" / "opencode" / "skills" / "skill-opencode"
    opencode_dir.mkdir(parents=True)
    (opencode_dir / "SKILL.md").write_text("""---
name: skill-opencode
description: Skill de teste OpenCode.
---
# OpenCode""", encoding="utf-8")

    # 2. Antigravity Builtin
    builtin_dir = tmp_path / ".gemini" / "antigravity" / "builtin" / "skills" / "skill-builtin"
    builtin_dir.mkdir(parents=True)
    (builtin_dir / "SKILL.md").write_text("""---
name: skill-builtin
description: Skill builtin Antigravity.
---
# Builtin""", encoding="utf-8")

    # 3. Antigravity Plugin
    plugin_dir = tmp_path / ".gemini" / "config" / "plugins" / "my-plugin" / "skills" / "skill-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "SKILL.md").write_text("""---
name: skill-plugin
description: Skill de plugin Antigravity.
---
# Plugin""", encoding="utf-8")

    skills = scan_all_skills(user_home=str(tmp_path))
    assert len(skills) == 3

    programs = {s["program"] for s in skills}
    assert "OpenCode" in programs
    assert "Google Antigravity" in programs

    plugin_skill = next(s for s in skills if s["name"] == "skill-plugin")
    assert plugin_skill["plugin"] == "my-plugin"
    assert "Plugin: my-plugin" in plugin_skill["source"]

def test_read_skill_content(tmp_path):
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("# Teste de Leitura", encoding="utf-8")

    content = read_skill_content(str(skill_file))
    assert content == "# Teste de Leitura"

    with pytest.raises(FileNotFoundError):
        read_skill_content(str(tmp_path / "nao-existe.md"))

    invalid_file = tmp_path / "script.py"
    invalid_file.write_text("print(1)", encoding="utf-8")
    with pytest.raises(ValueError):
        read_skill_content(str(invalid_file))
