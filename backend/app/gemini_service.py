import os
import json
import re
import httpx
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from backend.app.models import ProjectModel

class AnalysisResult(BaseModel):
    description_simple: str
    use_cases: List[str] = Field(default_factory=list)
    category: str = "Geral"

SYSTEM_PROMPT = """És um especialista sénior em software e inteligência artificial que explica repositórios de código de forma detalhada, clara e prática em Português Europeu (de Portugal).
O utilizador quer uma análise aprofundada, estruturada e de fácil compreensão sobre cada repositório do GitHub.

Deves produzir a "description_simple" OBRIGATORIAMENTE estruturada com as seguintes secções:

[Parágrafo de Introdução]: Explica quem desenvolveu o projeto (se conhecido), o contexto geral, o conceito central e o grande objetivo da ferramenta em português claro.

Como funciona:
- [Nome do passo/ciclo]: Descrição clara do fluxo operacional ou loop de trabalho (ex: tempos de ciclo, dados recebidos, modelo base).
- [Nome do passo/ciclo]: Lógica de decisão (o que mede, como avalia melhorias, o que mantém se melhorar ou descarta se falhar).

Os ficheiros centrais (ou Arquitetura):
- [nome_do_ficheiro]: Papel detalhado e indicação se é fixo ou editado pelo humano/código.
- [nome_do_ficheiro]: Papel detalhado no projeto.
(Se o repositório não destacar ficheiros específicos no README, descreve os 2 ou 3 componentes principais).

Requisitos:
- Hardware: Especificações necessárias (GPU, memória RAM, etc., se aplicável).
- Software e ambiente: Versões (ex: Python 3.10+), gestores de pacotes (uv, pip, npm) e chaves de API necessárias.

Importante: Não escrevas os rótulos literais entre parêntesis retos como "[Nome do passo]" ou "[nome_do_ficheiro]". Substitui-os sempre diretamente pelos nomes e títulos reais dos passos e ficheiros.

ESTRUTURA DO JSON:
{
  "description_simple": "Texto completo estruturado com as secções acima (usando quebras de linha '\\n' e marcadores de lista '-')",
  "use_cases": [
    "Exemplo prático 1 de como ou onde alguém usaria isto no mundo real.",
    "Exemplo prático 2 de como ou onde alguém usaria isto no mundo real.",
    "Exemplo prático 3 de como ou onde alguém usaria isto no mundo real."
  ],
  "category": "Uma única categoria curta sugerida (ex: Ferramentas, Inteligência Artificial, Automação, Web, Utilitários, Bases de Dados, Geral)"
}

Responde ESTRITAMENTE com o objeto JSON válido, sem texto fora dele.
"""

MODELS_ORDER = [
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
]

async def _call_gemini_api(prompt: str, api_key: str, system_prompt: str = SYSTEM_PROMPT) -> str:
    last_error = None

    # Try models via HTTP REST
    for model in MODELS_ORDER:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [
                    {"text": system_prompt}
                ]
            },
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                else:
                    last_error = f"Model {model} returned status {resp.status_code}: {resp.text[:150]}"
        except Exception as e:
            last_error = str(e)

    # If all models failed, try SDK as final attempt
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        response = await client.aio.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                temperature=0.2,
            )
        )
        if response and response.text:
            return response.text
    except Exception as e:
        last_error = str(e)

    raise RuntimeError(f"Falha na comunicação com a IA do Gemini: {last_error}")

def _extract_json(text: str) -> Any:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if match:
            cleaned = match.group(1).strip()
    return json.loads(cleaned)

async def analyze_repo_content(
    repo_name: str,
    repo_description: str,
    topics: list[str],
    readme_text: str,
    api_key: Optional[str] = None
) -> AnalysisResult:
    key = api_key or os.environ.get("GEMINI_API_KEY", "")

    truncated_readme = readme_text[:25000] if readme_text else "Sem README disponível."

    user_content = f"""Nome do repositório: {repo_name}
Descrição original: {repo_description or 'Não fornecida'}
Tópicos/Tags: {', '.join(topics) if topics else 'Nenhum'}

Conteúdo do README:
{truncated_readme}
"""

    if not key:
        return AnalysisResult(
            description_simple=f"{repo_name}: {repo_description or 'Repositório GitHub sem descrição fornecida.'} (Aviso: Define a chave GEMINI_API_KEY para obteres uma explicação simplificada gerada por IA).",
            use_cases=["Configurar a chave Gemini para obter exemplos práticos automáticos."],
            category="Geral"
        )

    try:
        raw_text = await _call_gemini_api(user_content, key)
        parsed = _extract_json(raw_text)
        return AnalysisResult(
            description_simple=parsed.get("description_simple", f"{repo_name}: {repo_description}"),
            use_cases=parsed.get("use_cases", []),
            category=parsed.get("category", "Geral")
        )
    except Exception as e:
        return AnalysisResult(
            description_simple=f"{repo_name}: {repo_description or 'Projeto de código no GitHub.'} (Não foi possível processar a explicação detalhada com IA: {str(e)}).",
            use_cases=["Explorar o código-fonte do repositório."],
            category="Geral"
        )

# ==================== PROJECT SUMMARY & MATCHING ====================

async def generate_project_summary_from_code(
    project_name: str,
    technologies: list[str],
    code_snippets: list[dict],
    api_key: Optional[str] = None
) -> str:
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key or not code_snippets:
        return f"Projeto '{project_name}' desenvolvido em {', '.join(technologies) if technologies else 'código local'}."

    snippets_text = "\n\n".join([f"--- Ficheiro: {s['file']} ---\n{s['content'][:1200]}" for s in code_snippets])

    prompt = f"""Analisa o código e estrutura deste projeto local do utilizador para escreveres um resumo claro e conciso:
Nome do Projeto: {project_name}
Tecnologias: {', '.join(technologies)}

Amostras de código:
{snippets_text}

Escreve em 2 a 3 frases claras e simples em Português Europeu o que este projeto faz e qual é o seu objetivo prático.
Responde em JSON com a chave "summary":
{{"summary": "O projeto..."}}
"""
    system_prompt = "És um programador experiente que resume o que projetos de código fazem em linguagem simples e direta."

    try:
        raw = await _call_gemini_api(prompt, key, system_prompt=system_prompt)
        parsed = _extract_json(raw)
        if isinstance(parsed, dict) and "summary" in parsed:
            return parsed["summary"]
        elif isinstance(parsed, str):
            return parsed
        return f"Projeto '{project_name}' em {', '.join(technologies)}."
    except Exception:
        return f"Projeto '{project_name}' desenvolvido em {', '.join(technologies)}."

async def match_repo_with_projects(
    repo_name: str,
    repo_description: str,
    repo_use_cases: list[str],
    projects: list[ProjectModel],
    api_key: Optional[str] = None
) -> List[dict]:
    if not projects:
        return []

    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return []

    projects_list_text = "\n".join([
        f"- ID: {p.id} | Nome: {p.name} | Resumo: {p.summary} | Tecnologias: {', '.join(p.technologies)}"
        for p in projects
    ])

    prompt = f"""Tens à frente um repositório do GitHub e a lista dos projetos pessoais que o utilizador está a desenvolver no computador.
A tua missão é avaliar se esta ferramenta do GitHub tem utilidade real e prática para ajudar em algum destes projetos.

DADOS DO REPOSITÓRIO GITHUB:
- Nome: {repo_name}
- Descrição: {repo_description}
- Casos de Uso: {', '.join(repo_use_cases)}

PROJETOS PESSOAIS DO UTILIZADOR:
{projects_list_text}

Responde ESTRITAMENTE em formato JSON com uma lista de correspondências relevantes:
[
  {{
    "project_id": <int>,
    "project_name": "<string>",
    "relevance_explanation": "Explicação direta (1 a 2 frases em Português Europeu) de como esta ferramenta do GitHub ajuda concretamente o projeto."
  }}
]

Regras obrigatórias:
1. Sê rigoroso: inclui APENAS projetos onde a ferramenta realmente possa ser útil ou integrada.
2. Se o repositório NÃO tiver utilidade para nenhum dos projetos, responde apenas: []
3. Não incluas texto fora do JSON.
"""

    system_prompt = "És um consultor de arquitetura de software que faz pontes práticas entre bibliotecas de código aberto e projetos pessoais de programação."

    try:
        raw = await _call_gemini_api(prompt, key, system_prompt=system_prompt)
        parsed = _extract_json(raw)
        if isinstance(parsed, list):
            valid_matches = []
            for item in parsed:
                if isinstance(item, dict) and "project_id" in item and "relevance_explanation" in item:
                    valid_matches.append({
                        "project_id": int(item["project_id"]),
                        "project_name": item.get("project_name", ""),
                        "relevance_explanation": item["relevance_explanation"]
                    })
            return valid_matches
        return []
    except Exception:
        return []

async def convert_prompt_for_model(
    prompt_text: str,
    act: str,
    current_model: str,
    target_model: str,
    api_key: Optional[str] = None
) -> Dict[str, str]:
    """
    Otimiza e adapta o prompt para as características e pontos fortes do modelo de IA de destino
    (ex: Claude com tags XML e raciocínio estruturado, Gemini com multimodalidade e precisão,
    ChatGPT com formatação direta, DeepSeek com foco em raciocínio/código).
    """
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        # Fallback offline caso não haja chave Gemini configurada
        model_tips = {
            "Claude (Anthropic)": f"<system>\nTu és um especialista em {act}.\n</system>\n\n<instructions>\n{prompt_text}\n</instructions>\n\n<guidelines>\n- Mantém rigor e precisão.\n- Pensa passo a passo antes de responder.\n</guidelines>",
            "Google Gemini": f"**Papel:** Especialista em {act}\n\n**Instruções Principais:**\n{prompt_text}\n\n**Diretrizes:**\n- Dá respostas estruturadas, concisas e práticas.",
            "DeepSeek": f"### Instrução de Sistema ({act})\n{prompt_text}\n\n### Raciocínio:\nResolve problemas de forma lógica, passo a passo, detalhando o código e a arquitetura.",
            "Meta Llama": f"[INST] <<SYS>>\nTu és um assistente especializado em {act}.\n{prompt_text}\n<</SYS>>\n\nPronto para começar. [/INST]",
            "Mistral AI": f"<s>[INST] Tu és um especialista em {act}.\n\nInstrução:\n{prompt_text}\n\nResponde com clareza, concisão e lógica direta. [/INST]",
            "xAI Grok": f"### Papel: Especialista em {act}\n{prompt_text}\n\n### Diretrizes:\n- Responde de forma direta, analítica e sem rodeios corporativos.",
            "ChatGPT (OpenAI)": prompt_text
        }
        optimized = model_tips.get(target_model, prompt_text)
        return {
            "converted_prompt": optimized,
            "explanation": f"Prompt adaptado para a sintaxe e estrutura recomendada do {target_model}."
        }

    instruction_rules = f"""Tens à frente um prompt de IA com o papel '{act}', originalmente preparado para {current_model}.
O teu objetivo é reescrever e OTIMIZAR este prompt para o modelo de destino: '{target_model}'.

Características e melhores práticas para cada modelo:
- Se o modelo de destino for 'Claude (Anthropic)': usa tags XML semânticas (<system>, <context>, <instructions>, <rules>), incentiva raciocínio estruturado ('pensa passo a passo'), tom conversacional e profissional.
- Se o modelo de destino for 'Google Gemini': utiliza Markdown estruturado, marcadores claros, diretrizes objetivas de contexto e formato de saída esperado.
- Se o modelo de destino for 'DeepSeek': otimiza para resolução de problemas em profundidade, lógica analítica passo a passo (Chain-of-Thought) e precisão técnica.
- Se o modelo de destino for 'ChatGPT (OpenAI)': formato limpo, direto, definição de persona com 'Age como...', instruções de estilo e restrições negativas claras.
- Se o modelo de destino for 'Meta Llama': estrutura em blocos concisos, regras delimitadas e exemplos clarificadores.
- Se o modelo de destino for 'Mistral AI': blocos de instrução compactos [INST], raciocínio denso e objetivo, sem prolixidade.
- Se o modelo de destino for 'xAI Grok': tom direto, analítico, perspicaz, sem rodeios ou floreados desnecessários.

PROMPT ORIGINAL:
\"\"\"{prompt_text}\"\"\"

Responde ESTRITAMENTE em formato JSON:
{{
  "converted_prompt": "<o texto completo do prompt adaptado e melhorado para o modelo alvo>",
  "explanation": "<1 a 2 frases em Português Europeu explicando o que foi melhorado para tirar o máximo partido do modelo alvo>"
}}
"""

    system_prompt = "És um especialista em Prompt Engineering de topo a nível mundial, mestre nas nuances e sintaxes ideais para Claude, OpenAI GPT, Google Gemini, DeepSeek, Meta Llama e Mistral AI."

    try:
        raw = await _call_gemini_api(instruction_rules, key, system_prompt=system_prompt)
        parsed = _extract_json(raw)
        if isinstance(parsed, dict) and "converted_prompt" in parsed:
            return {
                "converted_prompt": parsed["converted_prompt"],
                "explanation": parsed.get("explanation", f"Prompt otimizado para o modelo {target_model}.")
            }
    except Exception as e:
        pass

    return {
        "converted_prompt": prompt_text,
        "explanation": f"Não foi possível contactar o serviço de IA para reescrever automaticamente. O prompt original foi mantido."
    }


async def convert_skill_for_model(
    skill_content: str,
    skill_name: str,
    current_model: str,
    target_model: str,
    api_key: Optional[str] = None
) -> Dict[str, str]:
    """
    Otimiza e adapta as instruções e estrutura de um SKILL.md para o modelo de IA pretendido
    (Claude, Google Gemini, ChatGPT, DeepSeek, Mistral AI, xAI Grok), preservando o frontmatter YAML.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY")

    # Offline fallback
    if not key:
        # Atualizar ou injetar target_model no frontmatter
        updated = skill_content
        if "---" in updated:
            parts = updated.split("---", 2)
            if len(parts) >= 3:
                fm = parts[1]
                body = parts[2]
                if re.search(r"^(?:target_model|model):", fm, re.MULTILINE):
                    fm = re.sub(r"^(?:target_model|model):\s*.+$", f"target_model: {target_model}", fm, flags=re.MULTILINE)
                else:
                    fm = fm.rstrip() + f"\ntarget_model: {target_model}\n"
                updated = f"---{fm}---{body}"
        return {
            "converted_skill": updated,
            "explanation": f"Skill adaptado para as diretrizes e sintaxe do modelo {target_model}."
        }

    instruction_rules = f"""Tens à frente o ficheiro de um Skill ('{skill_name}') escrito para {current_model}.
O teu objetivo é reescrever e OTIMIZAR este ficheiro SKILL.md para ser executado com a máxima eficácia pelo modelo: '{target_model}'.

REGRAS OBRIGATÓRIAS:
1. MANTÉM O FRONTMATTER YAML NO TOPO entre marcadores '---', atualizando ou adicionando o campo 'target_model: {target_model}'.
2. Adapta a estrutura do texto e instruções:
   - Para 'Claude (Anthropic)': usa tags XML semânticas (<instructions>, <guidelines>, <rules>, <examples>), encoraja planeamento estruturado e raciocínio técnico.
   - Para 'Google Gemini': usa Markdown estruturado, secções claras, declaração explícita de inputs/outputs e estilo direto.
   - Para 'DeepSeek': enfatiza raciocínio analítico, lógica detalhada passo a passo e resolução de problemas técnicos complexos.
   - Para 'ChatGPT (OpenAI)': formato limpo, direto, persona profissional com 'Age como...', instruções acionáveis e restrições claras.
   - Para 'Mistral AI': instruções compactas, sem floreados, estruturadas e focadas na execução imediata.
   - Para 'xAI Grok': tom direto, analítico, perspicaz, sem rodeios ou formalismos excessivos.
3. Não percas nenhuma regra técnica ou comando essencial do skill original.

CONTEÚDO DO SKILL ORIGINAL:
\"\"\"{skill_content}\"\"\"

Responde ESTRITAMENTE em formato JSON:
{{
  "converted_skill": "<o ficheiro SKILL.md completo com frontmatter e corpo adaptado para o modelo alvo>",
  "explanation": "<1 a 2 frases em Português Europeu explicando o que foi otimizado para o modelo alvo>"
}}
"""

    system_prompt = "És um especialista em AI Agent Skills e Engenharia de Prompts para Claude, Google Gemini, OpenAI GPT, DeepSeek, Mistral e Grok."

    try:
        raw = await _call_gemini_api(instruction_rules, key, system_prompt=system_prompt)
        parsed = _extract_json(raw)
        if isinstance(parsed, dict) and "converted_skill" in parsed:
            return {
                "converted_skill": parsed["converted_skill"],
                "explanation": parsed.get("explanation", f"Skill otimizado com sucesso para o modelo {target_model}.")
            }
    except Exception:
        pass

    # Fallback em caso de erro na chamada
    return {
        "converted_skill": skill_content,
        "explanation": f"Não foi possível processar a conversão via IA. O conteúdo original foi preservado."
    }


