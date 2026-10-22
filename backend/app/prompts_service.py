import os
import json
import csv
import io
import httpx
from typing import List, Dict, Any, Optional

PROMPTS_CSV_URL = "https://raw.githubusercontent.com/f/prompts.chat/main/prompts.csv"
CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "prompts_chat_cache.json")

# Starter fallback prompts if offline and no cache exists yet
STARTER_PROMPTS = [
    {
        "act": "Linux Terminal",
        "prompt": "I want you to act as a linux terminal. I will type commands and you will reply with what the terminal should show. I want you to only reply with the terminal output inside one unique code block, and nothing else. do not write explanations. do not type commands unless I instruct you to do so. When I need to tell you something in english, I will do so by putting text inside curly brackets {like this}. My first command is pwd",
        "category": "Desenvolvimento",
        "for_devs": True
    },
    {
        "act": "Python Interpreter",
        "prompt": "I want you to act like a Python interpreter. I will give you Python code, and you will execute it. Do not provide any explanations. Do not respond with anything other than the output of the code. The first code is: print('Hello World!')",
        "category": "Desenvolvimento",
        "for_devs": True
    },
    {
        "act": "JavaScript Console",
        "prompt": "I want you to act as a javascript console. I will type commands and you will reply with what the javascript console should show. I want you to only reply with the terminal output inside one unique code block, and nothing else. do not write explanations. my first command is console.log('Hello World');",
        "category": "Desenvolvimento",
        "for_devs": True
    },
    {
        "act": "Assistente de Jardinagem e Plantas",
        "prompt": "Quero que atues como um jardineiro profissional e botânico experiente. Dá conselhos práticos e diretos sobre rega, poda, solo, fertilização e combate a pragas em plantas de interior e jardins exteriores. Evita termos muito complicados e dá dicas fáceis de aplicar.",
        "category": "Jardinagem & Casa",
        "for_devs": False
    },
    {
        "act": "Especialista em Piscinas",
        "prompt": "Age como um técnico de manutenção e tratamento de piscinas. Explica passo a passo como regular o pH, níveis de cloro e alcalinidade, como decantar água turva e fazer lavagem e enxaguamento do filtro de areia.",
        "category": "Manutenção",
        "for_devs": False
    },
    {
        "act": "Tradutor para Português Europeu",
        "prompt": "Quero que atues como um tradutor especialista em Português de Portugal (pt-PT). Traduz qualquer texto que eu enviar mantendo o tom natural e coloquial de Portugal, evitando expressões ou grafia do português do Brasil.",
        "category": "Línguas & Escrita",
        "for_devs": False
    },
    {
        "act": "Revisor de Código Sénior",
        "prompt": "Quero que atues como um Engenheiro de Software Sénior. Vou fornecer código e deves analisar potenciais bugs, falhas de segurança, otimizações de performance e sugerir melhorias de arquitetura com exemplos de código claros.",
        "category": "Desenvolvimento",
        "for_devs": True
    }
]

def categorize_prompt(act: str, p_type: str, for_devs: bool) -> str:
    p_type_lower = (p_type or "").lower()
    if for_devs or p_type_lower == "structured":
        return "Programação & Código"
    if p_type_lower == "image":
        return "Geração de Imagens"
    
    a = act.lower()
    if any(k in a for k in ['writer', 'author', 'screenwriter', 'poet', 'storyteller', 'essay', 'novel', 'script', 'editor', 'plagiarism', 'blog', 'lyrics', 'rapper', 'comedian', 'journalist', 'story']):
        return "Escrita & Criatividade"
    if any(k in a for k in ['coach', 'interviewer', 'recruiter', 'business', 'startup', 'advertiser', 'marketer', 'sales', 'consultant', 'accountant', 'ceo', 'career', 'resume', 'linkedin', 'manager']):
        return "Carreira & Negócios"
    if any(k in a for k in ['teacher', 'tutor', 'math', 'philosopher', 'philosophy', 'historian', 'scientist', 'doctor', 'chemist', 'physicist', 'academic', 'astronomer', 'etymologist']):
        return "Educação & Ciência"
    if any(k in a for k in ['translator', 'english', 'pronunciation', 'language', 'spanish', 'french', 'japanese', 'chinese', 'german', 'portuguese']):
        return "Idiomas & Tradução"
    if any(k in a for k in ['guide', 'travel', 'chef', 'cook', 'diet', 'fitness', 'personal trainer', 'nutritionist', 'gardener', 'plant', 'interior', 'makeup', 'style', 'virtual assistant', 'friend']):
        return "Estilo de Vida & Saúde"
    if any(k in a for k in ['game', 'character', 'rpg', 'player', 'dungeon', 'simulator', 'movie', 'film', 'music', 'song', 'critic', 'commentator']):
        return "Jogos & Entretenimento"
    
    return "Geral & Assistentes"

async def load_prompts_chat_data(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Carrega a lista de prompts do prompts.chat.
    Usa cache local para ser instantâneo e offline-first.
    """
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)

    if not force_refresh and os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    # Enriquecer categorias se antigo
                    has_detailed_cats = any(p.get("category") == "Programação & Código" for p in data)
                    if has_detailed_cats:
                        return data
        except Exception:
            pass

    # Tenta descarregar do GitHub
    try:
        csv.field_size_limit(10000000)
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(PROMPTS_CSV_URL)
            if resp.status_code == 200:
                text = resp.text
                reader = csv.DictReader(io.StringIO(text))
                prompts = []
                for row in reader:
                    act = (row.get("act") or "").strip()
                    prompt_text = (row.get("prompt") or "").strip()
                    for_devs = (row.get("for_devs") or "").lower() in ["true", "1", "yes"]
                    prompt_type = (row.get("type") or "").strip()
                    
                    if act and prompt_text:
                        category = categorize_prompt(act, prompt_type, for_devs)
                        prompts.append({
                            "act": act,
                            "prompt": prompt_text,
                            "category": category,
                            "for_devs": for_devs,
                            "target_model": "ChatGPT"
                        })

                if prompts:
                    with open(CACHE_FILE, "w", encoding="utf-8") as f:
                        json.dump(prompts, f, ensure_ascii=False, indent=2)
                    return prompts
    except Exception as e:
        print(f"Aviso ao carregar prompts.chat online: {e}")

    # Se já existir cache mesmo desatualizada, usa
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Fallback seguro
    return STARTER_PROMPTS
