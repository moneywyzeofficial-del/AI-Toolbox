import os
import re
from typing import List, Dict, Optional, Any
from pathlib import Path

def parse_frontmatter(content: str) -> Dict[str, Any]:
    """
    Extrai metadados simples de frontmatter YAML entre marcadores ---.
    """
    metadata: Dict[str, Any] = {}
    content = content.strip()
    if not content.startswith("---"):
        return metadata

    parts = content.split("---", 2)
    if len(parts) < 3:
        return metadata

    fm_text = parts[1]

    name_match = re.search(r"^name:\s*(.+)$", fm_text, re.MULTILINE)
    if name_match:
        metadata["name"] = name_match.group(1).strip().strip("'\"")

    model_match = re.search(r"^(?:target_model|model|ai_model):\s*(.+)$", fm_text, re.MULTILINE)
    if model_match:
        metadata["target_model"] = model_match.group(1).strip().strip("'\"")

    desc_multi = re.search(r"^description:\s*(?:>[-+]?|\|[-+]?)\s*\n((?:\s{2,}.*\n?)+)", fm_text, re.MULTILINE)
    if desc_multi:
        lines = [line.strip() for line in desc_multi.group(1).splitlines() if line.strip()]
        metadata["description"] = " ".join(lines)
    else:
        desc_single = re.search(r"^description:\s*(.+)$", fm_text, re.MULTILINE)
        if desc_single:
            val = desc_single.group(1).strip().strip("'\"")
            if val not in (">-", ">", ">+", "|-", "|", "|+"):
                metadata["description"] = val

    return metadata

def detect_model_for_skill(content: str, fm: Dict[str, Any]) -> str:
    """
    Identifica o modelo de IA para o qual o skill está otimizado.
    """
    explicit = fm.get("target_model") or fm.get("model") or fm.get("ai_model")
    if explicit:
        low = explicit.lower()
        if "claude" in low or "anthropic" in low:
            return "Claude"
        if "gemini" in low or "google" in low:
            return "Google Gemini"
        if "chatgpt" in low or "gpt" in low or "openai" in low:
            return "ChatGPT"
        if "deepseek" in low:
            return "DeepSeek"
        if "mistral" in low:
            return "Mistral AI"
        if "grok" in low or "xai" in low:
            return "xAI Grok"
        return explicit

    c_low = content.lower()
    if "gemini" in c_low or "mcp_gemini" in c_low:
        return "Google Gemini"
    if "deepseek" in c_low:
        return "DeepSeek"
    if "chatgpt" in c_low or "openai" in c_low or "gpt-4" in c_low:
        return "ChatGPT"
    if "mistral" in c_low:
        return "Mistral AI"
    if "grok" in c_low:
        return "xAI Grok"

    # A grande maioria dos skills nativos de agentes (Antigravity/OpenCode) segue o padrão Claude
    return "Claude"

def _parse_skill_file(skill_file: str, program: str, source: str, plugin: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not os.path.isfile(skill_file):
        return None

    try:
        with open(skill_file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return None

    fm = parse_frontmatter(content)
    folder_name = os.path.basename(os.path.dirname(skill_file))
    
    # If folder is "skills", fallback to parent folder name or skill file
    if folder_name.lower() == "skills":
        parent = os.path.basename(os.path.dirname(os.path.dirname(skill_file)))
        folder_name = parent or "skill"

    name = fm.get("name") or folder_name
    description = fm.get("description") or ""

    if not description:
        # Tentar extrair do primeiro parágrafo após cabeçalho
        non_fm = content.split("---", 2)[2] if content.strip().startswith("---") and len(content.split("---", 2)) >= 3 else content
        lines = [l.strip() for l in non_fm.splitlines() if l.strip() and not l.strip().startswith("#")]
        if lines:
            description = lines[0][:250]

    target_model = detect_model_for_skill(content, fm)
    is_custom = (source == "Antigravity (Personalizado)" or "personalizado" in source.lower())

    import hashlib
    skill_id = hashlib.md5(skill_file.encode("utf-8")).hexdigest()[:12]

    return {
        "id": skill_id,
        "name": name,
        "description": description or "Sem descrição fornecida.",
        "program": program,
        "source": source,
        "plugin": plugin,
        "directory": os.path.dirname(skill_file),
        "file_path": skill_file,
        "target_model": target_model,
        "is_custom": is_custom
    }

def scan_all_skills(user_home: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Varre os diretórios padrão do OpenCode e Google Antigravity para recolher todos os skills.
    """
    home = user_home or os.path.expanduser("~")
    skills: List[Dict[str, Any]] = []
    seen_paths = set()

    def add_skill(sk: Optional[Dict[str, Any]]):
        if sk and sk["file_path"] not in seen_paths:
            seen_paths.add(sk["file_path"])
            skills.append(sk)

    # 1. OpenCode Skills: ~/.config/opencode/skills/*
    opencode_skills_dir = os.path.join(home, ".config", "opencode", "skills")
    if os.path.isdir(opencode_skills_dir):
        for entry in os.listdir(opencode_skills_dir):
            item_path = os.path.join(opencode_skills_dir, entry)
            if os.path.isdir(item_path):
                skill_md = os.path.join(item_path, "SKILL.md")
                if os.path.isfile(skill_md):
                    add_skill(_parse_skill_file(skill_md, program="OpenCode", source="OpenCode"))

    # 2. Google Antigravity Built-in Skills: ~/.gemini/antigravity/builtin/skills/*
    agy_builtin_dir = os.path.join(home, ".gemini", "antigravity", "builtin", "skills")
    if os.path.isdir(agy_builtin_dir):
        for entry in os.listdir(agy_builtin_dir):
            item_path = os.path.join(agy_builtin_dir, entry)
            if os.path.isdir(item_path):
                skill_md = os.path.join(item_path, "SKILL.md")
                if os.path.isfile(skill_md):
                    add_skill(_parse_skill_file(skill_md, program="Google Antigravity", source="Antigravity (Nativo)"))

    # 3. Google Antigravity Custom Skills: ~/.gemini/config/skills/*
    agy_custom_dir = os.path.join(home, ".gemini", "config", "skills")
    if os.path.isdir(agy_custom_dir):
        for entry in os.listdir(agy_custom_dir):
            item_path = os.path.join(agy_custom_dir, entry)
            if os.path.isdir(item_path):
                skill_md = os.path.join(item_path, "SKILL.md")
                if os.path.isfile(skill_md):
                    add_skill(_parse_skill_file(skill_md, program="Google Antigravity", source="Antigravity (Personalizado)"))

    # 4. Google Antigravity Plugins: ~/.gemini/config/plugins/*/skills/*
    agy_plugins_dir = os.path.join(home, ".gemini", "config", "plugins")
    if os.path.isdir(agy_plugins_dir):
        for plugin_name in os.listdir(agy_plugins_dir):
            plugin_path = os.path.join(agy_plugins_dir, plugin_name)
            if not os.path.isdir(plugin_path):
                continue
            skills_sub = os.path.join(plugin_path, "skills")
            if not os.path.isdir(skills_sub):
                continue

            # Case A: skills directly has SKILL.md
            direct_md = os.path.join(skills_sub, "SKILL.md")
            if os.path.isfile(direct_md):
                add_skill(_parse_skill_file(direct_md, program="Google Antigravity", source=f"Plugin: {plugin_name}", plugin=plugin_name))

            # Case B: skills/subfolder/SKILL.md
            for sub in os.listdir(skills_sub):
                sub_path = os.path.join(skills_sub, sub)
                if os.path.isdir(sub_path):
                    skill_md = os.path.join(sub_path, "SKILL.md")
                    if os.path.isfile(skill_md):
                        add_skill(_parse_skill_file(skill_md, program="Google Antigravity", source=f"Plugin: {plugin_name}", plugin=plugin_name))

    # Ordenar alfabeticamente por nome
    skills.sort(key=lambda s: s["name"].lower())
    return skills

def read_skill_content(file_path: str) -> str:
    """
    Lê o conteúdo completo do ficheiro SKILL.md com validações de segurança.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError("Ficheiro do skill não encontrado.")
    if not file_path.lower().endswith(".md"):
        raise ValueError("Apenas ficheiros Markdown (.md) podem ser lidos.")

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()
