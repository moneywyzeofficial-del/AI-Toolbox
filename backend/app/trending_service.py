import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any

TRENDING_URL = "https://github.com/trending?since=daily"

async def fetch_github_trending(since: str = "daily") -> List[Dict[str, Any]]:
    """
    Obtém os repositórios em alta (trending) no GitHub hoje.
    """
    url = f"https://github.com/trending?since={since}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8"
    }

    async with httpx.AsyncClient(timeout=12.0) as client:
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            return []

    soup = BeautifulSoup(response.text, "html.parser")
    articles = soup.find_all("article", class_="Box-row")

    trending_list = []
    for art in articles:
        h2 = art.find("h2")
        if not h2:
            continue

        raw_name = "".join(h2.text.split())
        parts = raw_name.split("/")
        if len(parts) != 2:
            continue
        owner, name = parts[0], parts[1]
        repo_url = f"https://github.com/{owner}/{name}"

        # Descrição
        p_desc = art.find("p")
        description = p_desc.text.strip() if p_desc else ""

        # Linguagem
        span_lang = art.find("span", itemprop="programmingLanguage")
        language = span_lang.text.strip() if span_lang else ""

        # Estrelas totais
        stars = ""
        forks = ""
        links = art.find_all("a", class_="Link--muted")
        for l in links:
            svg = l.find("svg")
            if svg and "octicon-star" in str(svg):
                stars = l.text.strip().replace(",", "")
            elif svg and "octicon-repo-forked" in str(svg):
                forks = l.text.strip().replace(",", "")

        # Estrelas hoje
        stars_today = ""
        span_today = art.find("span", class_="d-inline-block float-sm-right")
        if span_today:
            stars_today = span_today.text.strip()

        trending_list.append({
            "name": name,
            "owner": owner,
            "full_name": f"{owner}/{name}",
            "url": repo_url,
            "description": description,
            "language": language,
            "stars": stars,
            "forks": forks,
            "stars_today": stars_today
        })

    return trending_list

def generate_hf_item_description(
    item_id: str,
    name: str,
    author: str,
    pipeline_tag: str,
    item_type: str,
    tags: list = None,
    sdk: str = None
) -> str:
    """
    Gera uma descrição concisa e informativa em português europeu sobre o que é
    e para que serve o modelo ou space do Hugging Face.
    """
    tags = tags or []
    tags_lower = [str(t).lower() for t in tags]
    name_lower = name.lower()
    author_lower = author.lower()
    full_str = f"{author_lower}/{name_lower} " + " ".join(tags_lower)

    # 1. Mapeamento base de tarefas
    task_map = {
        "text-generation": "Modelo de linguagem (LLM) para geração de texto, conversação, programação e raciocínio lógico.",
        "image-text-to-text": "Modelo multimodal de visão e linguagem para análise de imagens, leitura de documentos (OCR) e perguntas visuais.",
        "visual-question-answering": "Modelo multimodal focado em interpretação e resposta a questões baseadas em imagens.",
        "text-to-image": "Geração de imagens artísticas e realistas de alta resolução a partir de instruções em texto.",
        "image-to-image": "Transformação, edição, expansão e melhoria de imagens existentes com inteligência artificial.",
        "automatic-speech-recognition": "Reconhecimento de fala e transcrição automática de ficheiros de áudio e voz em texto.",
        "text-to-speech": "Síntese vocal com entoação realista a partir de texto escrito.",
        "feature-extraction": "Extração de representações vetoriais (embeddings) para pesquisa semântica e sistemas RAG.",
        "sentence-similarity": "Cálculo de similaridade semântica e correspondência de texto para pesquisa vetorial.",
        "translation": "Tradução automática de alta precisão entre múltiplos idiomas.",
        "depth-estimation": "Estimativa de mapas de profundidade 3D a partir de fotografias 2D.",
        "object-detection": "Deteção e localização de objetos em imagens em tempo real.",
        "image-classification": "Classificação e reconhecimento de categorias e temas em imagens.",
        "text-classification": "Classificação de texto, análise de sentimento ou deteção de categorias.",
        "token-classification": "Identificação de entidades mencionadas (NER) e anotação estruturada de texto.",
        "video-to-video": "Edição e transformação de vídeo assistida por inteligência artificial.",
        "text-to-video": "Geração de clips de vídeo a partir de prompts e descrições em texto.",
        "reinforcement-learning": "Agente autónomo treinado por aprendizagem por reforço.",
        "robotics": "Políticas de controlo para automação e sistemas de robótica inteligente."
    }

    base_desc = task_map.get(pipeline_tag, "")

    # 2. Deteção de famílias ou especializações notáveis
    if "face-swap" in full_str or "faceswap" in full_str:
        spec_desc = "Ferramenta para troca e substituição de rostos em fotografias com alinhamento facial de alta fidelidade."
    elif "flux" in full_str:
        spec_desc = "Modelo de geração visual da família Flux, conhecido por grande realismo, composição artística e renderização precisa de texto em imagens."
    elif "stable-diffusion" in full_str or "sdxl" in full_str:
        spec_desc = "Modelo de difusão para criação de arte digital e ilustrações a partir de texto."
    elif "whisper" in full_str:
        spec_desc = "Modelo de transcrição de áudio altamente robusto em múltiplos idiomas e dialetos."
    elif "deepseek" in full_str:
        spec_desc = "Modelo de raciocínio lógico avançado da família DeepSeek, com forte capacidade matemática e algorítmica."
    elif "llama" in full_str:
        spec_desc = "Modelo de linguagem de código aberto da Meta, altamente versátil para processamento de linguagem natural."
    elif "qwen" in full_str:
        spec_desc = "Modelo de linguagem e raciocínio de alta performance da família Qwen (Alibaba)."
    elif "gemma" in full_str:
        spec_desc = "Modelo de linguagem leve e eficiente desenvolvido pela Google DeepMind."
    elif "mistral" in full_str:
        spec_desc = "Modelo de linguagem europeu da Mistral AI, focado em alta densidade de raciocínio e velocidade."
    else:
        spec_desc = ""

    # 3. Construção da descrição final para Space ou Model
    if item_type == "space":
        engine = f" em {sdk.title()}" if sdk else ""
        if spec_desc:
            desc = f"Aplicação web interativa{engine}: {spec_desc} Permite testar diretamente no navegador sem instalação local."
        elif base_desc:
            desc = f"Aplicação web interativa{engine} para testar e demonstrar este modelo de {pipeline_tag}. Permite experimentar diretamente no navegador."
        else:
            desc = f"Aplicação web interativa{engine} desenvolvida por {author} para experimentar soluções de inteligência artificial diretamente no navegador."
    else:
        parts = []
        if spec_desc:
            parts.append(spec_desc)
        elif base_desc:
            parts.append(base_desc)
        else:
            parts.append(f"Modelo de inteligência artificial da categoria {pipeline_tag} disponibilizado por {author}.")

        nuances = []
        if "coder" in name_lower or "code" in name_lower:
            nuances.append("Otimizado com conhecimento especializado em programação e sintaxe de software.")
        elif "instruct" in name_lower or "chat" in name_lower:
            nuances.append("Afinado para seguir instruções diretas e manter diálogos com o utilizador.")
        if "r1" in name_lower or "reason" in name_lower:
            nuances.append("Focado em raciocínio analítico profundo passo a passo.")
        if "uncensored" in name_lower or "abliterated" in name_lower:
            nuances.append("Variante desprovida de recusas artificiais para maior liberdade de resposta.")
        if "gguf" in name_lower or "quant" in name_lower:
            nuances.append("Versão quantizada para menor consumo de memória RAM/VRAM.")
        if "lora" in name_lower:
            nuances.append("Adaptador leve de ajuste fino (LoRA).")

        if nuances:
            parts.append(" ".join(nuances))

        desc = " ".join(parts)

    return desc

async def fetch_huggingface_trending(category: str = "models", limit: int = 20) -> List[Dict[str, Any]]:
    """
    Obtém modelos ou spaces em alta (trending) no Hugging Face com descrição contextualizada.
    """
    endpoint = "models" if category == "models" else "spaces"
    url = f"https://huggingface.co/api/{endpoint}?sort=trendingScore&direction=-1&limit={limit}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                return []
            items = response.json()
    except Exception:
        return []

    results = []
    for it in items:
        item_id = it.get("id") or it.get("modelId")
        if not item_id:
            continue

        parts = item_id.split("/")
        if len(parts) == 2:
            author, name = parts[0], parts[1]
        else:
            author, name = "huggingface", item_id

        item_url = f"https://huggingface.co/{endpoint}/{item_id}" if endpoint == "spaces" else f"https://huggingface.co/{item_id}"
        likes = it.get("likes", 0)
        downloads = it.get("downloads", 0)
        pipeline_tag = it.get("pipeline_tag") or it.get("sdk") or "IA"
        tags = it.get("tags") or []
        sdk = it.get("sdk") or ""
        item_type = "model" if endpoint == "models" else "space"

        description = generate_hf_item_description(
            item_id=item_id,
            name=name,
            author=author,
            pipeline_tag=pipeline_tag,
            item_type=item_type,
            tags=tags,
            sdk=sdk
        )

        results.append({
            "name": name,
            "author": author,
            "full_name": item_id,
            "url": item_url,
            "type": item_type,
            "task": pipeline_tag,
            "description": description,
            "likes": f"{likes:,}" if likes else "0",
            "downloads": f"{downloads:,}" if downloads else "0"
        })

    return results

