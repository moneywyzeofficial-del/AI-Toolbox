import os
import socket
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from backend.app.models import (
    RepoModel,
    AnalysisRequest,
    CategoryUpdateRequest,
    ProjectModel,
    ProjectUpdateRequest,
    ProjectScanRequest,
    ProjectScanResult,
    ProjectMatchResult,
    LocalRepoScanRequest,
    LocalRepoScanItem,
    LocalRepoImportRequest,
    LocalRepoBatchImportRequest,
    OpenPathRequest,
    LinkRepoRequest,
    CloneUrlRequest,
    PromptModel,
    PromptCreateRequest,
    PromptUpdateRequest,
    PromptConvertRequest,
    SkillModel,
    SkillCreateRequest,
    SkillUpdateRequest,
    SkillConvertRequest,
    MediaExtractRequest,
    MediaProcessRequest,
    MediaItemModel,
)
from backend.app.db import (
    init_db,
    save_repository,
    get_repository,
    get_repository_by_url,
    get_repository_by_path,
    list_repositories,
    toggle_favorite,
    update_repo_category,
    mark_as_cloned,
    save_project,
    get_project,
    get_project_by_path,
    list_projects,
    update_project,
    delete_project,
    save_recommendation,
    get_project_recommendations,
    set_recommendation_link,
    get_repo_recommendations,
    save_prompt,
    get_prompt,
    list_prompts,
    update_prompt,
    delete_prompt,
    save_custom_skill,
    list_custom_skills,
    get_custom_skill,
    update_custom_skill,
    delete_custom_skill,
    save_media_item,
    get_media_item,
    list_media_items,
    delete_media_item,
)
from backend.app.shortcut_service import create_project_shortcut, remove_project_shortcut
from backend.app.trending_service import fetch_github_trending, fetch_huggingface_trending
from backend.app.github_service import parse_github_url, fetch_repo_data
from backend.app.gemini_service import (
    analyze_repo_content,
    generate_project_summary_from_code,
    match_repo_with_projects,
)
from backend.app.media_service import (
    extract_media_info,
    process_and_save_media,
)
from backend.app.git_service import (
    clone_repository,
    get_default_download_dir,
    check_git_updates,
    pull_repository,
)
from backend.app.folder_scanner import scan_local_folder
from backend.app.local_scanner import scan_installed_repositories

def get_db_path() -> str:
    return os.environ.get("REPOS_DB_PATH", "repos.db")

def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(get_db_path())
    yield

app = FastAPI(
    title="AI Toolbox",
    description="Hub Inteligente de Projetos, GitHub, Prompts e Ferramentas de IA",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/network-info")
def get_network_info():
    ip = get_local_ip()
    port = int(os.environ.get("PORT", "8000"))
    return {
        "local_ip": ip,
        "port": port,
        "url": f"http://{ip}:{port}"
    }

@app.post("/api/analyze", response_model=RepoModel)
async def analyze_repo(req: AnalysisRequest):
    try:
        owner, repo_name = parse_github_url(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db_path = get_db_path()
    normalized_url = f"https://github.com/{owner}/{repo_name}"

    # Check if we already have it in the database (with successful analysis)
    existing = get_repository_by_url(normalized_url, db_path=db_path)
    if existing and not (
        "Não foi possível" in existing.description_simple 
        or "Client error" in existing.description_simple 
        or "Aviso:" in existing.description_simple
    ):
        # Fetch any stored recommendations for this repo
        recs = get_repo_recommendations(existing.id, db_path=db_path)
        existing.project_matches = [
            ProjectMatchResult(
                project_id=r["project_id"],
                project_name=r["project_name"],
                relevance_explanation=r["reason"]
            )
            for r in recs
        ]
        return existing

    # Fetch from GitHub
    try:
        github_data = await fetch_repo_data(owner, repo_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao consultar o GitHub: {str(e)}")

    # Analyze with Gemini
    analysis = await analyze_repo_content(
        repo_name=github_data["name"],
        repo_description=github_data["description"],
        topics=github_data["topics"],
        readme_text=github_data["readme_content"]
    )

    repo_model = RepoModel(
        url=normalized_url,
        name=github_data["name"],
        owner=github_data["owner"],
        description_simple=analysis.description_simple,
        use_cases=analysis.use_cases,
        category=analysis.category or "Geral",
        is_favorite=False,
        is_cloned=False,
        local_path=None
    )

    repo_id = save_repository(repo_model, db_path=db_path)
    saved = get_repository(repo_id, db_path=db_path)
    if not saved:
        raise HTTPException(status_code=500, detail="Erro ao guardar o repositório na base de dados.")

    # Intelligent cross-referencing with user's personal projects
    user_projects = list_projects(db_path=db_path)
    if user_projects:
        try:
            matches = await match_repo_with_projects(
                repo_name=saved.name,
                repo_description=saved.description_simple,
                repo_use_cases=saved.use_cases,
                projects=user_projects
            )
            for m in matches:
                save_recommendation(
                    project_id=m["project_id"],
                    repo_id=repo_id,
                    reason=m["relevance_explanation"],
                    db_path=db_path
                )
            saved.project_matches = [ProjectMatchResult(**m) for m in matches]
        except Exception:
            saved.project_matches = []

    return saved

@app.get("/api/repos", response_model=List[RepoModel])
def get_repos(
    category: Optional[str] = Query(None),
    favorites_only: bool = Query(False),
    cloned_only: bool = Query(False),
    sort_by: str = Query("date"),
    sort_order: str = Query("desc")
):
    db_path = get_db_path()
    return list_repositories(
        category=category,
        favorites_only=favorites_only,
        cloned_only=cloned_only,
        sort_by=sort_by,
        sort_order=sort_order,
        db_path=db_path
    )

@app.get("/api/trending")
async def api_get_trending(since: str = Query("daily")):
    """
    Obtém repositórios em alta (trending) no GitHub hoje/esta semana.
    """
    try:
        trending = await fetch_github_trending(since=since)
        return trending
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter repositórios em alta: {str(e)}")

@app.get("/api/trending/huggingface")
async def api_get_huggingface_trending(category: str = Query("models")):
    """
    Obtém modelos ou spaces em alta (trending) no Hugging Face.
    """
    try:
        trending = await fetch_huggingface_trending(category=category)
        return trending
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter tendências do Hugging Face: {str(e)}")

@app.get("/api/repos/{repo_id}", response_model=RepoModel)
def get_single_repo(repo_id: int):
    db_path = get_db_path()
    repo = get_repository(repo_id, db_path=db_path)
    if not repo:
        raise HTTPException(status_code=404, detail="Repositório não encontrado.")
    recs = get_repo_recommendations(repo_id, db_path=db_path)
    repo.project_matches = [
        ProjectMatchResult(
            project_id=r["project_id"],
            project_name=r["project_name"],
            relevance_explanation=r["reason"]
        )
        for r in recs
    ]
    return repo

@app.post("/api/repos/{repo_id}/favorite")
def api_toggle_favorite(repo_id: int):
    db_path = get_db_path()
    repo = get_repository(repo_id, db_path=db_path)
    if not repo:
        raise HTTPException(status_code=404, detail="Repositório não encontrado.")
    new_status = toggle_favorite(repo_id, db_path=db_path)
    return {"id": repo_id, "is_favorite": new_status}

@app.patch("/api/repos/{repo_id}/category", response_model=RepoModel)
def api_update_category(repo_id: int, req: CategoryUpdateRequest):
    db_path = get_db_path()
    repo = get_repository(repo_id, db_path=db_path)
    if not repo:
        raise HTTPException(status_code=404, detail="Repositório não encontrado.")
    update_repo_category(repo_id, req.category, db_path=db_path)
    updated = get_repository(repo_id, db_path=db_path)
    return updated

@app.post("/api/repos/{repo_id}/clone")
def api_clone_repo(repo_id: int):
    db_path = get_db_path()
    repo = get_repository(repo_id, db_path=db_path)
    if not repo:
        raise HTTPException(status_code=404, detail="Repositório não encontrado.")

    download_dir = get_default_download_dir()
    success, local_path, message = clone_repository(repo.url, target_dir=download_dir)
    if success:
        mark_as_cloned(repo_id, local_path, db_path=db_path)
        return {"success": True, "local_path": local_path, "message": message}
    else:
        raise HTTPException(status_code=500, detail=message)

@app.post("/api/repos/clone-url")
def api_clone_url(req: CloneUrlRequest):
    """
    Instala um repositório no computador através do URL.
    Guarda-o ou atualiza-o no catálogo de repositórios.
    """
    db_path = get_db_path()
    download_dir = get_default_download_dir()

    # Verifica se já existe registo
    existing = get_repository_by_url(req.url, db_path=db_path)

    # Executa o clone
    success, local_path, message = clone_repository(req.url, target_dir=download_dir)
    if not success:
        raise HTTPException(status_code=500, detail=message)

    if existing:
        mark_as_cloned(existing.id, local_path, db_path=db_path)
        repo_id = existing.id
    else:
        try:
            owner, name = parse_github_url(req.url)
        except Exception:
            owner = req.owner or "unknown"
            name = req.name or os.path.basename(local_path)

        new_repo = RepoModel(
            url=req.url,
            name=name,
            owner=owner,
            description_simple=req.description or f"Repositório {name} instalado a partir do GitHub Trending.",
            use_cases=[],
            category="Ferramenta",
            is_cloned=True,
            local_path=local_path
        )
        repo_id = save_repository(new_repo, db_path=db_path)

    return {
        "success": True,
        "repo_id": repo_id,
        "local_path": local_path,
        "message": f"Repositório instalado com sucesso em {local_path}!"
    }

@app.post("/api/repos/{repo_id}/git-status")
def api_repo_git_status(repo_id: int):
    db_path = get_db_path()
    repo = get_repository(repo_id, db_path=db_path)
    if not repo:
        raise HTTPException(status_code=404, detail="Repositório não encontrado.")
    if not repo.local_path or not os.path.exists(repo.local_path):
        raise HTTPException(status_code=400, detail="O repositório não tem pasta local associada ou a pasta não existe.")

    has_updates, msg, count = check_git_updates(repo.local_path)
    return {
        "repo_id": repo_id,
        "has_updates": has_updates,
        "message": msg,
        "behind_count": count
    }

@app.post("/api/repos/{repo_id}/git-pull")
def api_repo_git_pull(repo_id: int):
    db_path = get_db_path()
    repo = get_repository(repo_id, db_path=db_path)
    if not repo:
        raise HTTPException(status_code=404, detail="Repositório não encontrado.")
    if not repo.local_path or not os.path.exists(repo.local_path):
        raise HTTPException(status_code=400, detail="O repositório não tem pasta local associada ou a pasta não existe.")

    success, msg = pull_repository(repo.local_path)
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {
        "repo_id": repo_id,
        "success": True,
        "message": msg
    }

@app.post("/api/repos/{repo_id}/reanalyze", response_model=RepoModel)
async def api_reanalyze_repo(repo_id: int):
    db_path = get_db_path()
    repo = get_repository(repo_id, db_path=db_path)
    if not repo:
        raise HTTPException(status_code=404, detail="Repositório não encontrado.")

    if "github.com" in repo.url:
        try:
            owner, repo_name = parse_github_url(repo.url)
            repo_data = await fetch_repo_data(owner, repo_name)
            analysis = await analyze_repo_content(
                name=repo_data["name"],
                description=repo_data["description"] or "",
                readme_content=repo_data["readme"] or ""
            )
            updated_model = RepoModel(
                id=repo.id,
                url=repo.url,
                name=repo_data["name"],
                owner=owner,
                description_simple=analysis["description_simple"],
                use_cases=analysis["use_cases"],
                category=analysis["category"],
                is_favorite=repo.is_favorite,
                is_cloned=repo.is_cloned,
                local_path=repo.local_path,
                created_at=repo.created_at
            )
            save_repository(updated_model, db_path=db_path)
            return get_repository(repo_id, db_path=db_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao reanalisar no GitHub: {str(e)}")

    if repo.local_path and os.path.isdir(repo.local_path):
        readme_content = ""
        for f in os.listdir(repo.local_path):
            if f.lower().startswith("readme"):
                try:
                    with open(os.path.join(repo.local_path, f), "r", encoding="utf-8", errors="ignore") as rf:
                        readme_content = rf.read()
                    break
                except Exception:
                    pass

        try:
            analysis = await analyze_repo_content(
                name=repo.name,
                description=repo.description_simple,
                readme_content=readme_content
            )
            updated_model = RepoModel(
                id=repo.id,
                url=repo.url,
                name=repo.name,
                owner=repo.owner,
                description_simple=analysis["description_simple"],
                use_cases=analysis["use_cases"],
                category=analysis["category"],
                is_favorite=repo.is_favorite,
                is_cloned=repo.is_cloned,
                local_path=repo.local_path,
                created_at=repo.created_at
            )
            save_repository(updated_model, db_path=db_path)
            return get_repository(repo_id, db_path=db_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao reanalisar código local: {str(e)}")

    raise HTTPException(status_code=400, detail="Não foi possível reanalisar este repositório.")

@app.delete("/api/repos/{repo_id}")
def api_delete_repo(repo_id: int):
    db_path = get_db_path()
    repo = get_repository(repo_id, db_path=db_path)
    if not repo:
        raise HTTPException(status_code=404, detail="Repositório não encontrado.")
    from backend.app.db import delete_repository
    delete_repository(repo_id, db_path=db_path)
    return {"success": True, "id": repo_id}

@app.get("/api/categories", response_model=List[str])
def api_get_categories():
    db_path = get_db_path()
    repos = list_repositories(db_path=db_path)
    categories = sorted(list({r.category for r in repos if r.category}))
    return categories

# ==================== LOCAL INSTALLED REPOS ENDPOINTS ====================

@app.post("/api/local-repos/scan")
def api_scan_local_repos(req: Optional[LocalRepoScanRequest] = None):
    db_path = get_db_path()
    folder = (req.folder if req and req.folder else "").strip()
    if not folder:
        if os.path.exists(r"D:\AI Projects"):
            folder = r"D:\AI Projects"
        else:
            folder = get_default_download_dir()

    if not os.path.isdir(folder):
        raise HTTPException(status_code=404, detail=f"Pasta não encontrada: {folder}")

    raw_items = scan_installed_repositories(folder)
    results = []
    for item in raw_items:
        is_cataloged = False
        cat_id = None

        existing_by_path = get_repository_by_path(item["path"], db_path=db_path)
        if existing_by_path:
            is_cataloged = True
            cat_id = existing_by_path.id
        elif item["remote_url"]:
            existing_by_url = get_repository_by_url(item["remote_url"], db_path=db_path)
            if existing_by_url:
                is_cataloged = True
                cat_id = existing_by_url.id

        results.append(LocalRepoScanItem(
            name=item["name"],
            path=item["path"],
            remote_url=item["remote_url"],
            has_readme=item["has_readme"],
            is_cataloged=is_cataloged,
            catalog_id=cat_id
        ))

    return {
        "search_folder": folder,
        "repos": results
    }

@app.post("/api/local-repos/import", response_model=RepoModel)
async def api_import_local_repo(req: LocalRepoImportRequest):
    db_path = get_db_path()

    existing = get_repository_by_path(req.path, db_path=db_path)
    if not existing and req.remote_url:
        existing = get_repository_by_url(req.remote_url, db_path=db_path)
    if existing:
        if not existing.is_cloned or existing.local_path != req.path:
            mark_as_cloned(existing.id, req.path, db_path=db_path)
            existing = get_repository(existing.id, db_path=db_path)
        return existing

    if req.auto_analyze and req.remote_url:
        try:
            owner, repo_name = parse_github_url(req.remote_url)
            repo_data = await fetch_repo_data(owner, repo_name)
            analysis = await analyze_repo_content(
                name=repo_data["name"],
                description=repo_data["description"] or "",
                readme_content=repo_data["readme"] or ""
            )
            repo_model = RepoModel(
                url=f"https://github.com/{owner}/{repo_name}",
                name=repo_data["name"],
                owner=owner,
                description_simple=analysis["description_simple"],
                use_cases=analysis["use_cases"],
                category=analysis["category"],
                is_cloned=True,
                local_path=req.path
            )
            saved_id = save_repository(repo_model, db_path=db_path)
            saved = get_repository(saved_id, db_path=db_path)
            return saved
        except Exception:
            pass

    description = f"Repositório local instalado em {req.path}."
    readme_path = None
    if os.path.isdir(req.path):
        for f in os.listdir(req.path):
            if f.lower().startswith("readme"):
                readme_path = os.path.join(req.path, f)
                break

    if readme_path and os.path.isfile(readme_path):
        try:
            with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = [l.strip("#* \r\t") for l in f.read().split("\n") if l.strip()]
                if lines:
                    description = " ".join(lines[:3])[:400]
        except Exception:
            pass

    url = req.remote_url if req.remote_url else f"local://{req.name.lower()}"
    owner = "local"
    if req.remote_url:
        try:
            owner, _ = parse_github_url(req.remote_url)
        except Exception:
            owner = "local"

    repo_model = RepoModel(
        url=url,
        name=req.name,
        owner=owner,
        description_simple=description,
        use_cases=["Utilização no ambiente local"],
        category="Ferramentas",
        is_cloned=True,
        local_path=req.path
    )
    saved_id = save_repository(repo_model, db_path=db_path)
    return get_repository(saved_id, db_path=db_path)

@app.post("/api/local-repos/import-batch")
async def api_import_batch_local_repos(req: LocalRepoBatchImportRequest):
    imported = []
    errors = []
    for item in req.repos:
        try:
            res = await api_import_local_repo(item)
            imported.append(res)
        except Exception as e:
            errors.append({"name": item.name, "error": str(e)})
    return {
        "total": len(req.repos),
        "imported_count": len(imported),
        "imported": imported,
        "errors": errors
    }

@app.post("/api/open-folder")
def api_open_folder(req: OpenPathRequest):
    path = os.path.abspath(req.path)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Caminho não encontrado: {path}")
    try:
        if os.name == 'nt':
            os.startfile(path)
        else:
            import subprocess
            subprocess.Popen(["xdg-open", path])
        return {"success": True, "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao abrir pasta: {str(e)}")

@app.post("/api/open-in-editor")
def api_open_in_editor(req: OpenPathRequest):
    path = os.path.abspath(req.path)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Caminho não encontrado: {path}")
    try:
        import subprocess
        # Abre o VS Code no caminho indicado
        subprocess.Popen(f'code "{path}"', shell=True)
        return {"success": True, "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao abrir no editor: {str(e)}")

# ==================== MY PROJECTS ENDPOINTS ====================

@app.post("/api/browse-folder")
def api_browse_folder():
    from backend.app.folder_browser import open_folder_picker
    default_dir = r"D:\AI Projects" if os.path.exists(r"D:\AI Projects") else None
    selected_path = open_folder_picker(initial_dir=default_dir)
    return {"path": selected_path}

@app.get("/api/my-projects/quick-folders")
def api_quick_folders():
    """
    Lista instantaneamente as pastas de projetos existentes em D:\\AI Projects.
    """
    base_dir = r"D:\AI Projects"
    if not os.path.exists(base_dir):
        return {"folders": []}

    try:
        entries = os.listdir(base_dir)
        folders = []
        for name in entries:
            full = os.path.join(base_dir, name)
            if os.path.isdir(full) and not name.startswith(".") and name != "Downloaded_Repos":
                folders.append({"name": name, "path": full})
        folders.sort(key=lambda x: x["name"].lower())
        return {"folders": folders}
    except Exception as e:
        return {"folders": [], "error": str(e)}

@app.get("/api/browse-directory")
def api_browse_directory(path: Optional[str] = Query(None)):
    """
    Navegação instantânea de pastas do sistema em tempo real dentro da própria app (0ms de atraso).
    """
    current_path = path if (path and os.path.exists(path)) else r"D:\AI Projects"
    if not os.path.exists(current_path):
        current_path = r"D:\\" if os.path.exists(r"D:\\") else r"C:\\"

    parent_path = os.path.dirname(current_path) if os.path.dirname(current_path) != current_path else None

    # Lista discos disponíveis se parent_path for nulo ou se pedir a raiz
    drives = []
    for letter in ["C", "D", "E"]:
        d_path = f"{letter}:\\"
        if os.path.exists(d_path):
            drives.append({"name": f"Disco ({letter}:)", "path": d_path})

    subfolders = []
    try:
        entries = os.listdir(current_path)
        for e in entries:
            full = os.path.join(current_path, e)
            if os.path.isdir(full) and not e.startswith("$") and not e.startswith("."):
                subfolders.append({"name": e, "path": full})
        subfolders.sort(key=lambda x: x["name"].lower())
    except Exception as e:
        pass

    return {
        "current_path": current_path,
        "parent_path": parent_path,
        "drives": drives,
        "subfolders": subfolders
    }

@app.post("/api/my-projects/scan", response_model=ProjectScanResult)
async def api_scan_folder(req: ProjectScanRequest):
    try:
        scanned = scan_local_folder(req.path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao analisar pasta: {str(e)}")

    summary = ""
    if scanned.get("readme_content"):
        # Take first 500 characters or lines from README
        lines = [line.strip("#* \r\t") for line in scanned["readme_content"].split("\n") if line.strip()]
        summary = " ".join(lines[:3])[:350]
    else:
        # Generate summary with Gemini from code snippets
        summary = await generate_project_summary_from_code(
            project_name=scanned["name"],
            technologies=scanned["technologies"],
            code_snippets=scanned["code_snippets"]
        )

    return ProjectScanResult(
        name=scanned["name"],
        path=scanned["path"],
        summary=summary,
        technologies=scanned["technologies"],
        internal_repos=scanned["internal_repos"]
    )

@app.post("/api/my-projects", response_model=ProjectModel)
async def api_create_project(proj: ProjectModel):
    db_path = get_db_path()
    proj_id = save_project(proj, db_path=db_path)
    saved = get_project(proj_id, db_path=db_path)
    if not saved:
        raise HTTPException(status_code=500, detail="Erro ao guardar projeto na base de dados.")

    # Retroactive matching with existing repositories in catalog
    existing_repos = list_repositories(db_path=db_path)
    for repo in existing_repos:
        try:
            matches = await match_repo_with_projects(
                repo_name=repo.name,
                repo_description=repo.description_simple,
                repo_use_cases=repo.use_cases,
                projects=[saved]
            )
            for m in matches:
                save_recommendation(
                    project_id=proj_id,
                    repo_id=repo.id,
                    reason=m["relevance_explanation"],
                    db_path=db_path
                )
        except Exception:
            pass

    return saved

@app.get("/api/my-projects", response_model=List[ProjectModel])
def api_list_projects(
    status: Optional[str] = Query(None),
    sort_by: str = Query("date"),
    sort_order: str = Query("desc")
):
    db_path = get_db_path()
    return list_projects(
        status=status,
        sort_by=sort_by,
        sort_order=sort_order,
        db_path=db_path
    )

@app.get("/api/my-projects/{proj_id}")
def api_get_project(proj_id: int):
    db_path = get_db_path()
    proj = get_project(proj_id, db_path=db_path)
    if not proj:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    recs = get_project_recommendations(proj_id, db_path=db_path)
    return {
        "project": proj,
        "recommendations": recs
    }

@app.patch("/api/my-projects/{proj_id}", response_model=ProjectModel)
def api_update_project(proj_id: int, req: ProjectUpdateRequest):
    db_path = get_db_path()
    proj = get_project(proj_id, db_path=db_path)
    if not proj:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    update_project(
        proj_id=proj_id,
        status=req.status,
        notes=req.notes,
        summary=req.summary,
        technologies=req.technologies,
        db_path=db_path
    )
    return get_project(proj_id, db_path=db_path)

@app.delete("/api/my-projects/{proj_id}")
def api_delete_project(proj_id: int):
    db_path = get_db_path()
    deleted = delete_project(proj_id, db_path=db_path)
    if not deleted:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    return {"success": True, "id": proj_id}

@app.post("/api/my-projects/{proj_id}/refresh")
async def api_refresh_project(proj_id: int):
    db_path = get_db_path()
    proj = get_project(proj_id, db_path=db_path)
    if not proj:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    try:
        scanned = scan_local_folder(proj.path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao ler pasta do projeto: {str(e)}")

    summary = proj.summary
    if scanned.get("readme_content"):
        lines = [line.strip("#* \r\t") for line in scanned["readme_content"].split("\n") if line.strip()]
        summary = " ".join(lines[:3])[:350]
    elif not summary or "Projeto '" in summary:
        summary = await generate_project_summary_from_code(
            project_name=scanned["name"],
            technologies=scanned["technologies"],
            code_snippets=scanned["code_snippets"]
        )

    update_project(
        proj_id=proj_id,
        summary=summary,
        technologies=scanned["technologies"],
        db_path=db_path
    )

    return get_project(proj_id, db_path=db_path)

@app.post("/api/my-projects/{proj_id}/find-recommendations")
async def api_find_recommendations_for_project(proj_id: int):
    db_path = get_db_path()
    proj = get_project(proj_id, db_path=db_path)
    if not proj:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    existing_repos = list_repositories(db_path=db_path)
    new_matches = []
    for repo in existing_repos:
        try:
            matches = await match_repo_with_projects(
                repo_name=repo.name,
                repo_description=repo.description_simple,
                repo_use_cases=repo.use_cases,
                projects=[proj]
            )
            for m in matches:
                save_recommendation(
                    project_id=proj_id,
                    repo_id=repo.id,
                    reason=m["relevance_explanation"],
                    db_path=db_path
                )
                new_matches.append(m)
        except Exception:
            pass

    return {
        "project_id": proj_id,
        "recommendations": get_project_recommendations(proj_id, db_path=db_path)
    }

@app.post("/api/my-projects/{proj_id}/link-repo")
def api_link_repo_to_project(proj_id: int, req: LinkRepoRequest):
    db_path = get_db_path()
    proj = get_project(proj_id, db_path=db_path)
    if not proj:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    repo = get_repository(req.repo_id, db_path=db_path)
    if not repo:
        raise HTTPException(status_code=404, detail="Repositório não encontrado.")

    if not repo.is_cloned or not repo.local_path or not os.path.exists(repo.local_path):
        raise HTTPException(
            status_code=400,
            detail="O repositório precisa de estar instalado no computador antes de ser ligado ao projeto."
        )

    shortcut_name = f"Atalho - {repo.name}"
    success, shortcut_path = create_project_shortcut(
        target_dir=repo.local_path,
        destination_dir=proj.path,
        shortcut_name=shortcut_name
    )

    set_recommendation_link(
        project_id=proj_id,
        repo_id=req.repo_id,
        is_linked=True,
        shortcut_path=shortcut_path if success else None,
        db_path=db_path
    )

    msg = f"Atalho criado na pasta do projeto: {os.path.basename(shortcut_path)}" if success else "Repositório associado ao projeto."
    return {
        "success": True,
        "is_linked": True,
        "shortcut_path": shortcut_path if success else None,
        "message": msg
    }

@app.post("/api/my-projects/{proj_id}/unlink-repo")
def api_unlink_repo_from_project(proj_id: int, req: LinkRepoRequest):
    db_path = get_db_path()
    proj = get_project(proj_id, db_path=db_path)
    if not proj:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    recs = get_project_recommendations(proj_id, db_path=db_path)
    target_rec = next((r for r in recs if r["repo_id"] == req.repo_id), None)
    if target_rec and target_rec.get("shortcut_path"):
        remove_project_shortcut(target_rec["shortcut_path"])

    set_recommendation_link(
        project_id=proj_id,
        repo_id=req.repo_id,
        is_linked=False,
        shortcut_path=None,
        db_path=db_path
    )

    return {
        "success": True,
        "is_linked": False,
        "message": "Repositório desligado do projeto."
    }

# ==================== SKILLS ENDPOINTS ====================

@app.get("/api/skills")
def api_get_skills(
    program: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    from backend.app.skills_scanner import scan_all_skills
    scanned = scan_all_skills()
    custom_db = list_custom_skills(db_path=get_db_path())

    seen_paths = set()
    merged = []

    # 1. Custom skills from DB
    for cs in custom_db:
        if cs.get("file_path"):
            seen_paths.add(os.path.normpath(cs["file_path"]).lower())
        merged.append(cs)

    # 2. Scanned skills from disk
    for s in scanned:
        norm = os.path.normpath(s["file_path"]).lower()
        if norm not in seen_paths:
            seen_paths.add(norm)
            merged.append(s)

    # Filters
    if program:
        merged = [s for s in merged if s.get("program", "").lower() == program.lower()]

    if model:
        m_low = model.lower()
        merged = [s for s in merged if m_low in s.get("target_model", "").lower()]

    if search:
        q = search.lower()
        merged = [
            s for s in merged
            if q in s.get("name", "").lower()
            or q in s.get("description", "").lower()
            or (s.get("plugin") and q in s["plugin"].lower())
            or q in s.get("source", "").lower()
            or q in s.get("target_model", "").lower()
        ]

    return merged

@app.get("/api/skills/my")
def api_get_my_skills():
    """
    Retorna os skills criados ou alterados pelo utilizador.
    """
    custom_db = list_custom_skills(db_path=get_db_path())
    from backend.app.skills_scanner import scan_all_skills
    scanned = scan_all_skills()

    seen = {c["id"]: c for c in custom_db}
    for s in scanned:
        if s.get("is_custom") and s["id"] not in seen:
            seen[s["id"]] = s

    return list(seen.values())

@app.post("/api/skills")
def api_create_skill(req: SkillCreateRequest):
    home = os.path.expanduser("~")
    import re
    slug = re.sub(r'[^a-zA-Z0-9_\-]+', '-', req.name.strip().lower()).strip('-') or 'custom-skill'
    skill_dir = os.path.join(home, ".gemini", "config", "skills", slug)
    os.makedirs(skill_dir, exist_ok=True)
    file_path = os.path.join(skill_dir, "SKILL.md")

    raw_content = req.content.strip()
    if not raw_content.startswith("---"):
        full_content = f"""---
name: {req.name}
description: {req.description}
target_model: {req.target_model or 'Claude'}
---

{raw_content}
"""
    else:
        full_content = raw_content

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(full_content)
    except Exception:
        file_path = ""

    saved = save_custom_skill(
        name=req.name,
        description=req.description,
        content=full_content,
        target_model=req.target_model or "Claude",
        program=req.program or "Google Antigravity",
        file_path=file_path,
        db_path=get_db_path()
    )
    return saved

@app.put("/api/skills/{skill_id}")
def api_update_skill(skill_id: str, req: SkillUpdateRequest):
    db_id = None
    if skill_id.startswith("custom-"):
        try:
            db_id = int(skill_id.replace("custom-", ""))
        except ValueError:
            pass
    elif skill_id.isdigit():
        db_id = int(skill_id)

    target_path = req.file_path
    if db_id and not target_path:
        item = get_custom_skill(db_id, db_path=get_db_path())
        if item:
            target_path = item.get("file_path")

    if target_path and os.path.isfile(target_path) and req.content:
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(req.content)
        except Exception:
            pass

    if db_id:
        update_custom_skill(
            skill_id=db_id,
            name=req.name,
            description=req.description,
            content=req.content,
            target_model=req.target_model,
            file_path=target_path,
            db_path=get_db_path()
        )
        updated = get_custom_skill(db_id, db_path=get_db_path())
        return updated or {"status": "ok"}
    else:
        # Se era um skill nativo a ser personalizado
        saved = save_custom_skill(
            name=req.name or "Skill Personalizado",
            description=req.description or "",
            content=req.content or "",
            target_model=req.target_model or "Claude",
            program="Google Antigravity",
            file_path=target_path or "",
            db_path=get_db_path()
        )
        return saved

@app.delete("/api/skills/{skill_id}")
def api_delete_skill(skill_id: str):
    db_id = None
    if skill_id.startswith("custom-"):
        try:
            db_id = int(skill_id.replace("custom-", ""))
        except ValueError:
            pass
    elif skill_id.isdigit():
        db_id = int(skill_id)

    if db_id:
        item = get_custom_skill(db_id, db_path=get_db_path())
        delete_custom_skill(db_id, db_path=get_db_path())
        if item and item.get("file_path") and os.path.isfile(item["file_path"]):
            try:
                os.remove(item["file_path"])
            except Exception:
                pass
        return {"status": "deleted", "id": skill_id}
    raise HTTPException(status_code=404, detail="Skill personalizado não encontrado.")

@app.post("/api/skills/convert")
async def api_convert_skill(req: SkillConvertRequest):
    from backend.app.gemini_service import convert_skill_for_model
    try:
        result = await convert_skill_for_model(
            skill_content=req.skill_content,
            skill_name=req.skill_name or "Skill",
            current_model=req.current_model or "Claude",
            target_model=req.target_model
        )
        if isinstance(result, dict):
            result["target_model"] = req.target_model
            result["converted_content"] = result.get("converted_skill", "")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao converter skill: {str(e)}")

@app.get("/api/skills/content")
def api_get_skill_content(path: str = Query(...)):
    from backend.app.skills_scanner import read_skill_content
    try:
        content = read_skill_content(path)
        return {"file_path": path, "content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ficheiro do skill não encontrado.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== PROMPTS ENDPOINTS ====================

@app.get("/api/prompts/community")
async def api_get_community_prompts(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    refresh: bool = Query(False)
):
    from backend.app.prompts_service import load_prompts_chat_data
    try:
        prompts = await load_prompts_chat_data(force_refresh=refresh)
        if category and category != "all":
            prompts = [p for p in prompts if p.get("category", "").lower() == category.lower()]
        if search:
            q = search.lower().strip()
            prompts = [
                p for p in prompts
                if q in p["act"].lower() or q in p["prompt"].lower() or q in p.get("category", "").lower()
            ]
        return prompts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao carregar prompts da comunidade: {str(e)}")

@app.get("/api/prompts/community/categories")
async def api_get_community_categories():
    from backend.app.prompts_service import load_prompts_chat_data
    try:
        prompts = await load_prompts_chat_data()
        counts = {}
        for p in prompts:
            cat = p.get("category") or "Geral & Assistentes"
            counts[cat] = counts.get(cat, 0) + 1
        
        # Sort categories with highest count first or alphabetically
        sorted_cats = [
            {"name": cat, "count": count}
            for cat, count in sorted(counts.items(), key=lambda x: x[0])
        ]
        return sorted_cats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter categorias: {str(e)}")

@app.get("/api/prompts", response_model=List[PromptModel])
def api_list_prompts(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    target_model: Optional[str] = Query(None),
    sort_by: str = Query("date"),
    sort_order: str = Query("desc")
):
    db_path = get_db_path()
    return list_prompts(
        search=search,
        category=category,
        source=source,
        target_model=target_model,
        sort_by=sort_by,
        sort_order=sort_order,
        db_path=db_path
    )

@app.post("/api/prompts", response_model=PromptModel)
def api_create_prompt(req: PromptCreateRequest):
    db_path = get_db_path()
    p = PromptModel(
        act=req.act,
        prompt=req.prompt,
        category=req.category or "Geral",
        source=req.source or "personalizado",
        target_model=req.target_model or "ChatGPT"
    )
    prompt_id = save_prompt(p, db_path=db_path)
    created = get_prompt(prompt_id, db_path=db_path)
    if not created:
        raise HTTPException(status_code=500, detail="Erro ao guardar prompt.")
    return created

@app.get("/api/prompts/{prompt_id}", response_model=PromptModel)
def api_get_single_prompt(prompt_id: int):
    db_path = get_db_path()
    p = get_prompt(prompt_id, db_path=db_path)
    if not p:
        raise HTTPException(status_code=404, detail="Prompt não encontrado.")
    return p

@app.put("/api/prompts/{prompt_id}", response_model=PromptModel)
def api_update_prompt(prompt_id: int, req: PromptUpdateRequest):
    db_path = get_db_path()
    existing = get_prompt(prompt_id, db_path=db_path)
    if not existing:
        raise HTTPException(status_code=404, detail="Prompt não encontrado.")

    success = update_prompt(
        prompt_id=prompt_id,
        act=req.act,
        prompt=req.prompt,
        category=req.category,
        target_model=req.target_model,
        db_path=db_path
    )
    if not success:
        raise HTTPException(status_code=400, detail="Nenhuma alteração efetuada.")
    return get_prompt(prompt_id, db_path=db_path)

@app.delete("/api/prompts/{prompt_id}")
def api_delete_prompt(prompt_id: int):
    db_path = get_db_path()
    existing = get_prompt(prompt_id, db_path=db_path)
    if not existing:
        raise HTTPException(status_code=404, detail="Prompt não encontrado.")

    success = delete_prompt(prompt_id, db_path=db_path)
    return {"success": success, "message": "Prompt eliminado com sucesso."}

@app.post("/api/prompts/convert")
async def api_convert_prompt(req: PromptConvertRequest):
    from backend.app.gemini_service import convert_prompt_for_model
    try:
        result = await convert_prompt_for_model(
            prompt_text=req.prompt_text,
            act=req.act or "Prompt",
            current_model=req.current_model or "ChatGPT",
            target_model=req.target_model
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao converter prompt: {str(e)}")

# ==================== FACEBOOK & MEDIA ENDPOINTS ====================

@app.get("/api/media", response_model=List[MediaItemModel])
def api_list_media(category: Optional[str] = None, search: Optional[str] = None):
    db_path = get_db_path()
    return list_media_items(category=category, search=search, db_path=db_path)

@app.post("/api/media/extract")
async def api_extract_media(req: MediaExtractRequest):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="URL inválido ou em falta.")
    try:
        data = await extract_media_info(req.url.strip())
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao analisar o link: {str(e)}")

@app.post("/api/media/process", response_model=MediaItemModel)
async def api_process_media(req: MediaProcessRequest):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="URL inválido ou em falta.")
    try:
        db_path = get_db_path()
        result = await process_and_save_media(
            url=req.url.strip(),
            download_video=req.download_video,
            db_path=db_path
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar conteúdo: {str(e)}")

@app.delete("/api/media/{media_id}")
def api_delete_media(media_id: int):
    db_path = get_db_path()
    item = get_media_item(media_id, db_path=db_path)
    if not item:
        raise HTTPException(status_code=404, detail="Item de média não encontrado.")
    
    # Se tiver ficheiro descarregado localmente, remove-o
    local_path = item.get("local_file_path")
    if local_path and os.path.exists(local_path):
        try:
            os.remove(local_path)
        except Exception:
            pass

    deleted = delete_media_item(media_id, db_path=db_path)
    return {"success": deleted, "message": "Item removido com sucesso."}

@app.get("/api/media/{media_id}/stream")
def api_stream_media(media_id: int, request: Request):
    import re
    db_path = get_db_path()
    item = get_media_item(media_id, db_path=db_path)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    
    file_path = item.get("local_file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Ficheiro de vídeo local não encontrado.")
        
    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")
    
    if range_header:
        byte1, byte2 = 0, None
        match = re.search(r"bytes=(\d+)-(\d*)", range_header)
        if match:
            g1, g2 = match.groups()
            byte1 = int(g1)
            if g2:
                byte2 = int(g2)
        if byte2 is None or byte2 >= file_size:
            byte2 = file_size - 1
            
        length = byte2 - byte1 + 1
        
        def iterfile():
            with open(file_path, "rb") as f:
                f.seek(byte1)
                remaining = length
                while remaining > 0:
                    chunk_size = min(64 * 1024, remaining)
                    data = f.read(chunk_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data
                    
        headers = {
            "Content-Range": f"bytes {byte1}-{byte2}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
            "Content-Type": "video/mp4",
        }
        return StreamingResponse(iterfile(), status_code=206, headers=headers)
    else:
        def iterfile():
            with open(file_path, "rb") as f:
                while chunk := f.read(64 * 1024):
                    yield chunk
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": "video/mp4",
        }
        return StreamingResponse(iterfile(), status_code=200, headers=headers)

# Mount static files if directory exists
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

