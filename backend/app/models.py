from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ProjectMatchResult(BaseModel):
    project_id: int
    project_name: str
    relevance_explanation: str

class RepoModel(BaseModel):
    id: Optional[int] = None
    url: str
    name: str
    owner: str
    description_simple: str
    use_cases: List[str] = Field(default_factory=list)
    category: str = "Geral"
    is_favorite: bool = False
    is_cloned: bool = False
    local_path: Optional[str] = None
    created_at: Optional[str] = None
    project_matches: List[ProjectMatchResult] = Field(default_factory=list)

class AnalysisRequest(BaseModel):
    url: str

class CategoryUpdateRequest(BaseModel):
    category: str

class ProjectModel(BaseModel):
    id: Optional[int] = None
    name: str
    path: str
    summary: str
    status: str = "em_desenvolvimento"  # em_desenvolvimento, em_pausa, concluido
    technologies: List[str] = Field(default_factory=list)
    notes: Optional[str] = ""
    created_at: Optional[str] = None

class ProjectUpdateRequest(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    summary: Optional[str] = None
    technologies: Optional[List[str]] = None

class ProjectScanRequest(BaseModel):
    path: str

class ProjectScanResult(BaseModel):
    name: str
    path: str
    summary: str
    technologies: List[str] = Field(default_factory=list)
    internal_repos: List[Dict[str, Any]] = Field(default_factory=list)

class ProjectRecommendationModel(BaseModel):
    id: Optional[int] = None
    project_id: int
    repo_id: int
    reason: str
    repo_name: Optional[str] = None
    repo_url: Optional[str] = None
    repo_category: Optional[str] = None
    created_at: Optional[str] = None

class LocalRepoScanRequest(BaseModel):
    folder: Optional[str] = None

class LocalRepoScanItem(BaseModel):
    name: str
    path: str
    remote_url: str = ""
    has_readme: bool = False
    is_cataloged: bool = False
    catalog_id: Optional[int] = None

class LocalRepoImportRequest(BaseModel):
    name: str
    path: str
    remote_url: Optional[str] = ""
    auto_analyze: bool = False

class OpenPathRequest(BaseModel):
    path: str

class LocalRepoBatchImportRequest(BaseModel):
    repos: List[LocalRepoImportRequest]

class LinkRepoRequest(BaseModel):
    repo_id: int

class CloneUrlRequest(BaseModel):
    url: str
    name: Optional[str] = None
    owner: Optional[str] = None
    description: Optional[str] = ""

class PromptModel(BaseModel):
    id: Optional[int] = None
    act: str
    prompt: str
    category: Optional[str] = "Geral"
    source: Optional[str] = "personalizado"  # "personalizado" ou "prompts.chat"
    target_model: Optional[str] = "ChatGPT"  # ChatGPT, Claude, Gemini, DeepSeek, Llama
    created_at: Optional[str] = None

class PromptCreateRequest(BaseModel):
    act: str
    prompt: str
    category: Optional[str] = "Geral"
    source: Optional[str] = "personalizado"
    target_model: Optional[str] = "ChatGPT"

class PromptUpdateRequest(BaseModel):
    act: Optional[str] = None
    prompt: Optional[str] = None
    category: Optional[str] = None
    target_model: Optional[str] = None

class PromptConvertRequest(BaseModel):
    prompt_text: str
    act: Optional[str] = "Prompt"
    current_model: Optional[str] = "ChatGPT"
    target_model: str  # "Claude 3.7 / 3.5 Sonnet", "ChatGPT (GPT-4o)", "Google Gemini 2.5", "DeepSeek-V3 / R1", "Meta Llama 3"

class SkillModel(BaseModel):
    id: str
    name: str
    description: str
    program: str = "Google Antigravity"
    source: str = "Antigravity (Personalizado)"
    plugin: Optional[str] = None
    directory: Optional[str] = ""
    file_path: Optional[str] = ""
    target_model: str = "Claude"
    is_custom: bool = True
    content: Optional[str] = None
    created_at: Optional[str] = None

class SkillCreateRequest(BaseModel):
    name: str
    description: str
    content: str
    target_model: Optional[str] = "Claude"
    program: Optional[str] = "Google Antigravity"

class SkillUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    target_model: Optional[str] = None
    file_path: Optional[str] = None

class SkillConvertRequest(BaseModel):
    skill_content: str
    skill_name: Optional[str] = "Skill"
    current_model: Optional[str] = "Claude"
    target_model: str

class MediaExtractRequest(BaseModel):
    url: str

class MediaProcessRequest(BaseModel):
    url: str
    download_video: bool = True

class MediaItemModel(BaseModel):
    id: int
    url: str
    title: str
    author: Optional[str] = ""
    description: Optional[str] = ""
    summary_ai: Optional[str] = ""
    category: Optional[str] = "Geral"
    thumbnail_url: Optional[str] = ""
    media_type: Optional[str] = "video"
    local_file_path: Optional[str] = ""
    file_size_bytes: Optional[int] = 0
    duration_seconds: Optional[int] = 0
    source: Optional[str] = "Facebook"
    created_at: Optional[str] = None




