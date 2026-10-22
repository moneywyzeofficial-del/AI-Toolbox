import os
import re
import asyncio
from typing import Dict, Any, Optional
import yt_dlp
from backend.app.db import save_media_item
from backend.app.gemini_service import _call_gemini_api

MEDIA_SYSTEM_PROMPT = """És um assistente útil e conciso em Português Europeu (de Portugal).
O utilizador guardou um vídeo ou publicação (do Facebook ou de outra rede social).
A tua missão é gerar um resumo curto, claro e útil sobre o conteúdo com base no título, descrição e detalhes fornecidos.

ESTRUTURA DO JSON:
{
  "summary": "Resumo em 2 a 3 frases claras e diretas em português europeu.",
  "category": "Categoria sugerida (ex: Jardinagem, Culinária, Notícias, Tecnologia, Tutoriais, Humor, Piscinas, Geral)",
  "key_points": ["Ponto principal 1", "Ponto principal 2"]
}

Responde ESTRITAMENTE com o JSON válido, sem texto fora dele.
"""

def get_downloads_dir() -> str:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "downloads", "facebook"))
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

def detect_source(url: str) -> str:
    url_lower = url.lower()
    if "facebook.com" in url_lower or "fb.watch" in url_lower or "fb.me" in url_lower:
        return "Facebook"
    if "instagram.com" in url_lower:
        return "Instagram"
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "YouTube"
    if "tiktok.com" in url_lower:
        return "TikTok"
    return "Web"

def extract_media_info_sync(url: str) -> Dict[str, Any]:
    """Extrai metadados do vídeo/post sem descarregar."""
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            raise ValueError("Não foi possível extrair informação do URL.")
        
        # Pode vir como playlist se for uma página com múltiplos vídeos
        if 'entries' in info and info['entries']:
            info = info['entries'][0]
            
        title = info.get('title') or info.get('description', '')[:50] or "Vídeo sem título"
        author = info.get('uploader') or info.get('channel') or info.get('creator') or ""
        description = info.get('description') or ""
        duration = int(info.get('duration') or 0)
        thumbnail = info.get('thumbnail') or ""
        source = detect_source(url)
        
        # Tenta obter URL de stream direto se existir
        stream_url = ""
        formats = info.get('formats', [])
        for f in reversed(formats):
            if f.get('url') and f.get('vcodec') != 'none':
                stream_url = f.get('url')
                break
                
        return {
            "title": title,
            "author": author,
            "description": description,
            "duration_seconds": duration,
            "thumbnail_url": thumbnail,
            "source": source,
            "stream_url": stream_url,
            "media_type": "video" if duration > 0 or info.get('vcodec') else "post"
        }

async def extract_media_info(url: str) -> Dict[str, Any]:
    return await asyncio.to_thread(extract_media_info_sync, url)

def download_media_sync(url: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
    """Descarrega o vídeo em mp4 para a pasta local e devolve metadados e caminho."""
    save_dir = output_dir or get_downloads_dir()
    os.makedirs(save_dir, exist_ok=True)
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(save_dir, '%(id)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if not info:
            raise ValueError("Falha ao descarregar média.")
            
        if 'entries' in info and info['entries']:
            info = info['entries'][0]
            
        video_id = info.get('id', 'video')
        # Procura o ficheiro final descarregado
        expected_filename = ydl.prepare_filename(info)
        # Se houve merge para mp4, a extensão final é .mp4
        mp4_filename = os.path.splitext(expected_filename)[0] + ".mp4"
        
        final_path = mp4_filename if os.path.exists(mp4_filename) else expected_filename
        file_size = os.path.getsize(final_path) if os.path.exists(final_path) else 0
        
        title = info.get('title') or "Vídeo guardado"
        author = info.get('uploader') or info.get('channel') or ""
        description = info.get('description') or ""
        duration = int(info.get('duration') or 0)
        thumbnail = info.get('thumbnail') or ""
        source = detect_source(url)
        
        return {
            "title": title,
            "author": author,
            "description": description,
            "duration_seconds": duration,
            "thumbnail_url": thumbnail,
            "source": source,
            "local_file_path": final_path,
            "file_size_bytes": file_size,
            "media_type": "video"
        }

async def download_media(url: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
    return await asyncio.to_thread(download_media_sync, url, output_dir)

async def summarize_media(title: str, description: str, author: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return {
            "summary": f"Vídeo de {author}: {title}" if author else title,
            "category": "Geral",
            "key_points": []
        }
        
    prompt = f"Título: {title}\nAutor: {author}\nDescrição: {description[:1000]}"
    try:
        raw_resp = await _call_gemini_api(prompt, key, system_prompt=MEDIA_SYSTEM_PROMPT)
        import json
        clean = raw_resp.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.endswith("```"):
            clean = clean[:-3]
        data = json.loads(clean.strip())
        return {
            "summary": data.get("summary", title),
            "category": data.get("category", "Geral"),
            "key_points": data.get("key_points", [])
        }
    except Exception as e:
        return {
            "summary": f"Vídeo: {title}",
            "category": "Geral",
            "key_points": []
        }

async def process_and_save_media(url: str, download_video: bool = True, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Fluxo completo: extrai/descarrega, resume com IA e grava na BD."""
    if download_video:
        media_data = await download_media(url)
    else:
        media_data = await extract_media_info(url)
        media_data["local_file_path"] = ""
        media_data["file_size_bytes"] = 0

    ai_data = await summarize_media(
        title=media_data["title"],
        description=media_data["description"],
        author=media_data["author"]
    )
    
    actual_db = db_path or "data/repos.db"
    saved = save_media_item(
        url=url,
        title=media_data["title"],
        author=media_data.get("author", ""),
        description=media_data.get("description", ""),
        summary_ai=ai_data.get("summary", ""),
        category=ai_data.get("category", "Geral"),
        thumbnail_url=media_data.get("thumbnail_url", ""),
        media_type=media_data.get("media_type", "video"),
        local_file_path=media_data.get("local_file_path", ""),
        file_size_bytes=media_data.get("file_size_bytes", 0),
        duration_seconds=media_data.get("duration_seconds", 0),
        source=media_data.get("source", "Facebook"),
        db_path=actual_db
    )
    return saved
