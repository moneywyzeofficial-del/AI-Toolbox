# Os Meus Projetos e Cruzamento Inteligente Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to catalog their local development projects from disk folders, automatically summarize them via README or Gemini AI code analysis, detect tech stacks and internal repos, and intelligently cross-reference newly analyzed or existing GitHub repositories with their personal projects.

**Architecture:** Extend FastAPI backend with SQLite tables for `my_projects` and `project_recommendations`. Add a `folder_scanner.py` service to safely inspect local directories and git configurations. Enhance `gemini_service.py` with prompts to generate project summaries from code and evaluate practical relevance between GitHub repos and personal projects. Update the responsive web frontend with a dedicated "Os Meus Projetos" tab and utility match badges on the analysis screen.

**Tech Stack:** Python 3.12, FastAPI, SQLite3, google-genai / HTTP REST, pytest, TailwindCSS, JavaScript.

**Spec:** [docs/superpowers/specs/2026-10-16-meus-projetos-e-cruzamento-design.md](file:///d:/AI%20Projects/Github%20Repo%20Organizer/docs/superpowers/specs/2026-10-16-meus-projetos-e-cruzamento-design.md)

## Global Constraints

- Platform: Windows (Python 3.12, Git installed).
- Language: European Portuguese for all user-facing texts, summaries, and match explanations.
- Non-Destructive: Never modify or alter files in the user's project folders.
- Manual Confirmation: Internal repos detected inside project folders are only added to the main catalog upon explicit user confirmation.
- Offline-First: All project data and cross-reference recommendations are stored persistently in SQLite.
- Git commits: Never commit automatically without explicit user request.

## Review Focus

1. Invalid or non-existent local directory path -> return clean HTTP 400 error in Portuguese without crashing.
2. Large project directories (e.g. `node_modules`, `.venv`, `.git`) -> scanner must skip these to prevent high CPU or memory usage.
3. Project without README or code -> fallback gracefully with user-editable placeholder.
4. Analyzing a GitHub repo when user has zero projects registered -> analyze cleanly without errors, stating no personal projects are registered yet.
5. Re-analyzing a project folder -> preserve user's personal notes and project status intact.

---

### Task 1: SQLite Schema & Data Layer for My Projects

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/db.py`
- Test: `tests/test_my_projects_db.py`

**Interfaces:**
- Consumes: `pydantic`, `sqlite3`.
- Produces:
  - `ProjectModel` (id, name, path, summary, status, technologies: List[str], notes: str, created_at)
  - `save_project(proj: ProjectModel, db_path) -> int`
  - `get_project(proj_id: int, db_path) -> Optional[ProjectModel]`
  - `list_projects(status: Optional[str] = None, db_path) -> List[ProjectModel]`
  - `update_project(proj_id: int, status: Optional[str] = None, notes: Optional[str] = None, summary: Optional[str] = None, technologies: Optional[List[str]] = None, db_path) -> bool`
  - `save_recommendation(project_id: int, repo_id: int, reason: str, db_path) -> int`
  - `get_project_recommendations(project_id: int, db_path) -> List[dict]`

- [ ] **Step 1: Write failing tests for project and recommendation database operations**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement ProjectModel and DB methods in db.py**
- [ ] **Step 4: Run test to verify it passes**

---

### Task 2: Local Folder Scanner Service

**Files:**
- Create: `backend/app/folder_scanner.py`
- Test: `tests/test_folder_scanner.py`

**Interfaces:**
- Consumes: Standard library `os`, `pathlib`, `re`.
- Produces:
  - `scan_local_folder(folder_path: str) -> dict` returning:
    - `name: str` (derived from folder or readme title)
    - `path: str`
    - `readme_content: Optional[str]`
    - `technologies: List[str]`
    - `code_snippets: List[dict]` (samples of main files for AI summary if no README)
    - `internal_repos: List[dict]` (subdirectories containing `.git` with remote URL and name)

- [ ] **Step 1: Write failing tests for folder scanner with temporary directories**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement folder_scanner.py skipping heavy folders (.venv, node_modules, .git)**
- [ ] **Step 4: Run test to verify it passes**

---

### Task 3: Gemini Service for Project Summaries and Repository Matching

**Files:**
- Modify: `backend/app/gemini_service.py`
- Test: `tests/test_project_matching.py`

**Interfaces:**
- Consumes: `_call_gemini_api`
- Produces:
  - `async generate_project_summary_from_code(project_name: str, technologies: list[str], code_snippets: list[dict], api_key: Optional[str] = None) -> str`
  - `async match_repo_with_projects(repo_name: str, repo_description: str, repo_use_cases: list[str], projects: list[ProjectModel], api_key: Optional[str] = None) -> List[dict]`
    returns list of `{project_id: int, project_name: str, relevance_explanation: str}`

- [ ] **Step 1: Write failing tests for code summarization and project matching**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement Gemini prompt methods in gemini_service.py**
- [ ] **Step 4: Run test to verify it passes**

---

### Task 4: FastAPI Endpoints for My Projects & Matching

**Files:**
- Modify: `backend/app/main.py`
- Test: `tests/test_my_projects_api.py`

**Interfaces:**
- Produces:
  - `POST /api/my-projects/scan` -> takes `{"folder_path": "..."}`, returns scanned metadata
  - `POST /api/my-projects` -> saves project, triggers retroactive match against existing repos
  - `GET /api/my-projects` -> lists all projects
  - `GET /api/my-projects/{id}` -> returns project and its recommendations
  - `PATCH /api/my-projects/{id}` -> updates notes and status
  - `POST /api/my-projects/{id}/refresh` -> re-scans folder preserving notes and status
  - `POST /api/my-projects/{id}/find-recommendations` -> triggers retroactive search against existing repos
  - `POST /api/analyze` -> enriched to return `project_matches`

- [ ] **Step 1: Write failing tests for My Projects endpoints**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement endpoints in main.py**
- [ ] **Step 4: Run test to verify it passes**

---

### Task 5: Frontend UI for "Os Meus Projetos" and Match Display

**Files:**
- Modify: `backend/static/index.html`
- Modify: `backend/static/app.js`
- Modify: `backend/static/style.css`

**Features:**
- Add "Os Meus Projetos" tab to header.
- Add project list view with status filter (*Todos*, *Em Desenvolvimento*, *Concluído*).
- "Adicionar Projeto" button opening a modal to scan a local directory.
- Preview card in modal showing detected README / AI summary, technologies, and internal repos detected with checkboxes.
- Project detail view showing technologies, notes editor, and list of recommended GitHub repos.
- In **Analisador**: display a highlighted card "Utilidade para os teus Projetos" when a GitHub repo matches one of Tiago's projects.

- [ ] **Step 1: Update index.html with tab pane, modal, and match container**
- [ ] **Step 2: Update app.js with project management and matching render logic**
- [ ] **Step 3: Test responsive layout and manual verification**

---

### Task 6: Full Integration and Verification

- [ ] **Step 1: Run full automated pytest suite**
- [ ] **Step 2: Verify launcher.py and frontend endpoints**
- [ ] **Step 3: Update README.md with documentation for the new feature**
