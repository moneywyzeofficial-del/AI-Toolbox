# GitHub Repo Organizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local web application that analyzes GitHub repositories, explains them in plain European Portuguese with practical use cases via Google Gemini, categorizes them, saves all data to a local SQLite database, and provides options to favorite or clone the repo locally.

**Architecture:** Python backend using FastAPI serving a clean HTML/JS/CSS frontend. The backend fetches GitHub repo metadata & README via the GitHub public API, invokes Gemini to generate plain-language explanations, use cases, and categories, stores records in SQLite, and clones repos via the local Git CLI into a dedicated projects directory.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, httpx, google-genai / google-generativeai, SQLite3, pytest, HTML5/TailwindCSS (via CDN), JavaScript.

**Spec:** [docs/superpowers/specs/2026-10-16-github-repo-organizer-design.md](file:///d:/AI%20Projects/Github%20Repo%20Organizer/docs/superpowers/specs/2026-10-16-github-repo-organizer-design.md)

## Global Constraints

- Platform: Windows (Python 3.12, Git installed).
- Language and Tone: Plain European Portuguese for user-facing outputs and explanations, avoiding unnecessary jargon.
- Offline Availability: Persist all analysis results in local SQLite so past queries are always accessible offline without re-calling APIs.
- Clones Directory: Default local directory for cloned repositories at `d:\AI Projects\Downloaded_Repos`.
- Git commits: Never commit automatically without explicit user request, as per user global preferences.

## Review Focus

1. Invalid or malformed GitHub URLs (e.g., non-GitHub domain, missing owner/repo) -> return clean 400 with user-friendly error in Portuguese.
2. Non-existent or private GitHub repositories (404 from GitHub) -> return clear explanation that the repo is private or does not exist.
3. Repositories without a README or with an empty README -> Gemini should synthesize an explanation based on name, description, and topics rather than failing.
4. Clone destination directory already exists -> avoid crashing or corrupting files; return friendly status that repo is already cloned.
5. Missing or invalid Gemini API key -> clear error message instructing how to set GEMINI_API_KEY.

---

### Task 1: Project Setup and SQLite Database Layer

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/db.py`
- Create: `backend/app/models.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Consumes: Standard library `sqlite3`, `pydantic`.
- Produces:
  - `init_db(db_path: str = "repos.db") -> None`
  - `save_repository(repo: RepoModel, db_path: str = "repos.db") -> int`
  - `get_repository(repo_id: int, db_path: str = "repos.db") -> Optional[RepoModel]`
  - `list_repositories(category: Optional[str] = None, favorites_only: bool = False, db_path: str = "repos.db") -> List[RepoModel]`
  - `toggle_favorite(repo_id: int, db_path: str = "repos.db") -> bool`
  - `update_repo_category(repo_id: int, new_category: str, db_path: str = "repos.db") -> bool`
  - `mark_as_cloned(repo_id: int, local_path: str, db_path: str = "repos.db") -> bool`

- [ ] **Step 1: Write requirements.txt and failing tests for the database layer**

Create `tests/test_db.py` testing database initialization, saving a repository analysis, querying repositories, filtering by category and favorite, and toggling favorite status.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_db.py -v`
Expected: FAIL (modules not found)

- [ ] **Step 3: Implement models.py and db.py**

Create `backend/app/models.py` with `RepoModel` (id, url, name, owner, description_simple, use_cases, category, is_favorite, is_cloned, local_path, created_at).
Implement SQLite schema and CRUD methods in `backend/app/db.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_db.py -v`
Expected: PASS

---

### Task 2: GitHub Metadata and README Service

**Files:**
- Create: `backend/app/github_service.py`
- Test: `tests/test_github_service.py`

**Interfaces:**
- Consumes: `httpx`.
- Produces:
  - `parse_github_url(url: str) -> Tuple[str, str]` (extracts owner, repo)
  - `async fetch_repo_data(owner: str, repo: str) -> dict` (returns name, full_name, description, stars, topics, readme_content)

- [ ] **Step 1: Write the failing tests for GitHub service**

Create `tests/test_github_service.py` with tests for:
- Parsing valid URLs (`https://github.com/owner/repo`, `https://github.com/owner/repo/`)
- Handling invalid URLs (raises `ValueError`)
- Mocked HTTP requests for fetching repo info and base64-decoded README.
- Handling repositories without README.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_github_service.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement github_service.py**

Implement `parse_github_url` regex and async `fetch_repo_data` using `httpx.AsyncClient` with GitHub REST API headers (`Accept: application/vnd.github.v3+json`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_github_service.py -v`
Expected: PASS

---

### Task 3: Gemini Analysis Service (Explanations & Categorization)

**Files:**
- Create: `backend/app/gemini_service.py`
- Test: `tests/test_gemini_service.py`

**Interfaces:**
- Consumes: `google-genai` or standard HTTP client with Gemini API key.
- Produces:
  - `async analyze_repo_content(repo_name: str, repo_description: str, topics: list[str], readme_text: str, api_key: Optional[str] = None) -> AnalysisResult`
  where `AnalysisResult` has `description_simple: str`, `use_cases: list[str]`, and `category: str`.

- [ ] **Step 1: Write the failing tests for Gemini service**

Create `tests/test_gemini_service.py` with tests mocking the Gemini API response to ensure structured output parsing (description in Portuguese, list of practical use cases, category).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_gemini_service.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement gemini_service.py**

Create structured prompt instructing Gemini to:
1. Explain what the project is in clear, simple European Portuguese for someone learning technology.
2. Provide 2-3 concrete practical use case scenarios.
3. Suggest a concise category (e.g. "Ferramentas", "Inteligência Artificial", "Automação", "Web", "Utilitários").
Parse JSON response safely.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_gemini_service.py -v`
Expected: PASS

---

### Task 4: Local Git Clone Service

**Files:**
- Create: `backend/app/git_service.py`
- Test: `tests/test_git_service.py`

**Interfaces:**
- Consumes: Python `subprocess` / `asyncio.subprocess` and `os`.
- Produces:
  - `clone_repository(repo_url: str, target_dir: str = "d:\\AI Projects\\Downloaded_Repos") -> Tuple[bool, str]`

- [ ] **Step 1: Write the failing tests for Git clone service**

Create `tests/test_git_service.py` testing successful clone command invocation (mocked), existing target directory handling, and error handling.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_git_service.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement git_service.py**

Implement `clone_repository` ensuring target folder exists, executing `git clone <url> <path>` safely, and checking if destination directory already exists.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_git_service.py -v`
Expected: PASS

---

### Task 5: FastAPI Backend Endpoints

**Files:**
- Create: `backend/app/main.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `db.py`, `github_service.py`, `gemini_service.py`, `git_service.py`.
- Produces:
  - `POST /api/analyze` (receives `{"url": "..."}`, returns analysis and saves to DB)
  - `GET /api/repos` (supports `?category=...&favorites_only=...`)
  - `POST /api/repos/{id}/favorite` (toggles favorite)
  - `POST /api/repos/{id}/clone` (executes clone to local PC)
  - `PATCH /api/repos/{id}/category` (updates category)
  - Serves static files for frontend.

- [ ] **Step 1: Write failing tests for FastAPI routes**

Create `tests/test_api.py` using `fastapi.testclient.TestClient` to test the API endpoints with mocked external services.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py -v`
Expected: FAIL

- [ ] **Step 3: Implement main.py routes**

Assemble all services into clean, RESTful FastAPI routes with proper error handling and static files mounting.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api.py -v`
Expected: PASS

---

### Task 6: Frontend Web Interface

**Files:**
- Create: `backend/static/index.html`
- Create: `backend/static/app.js`
- Create: `backend/static/style.css`

**Features:**
- Header with tabs:
  1. **Analisador**: Input URL, loading state, formatted cards with Simple Description, Practical Use Cases, Category tag, and action buttons ("Adicionar ao Computador", "Favorito").
  2. **Histórico e Favoritos**: Filter by category, toggle "Apenas Favoritos", view cards, update category, and trigger clone.
  3. **Repositórios no PC (Fase 2 - Prévia)**: View repos that have been cloned locally with folder paths.

- [ ] **Step 1: Create HTML structure with tabs and Tailwind UI**
- [ ] **Step 2: Implement app.js client logic** (API calls, reactive DOM rendering, toast notifications)
- [ ] **Step 3: Manual end-to-end verification via browser testing**
- [ ] **Step 4: Verify all styling and Portuguese copy consistency**

---

### Task 7: Runner Script and Documentation

**Files:**
- Create: `run.bat` (one-click runner for Windows)
- Create: `README.md` (simple instructions in Portuguese on how to start the app)

- [ ] **Step 1: Create `run.bat` that checks Python, installs dependencies if missing, and starts Uvicorn**
- [ ] **Step 2: Create clear `README.md`**
- [ ] **Step 3: Execute full end-to-end verification**
