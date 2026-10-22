import sqlite3
import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from backend.app.models import RepoModel, ProjectModel, PromptModel

DEFAULT_DB_PATH = "repos.db"

def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                owner TEXT NOT NULL,
                description_simple TEXT NOT NULL,
                use_cases TEXT NOT NULL,
                category TEXT NOT NULL,
                is_favorite INTEGER NOT NULL DEFAULT 0,
                is_cloned INTEGER NOT NULL DEFAULT 0,
                local_path TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS my_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                path TEXT UNIQUE NOT NULL,
                summary TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'em_desenvolvimento',
                technologies TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS project_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                repo_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_linked INTEGER NOT NULL DEFAULT 0,
                shortcut_path TEXT,
                UNIQUE(project_id, repo_id),
                FOREIGN KEY (project_id) REFERENCES my_projects(id) ON DELETE CASCADE,
                FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                act TEXT NOT NULL,
                prompt TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'Geral',
                source TEXT NOT NULL DEFAULT 'personalizado',
                target_model TEXT NOT NULL DEFAULT 'ChatGPT',
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS custom_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                content TEXT NOT NULL,
                target_model TEXT NOT NULL DEFAULT 'Claude',
                program TEXT NOT NULL DEFAULT 'Google Antigravity',
                file_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS facebook_saved_media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                author TEXT,
                description TEXT,
                summary_ai TEXT,
                category TEXT NOT NULL DEFAULT 'Geral',
                thumbnail_url TEXT,
                media_type TEXT NOT NULL DEFAULT 'video',
                local_file_path TEXT,
                file_size_bytes INTEGER DEFAULT 0,
                duration_seconds INTEGER DEFAULT 0,
                source TEXT NOT NULL DEFAULT 'Facebook',
                created_at TEXT NOT NULL
            )
        """)
        try:
            conn.execute("ALTER TABLE prompts ADD COLUMN target_model TEXT NOT NULL DEFAULT 'ChatGPT'")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE project_recommendations ADD COLUMN is_linked INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE project_recommendations ADD COLUMN shortcut_path TEXT")
        except Exception:
            pass
    conn.close()

def _row_to_model(row: sqlite3.Row) -> RepoModel:
    use_cases = []
    if row["use_cases"]:
        try:
            use_cases = json.loads(row["use_cases"])
        except Exception:
            use_cases = [row["use_cases"]]

    return RepoModel(
        id=row["id"],
        url=row["url"],
        name=row["name"],
        owner=row["owner"],
        description_simple=row["description_simple"],
        use_cases=use_cases,
        category=row["category"],
        is_favorite=bool(row["is_favorite"]),
        is_cloned=bool(row["is_cloned"]),
        local_path=row["local_path"],
        created_at=row["created_at"],
    )

def _row_to_project(row: sqlite3.Row) -> ProjectModel:
    techs = []
    if row["technologies"]:
        try:
            techs = json.loads(row["technologies"])
        except Exception:
            techs = [row["technologies"]]

    return ProjectModel(
        id=row["id"],
        name=row["name"],
        path=row["path"],
        summary=row["summary"],
        status=row["status"],
        technologies=techs,
        notes=row["notes"],
        created_at=row["created_at"],
    )

def save_repository(repo: RepoModel, db_path: str = DEFAULT_DB_PATH) -> int:
    init_db(db_path)
    conn = get_connection(db_path)
    created_at = repo.created_at or datetime.now().isoformat()
    use_cases_json = json.dumps(repo.use_cases, ensure_ascii=False)

    with conn:
        cursor = conn.execute("""
            INSERT INTO repositories (
                url, name, owner, description_simple, use_cases, category,
                is_favorite, is_cloned, local_path, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                name=excluded.name,
                owner=excluded.owner,
                description_simple=excluded.description_simple,
                use_cases=excluded.use_cases,
                category=excluded.category
        """, (
            repo.url,
            repo.name,
            repo.owner,
            repo.description_simple,
            use_cases_json,
            repo.category,
            1 if repo.is_favorite else 0,
            1 if repo.is_cloned else 0,
            repo.local_path,
            created_at,
        ))
        if cursor.lastrowid:
            repo_id = cursor.lastrowid
        else:
            cur = conn.execute("SELECT id FROM repositories WHERE url = ?", (repo.url,))
            row = cur.fetchone()
            repo_id = row["id"] if row else 0

    conn.close()
    return repo_id

def get_repository(repo_id: int, db_path: str = DEFAULT_DB_PATH) -> Optional[RepoModel]:
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return _row_to_model(row)
    return None

def get_repository_by_url(url: str, db_path: str = DEFAULT_DB_PATH) -> Optional[RepoModel]:
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.execute("SELECT * FROM repositories WHERE url = ?", (url,))
    row = cur.fetchone()
    conn.close()
    if row:
        return _row_to_model(row)
    return None

def get_repository_by_path(path: str, db_path: str = DEFAULT_DB_PATH) -> Optional[RepoModel]:
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.execute("SELECT * FROM repositories WHERE local_path = ?", (path,))
    row = cur.fetchone()
    conn.close()
    if row:
        return _row_to_model(row)
    return None

def list_repositories(
    category: Optional[str] = None,
    favorites_only: bool = False,
    cloned_only: bool = False,
    sort_by: str = "date",
    sort_order: str = "desc",
    db_path: str = DEFAULT_DB_PATH
) -> List[RepoModel]:
    init_db(db_path)
    conn = get_connection(db_path)
    query = "SELECT * FROM repositories WHERE 1=1"
    params = []

    if category:
        query += " AND category = ?"
        params.append(category)

    if favorites_only:
        query += " AND is_favorite = 1"

    if cloned_only:
        query += " AND is_cloned = 1"

    order_dir = "ASC" if sort_order.lower() == "asc" else "DESC"
    if sort_by == "name":
        query += f" ORDER BY name COLLATE NOCASE {order_dir}"
    else:
        # Default sort by date
        query += f" ORDER BY created_at {order_dir}, id {order_dir}"

    cur = conn.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return [_row_to_model(r) for r in rows]

def toggle_favorite(repo_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    init_db(db_path)
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("SELECT is_favorite FROM repositories WHERE id = ?", (repo_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return False
        new_val = 0 if row["is_favorite"] else 1
        conn.execute("UPDATE repositories SET is_favorite = ? WHERE id = ?", (new_val, repo_id))
    conn.close()
    return bool(new_val)

def update_repo_category(repo_id: int, new_category: str, db_path: str = DEFAULT_DB_PATH) -> bool:
    init_db(db_path)
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("UPDATE repositories SET category = ? WHERE id = ?", (new_category, repo_id))
        updated = cur.rowcount > 0
    conn.close()
    return updated

def mark_as_cloned(repo_id: int, local_path: str, db_path: str = DEFAULT_DB_PATH) -> bool:
    init_db(db_path)
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute(
            "UPDATE repositories SET is_cloned = 1, local_path = ? WHERE id = ?",
            (local_path, repo_id)
        )
        updated = cur.rowcount > 0
    conn.close()
    return updated

def delete_repository(repo_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    init_db(db_path)
    conn = get_connection(db_path)
    with conn:
        conn.execute("DELETE FROM project_recommendations WHERE repo_id = ?", (repo_id,))
        cur = conn.execute("DELETE FROM repositories WHERE id = ?", (repo_id,))
        deleted = cur.rowcount > 0
    conn.close()
    return deleted

# ==================== MY PROJECTS CRUD ====================

def save_project(proj: ProjectModel, db_path: str = DEFAULT_DB_PATH) -> int:
    init_db(db_path)
    conn = get_connection(db_path)
    created_at = proj.created_at or datetime.now().isoformat()
    techs_json = json.dumps(proj.technologies, ensure_ascii=False)

    with conn:
        cur = conn.execute("""
            INSERT INTO my_projects (name, path, summary, status, technologies, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                name=excluded.name,
                summary=excluded.summary,
                technologies=excluded.technologies
        """, (
            proj.name,
            proj.path,
            proj.summary,
            proj.status or "em_desenvolvimento",
            techs_json,
            proj.notes or "",
            created_at,
        ))
        if cur.lastrowid:
            proj_id = cur.lastrowid
        else:
            row = conn.execute("SELECT id FROM my_projects WHERE path = ?", (proj.path,)).fetchone()
            proj_id = row["id"] if row else 0

    conn.close()
    return proj_id

def get_project(proj_id: int, db_path: str = DEFAULT_DB_PATH) -> Optional[ProjectModel]:
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.execute("SELECT * FROM my_projects WHERE id = ?", (proj_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return _row_to_project(row)
    return None

def get_project_by_path(path: str, db_path: str = DEFAULT_DB_PATH) -> Optional[ProjectModel]:
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.execute("SELECT * FROM my_projects WHERE path = ?", (path,))
    row = cur.fetchone()
    conn.close()
    if row:
        return _row_to_project(row)
    return None

def list_projects(
    status: Optional[str] = None,
    sort_by: str = "date",
    sort_order: str = "desc",
    db_path: str = DEFAULT_DB_PATH
) -> List[ProjectModel]:
    init_db(db_path)
    conn = get_connection(db_path)
    query = "SELECT * FROM my_projects WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)

    order_dir = "ASC" if sort_order.lower() == "asc" else "DESC"
    if sort_by == "name":
        query += f" ORDER BY name COLLATE NOCASE {order_dir}"
    else:
        query += f" ORDER BY created_at {order_dir}, id {order_dir}"

    cur = conn.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return [_row_to_project(r) for r in rows]

def update_project(
    proj_id: int,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    summary: Optional[str] = None,
    technologies: Optional[List[str]] = None,
    db_path: str = DEFAULT_DB_PATH
) -> bool:
    init_db(db_path)
    conn = get_connection(db_path)
    updates = []
    params = []

    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)
    if summary is not None:
        updates.append("summary = ?")
        params.append(summary)
    if technologies is not None:
        updates.append("technologies = ?")
        params.append(json.dumps(technologies, ensure_ascii=False))

    if not updates:
        conn.close()
        return True

    params.append(proj_id)
    query = f"UPDATE my_projects SET {', '.join(updates)} WHERE id = ?"
    with conn:
        cur = conn.execute(query, params)
        updated = cur.rowcount > 0
    conn.close()
    return updated

def delete_project(proj_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    init_db(db_path)
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("DELETE FROM my_projects WHERE id = ?", (proj_id,))
        deleted = cur.rowcount > 0
    conn.close()
    return deleted

# ==================== RECOMMENDATIONS ====================

def save_recommendation(
    project_id: int,
    repo_id: int,
    reason: str,
    db_path: str = DEFAULT_DB_PATH
) -> int:
    init_db(db_path)
    conn = get_connection(db_path)
    created_at = datetime.now().isoformat()
    with conn:
        cur = conn.execute("""
            INSERT INTO project_recommendations (project_id, repo_id, reason, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(project_id, repo_id) DO UPDATE SET
                reason=excluded.reason
        """, (project_id, repo_id, reason, created_at))
        rec_id = cur.lastrowid
        if not rec_id:
            row = conn.execute(
                "SELECT id FROM project_recommendations WHERE project_id = ? AND repo_id = ?",
                (project_id, repo_id)
            ).fetchone()
            rec_id = row["id"] if row else 0
    conn.close()
    return rec_id

def get_project_recommendations(project_id: int, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.execute("""
        SELECT 
            pr.id, pr.project_id, pr.repo_id, pr.reason, pr.created_at,
            pr.is_linked, pr.shortcut_path,
            r.name as repo_name, r.url as repo_url, r.category as repo_category,
            r.description_simple as repo_description, r.is_favorite, r.is_cloned,
            r.local_path as repo_local_path
        FROM project_recommendations pr
        JOIN repositories r ON pr.repo_id = r.id
        WHERE pr.project_id = ?
        ORDER BY pr.id DESC
    """, (project_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def set_recommendation_link(
    project_id: int,
    repo_id: int,
    is_linked: bool,
    shortcut_path: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH
) -> bool:
    init_db(db_path)
    conn = get_connection(db_path)
    with conn:
        # Garante que existe registo
        cur = conn.execute(
            "SELECT id FROM project_recommendations WHERE project_id = ? AND repo_id = ?",
            (project_id, repo_id)
        )
        row = cur.fetchone()
        if not row:
            created_at = datetime.now().isoformat()
            conn.execute("""
                INSERT INTO project_recommendations (project_id, repo_id, reason, created_at, is_linked, shortcut_path)
                VALUES (?, ?, 'Ligado manualmente ao projeto.', ?, ?, ?)
            """, (project_id, repo_id, created_at, 1 if is_linked else 0, shortcut_path))
        else:
            conn.execute("""
                UPDATE project_recommendations
                SET is_linked = ?, shortcut_path = ?
                WHERE project_id = ? AND repo_id = ?
            """, (1 if is_linked else 0, shortcut_path, project_id, repo_id))
    conn.close()
    return True

def get_repo_recommendations(repo_id: int, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.execute("""
        SELECT 
            pr.id, pr.project_id, pr.repo_id, pr.reason, pr.created_at,
            p.name as project_name, p.path as project_path, p.status as project_status
        FROM project_recommendations pr
        JOIN my_projects p ON pr.project_id = p.id
        WHERE pr.repo_id = ?
        ORDER BY pr.id DESC
    """, (repo_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ==================== PROMPTS CRUD ====================

def _row_to_prompt(row: sqlite3.Row) -> PromptModel:
    keys = row.keys()
    return PromptModel(
        id=row["id"],
        act=row["act"],
        prompt=row["prompt"],
        category=row["category"],
        source=row["source"],
        target_model=row["target_model"] if "target_model" in keys else "ChatGPT",
        created_at=row["created_at"]
    )

def save_prompt(prompt: PromptModel, db_path: str = DEFAULT_DB_PATH) -> int:
    init_db(db_path)
    conn = get_connection(db_path)
    created_at = prompt.created_at or datetime.now().isoformat()
    with conn:
        cursor = conn.execute("""
            INSERT INTO prompts (act, prompt, category, source, target_model, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            prompt.act,
            prompt.prompt,
            prompt.category or "Geral",
            prompt.source or "personalizado",
            prompt.target_model or "ChatGPT",
            created_at
        ))
        prompt_id = cursor.lastrowid
    conn.close()
    return prompt_id

def get_prompt(prompt_id: int, db_path: str = DEFAULT_DB_PATH) -> Optional[PromptModel]:
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return _row_to_prompt(row)
    return None

def list_prompts(
    search: Optional[str] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    target_model: Optional[str] = None,
    sort_by: str = "date",
    sort_order: str = "desc",
    db_path: str = DEFAULT_DB_PATH
) -> List[PromptModel]:
    init_db(db_path)
    conn = get_connection(db_path)
    query = "SELECT * FROM prompts WHERE 1=1"
    params = []

    if category:
        query += " AND category = ?"
        params.append(category)

    if source:
        query += " AND source = ?"
        params.append(source)

    if target_model:
        query += " AND target_model = ?"
        params.append(target_model)

    if search:
        query += " AND (act LIKE ? OR prompt LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term])

    order_dir = "ASC" if sort_order.lower() == "asc" else "DESC"
    if sort_by == "act" or sort_by == "name":
        query += f" ORDER BY act COLLATE NOCASE {order_dir}"
    else:
        query += f" ORDER BY created_at {order_dir}, id {order_dir}"

    cur = conn.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return [_row_to_prompt(r) for r in rows]

def update_prompt(
    prompt_id: int,
    act: Optional[str] = None,
    prompt: Optional[str] = None,
    category: Optional[str] = None,
    target_model: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH
) -> bool:
    init_db(db_path)
    conn = get_connection(db_path)
    updates = []
    params = []

    if act is not None:
        updates.append("act = ?")
        params.append(act)
    if prompt is not None:
        updates.append("prompt = ?")
        params.append(prompt)
    if category is not None:
        updates.append("category = ?")
        params.append(category)
    if target_model is not None:
        updates.append("target_model = ?")
        params.append(target_model)

    if not updates:
        conn.close()
        return False

    params.append(prompt_id)
    with conn:
        cur = conn.execute(f"UPDATE prompts SET {', '.join(updates)} WHERE id = ?", params)
        success = cur.rowcount > 0
    conn.close()
    return success

def delete_prompt(prompt_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    init_db(db_path)
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
        success = cur.rowcount > 0
    conn.close()
    return success

# ==================== CUSTOM SKILLS DATABASE OPERATIONS ====================

def save_custom_skill(
    name: str,
    description: str,
    content: str,
    target_model: str = "Claude",
    program: str = "Google Antigravity",
    file_path: Optional[str] = "",
    db_path: str = DEFAULT_DB_PATH
) -> Dict[str, Any]:
    init_db(db_path)
    conn = get_connection(db_path)
    now = datetime.now().isoformat()
    with conn:
        cur = conn.execute(
            """
            INSERT INTO custom_skills (name, description, content, target_model, program, file_path, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, description, content, target_model, program, file_path or "", now, now)
        )
        skill_id = cur.lastrowid
    conn.close()
    return {
        "id": f"custom-{skill_id}",
        "db_id": skill_id,
        "name": name,
        "description": description,
        "content": content,
        "target_model": target_model,
        "program": program,
        "source": "Antigravity (Personalizado)",
        "file_path": file_path or "",
        "directory": os.path.dirname(file_path) if file_path else "",
        "is_custom": True,
        "created_at": now,
        "updated_at": now
    }

def list_custom_skills(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM custom_skills ORDER BY updated_at DESC")
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({
            "id": f"custom-{r['id']}",
            "db_id": r["id"],
            "name": r["name"],
            "description": r["description"],
            "content": r["content"],
            "target_model": r["target_model"],
            "program": r["program"],
            "source": "Antigravity (Personalizado)",
            "file_path": r["file_path"],
            "directory": os.path.dirname(r["file_path"]) if r["file_path"] else "",
            "is_custom": True,
            "created_at": r["created_at"],
            "updated_at": r["updated_at"]
        })
    return result

def get_custom_skill(skill_id: int, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM custom_skills WHERE id = ?", (skill_id,))
    r = cur.fetchone()
    conn.close()
    if not r:
        return None
    return {
        "id": f"custom-{r['id']}",
        "db_id": r["id"],
        "name": r["name"],
        "description": r["description"],
        "content": r["content"],
        "target_model": r["target_model"],
        "program": r["program"],
        "source": "Antigravity (Personalizado)",
        "file_path": r["file_path"],
        "directory": os.path.dirname(r["file_path"]) if r["file_path"] else "",
        "is_custom": True,
        "created_at": r["created_at"],
        "updated_at": r["updated_at"]
    }

def update_custom_skill(
    skill_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    content: Optional[str] = None,
    target_model: Optional[str] = None,
    program: Optional[str] = None,
    file_path: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH
) -> bool:
    init_db(db_path)
    conn = get_connection(db_path)
    updates = []
    params = []

    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if content is not None:
        updates.append("content = ?")
        params.append(content)
    if target_model is not None:
        updates.append("target_model = ?")
        params.append(target_model)
    if program is not None:
        updates.append("program = ?")
        params.append(program)
    if file_path is not None:
        updates.append("file_path = ?")
        params.append(file_path)

    if not updates:
        conn.close()
        return False

    updates.append("updated_at = ?")
    params.append(datetime.now().isoformat())

    params.append(skill_id)
    with conn:
        cur = conn.execute(f"UPDATE custom_skills SET {', '.join(updates)} WHERE id = ?", params)
        success = cur.rowcount > 0
    conn.close()
    return success

def delete_custom_skill(skill_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    init_db(db_path)
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("DELETE FROM custom_skills WHERE id = ?", (skill_id,))
        success = cur.rowcount > 0
    conn.close()
    return success

# ==================== FACEBOOK & MEDIA CRUD ====================

def save_media_item(
    url: str,
    title: str,
    author: Optional[str] = "",
    description: Optional[str] = "",
    summary_ai: Optional[str] = "",
    category: str = "Geral",
    thumbnail_url: Optional[str] = "",
    media_type: str = "video",
    local_file_path: Optional[str] = "",
    file_size_bytes: int = 0,
    duration_seconds: int = 0,
    source: str = "Facebook",
    db_path: str = DEFAULT_DB_PATH
) -> Dict[str, Any]:
    init_db(db_path)
    conn = get_connection(db_path)
    now = datetime.now().isoformat()
    with conn:
        cur = conn.execute(
            """
            INSERT INTO facebook_saved_media (
                url, title, author, description, summary_ai, category,
                thumbnail_url, media_type, local_file_path, file_size_bytes,
                duration_seconds, source, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                url, title, author or "", description or "", summary_ai or "", category,
                thumbnail_url or "", media_type, local_file_path or "", file_size_bytes,
                duration_seconds, source, now
            )
        )
        media_id = cur.lastrowid
    conn.close()
    return get_media_item(media_id, db_path=db_path) or {}

def get_media_item(media_id: int, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.execute("SELECT * FROM facebook_saved_media WHERE id = ?", (media_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)

def list_media_items(
    category: Optional[str] = None,
    search: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH
) -> List[Dict[str, Any]]:
    init_db(db_path)
    conn = get_connection(db_path)
    query = "SELECT * FROM facebook_saved_media WHERE 1=1"
    params = []

    if category:
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND (title LIKE ? OR description LIKE ? OR summary_ai LIKE ? OR author LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s, s])

    query += " ORDER BY id DESC"
    cur = conn.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_media_item(media_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    init_db(db_path)
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("DELETE FROM facebook_saved_media WHERE id = ?", (media_id,))
        success = cur.rowcount > 0
    conn.close()
    return success



