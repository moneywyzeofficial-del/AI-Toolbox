import os
import shutil
import tempfile
import pytest
from backend.app.local_scanner import get_git_remote_url, scan_installed_repositories

def test_get_git_remote_url_empty_when_no_git():
    with tempfile.TemporaryDirectory() as tmpdir:
        url = get_git_remote_url(tmpdir)
        assert url == ""

def test_get_git_remote_url_normalization(monkeypatch):
    import subprocess
    def mock_check_output(cmd, cwd, text, stderr):
        return "git@github.com:openai/whisper.git\n"

    monkeypatch.setattr(subprocess, "check_output", mock_check_output)
    url = get_git_remote_url("dummy")
    assert url == "https://github.com/openai/whisper"

def test_scan_installed_repositories_non_existent():
    res = scan_installed_repositories("C:\\pasta_que_nao_existe_12345")
    assert res == []

def test_scan_installed_repositories_finds_repos(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        # Criar repo A
        repo_a = os.path.join(tmpdir, "ProjectA")
        os.makedirs(os.path.join(repo_a, ".git"))
        with open(os.path.join(repo_a, "README.md"), "w", encoding="utf-8") as f:
            f.write("# Project A\nDescricao de teste.")

        # Criar repo B dentro de uma subpasta
        sub = os.path.join(tmpdir, "apps")
        repo_b = os.path.join(sub, "ProjectB")
        os.makedirs(os.path.join(repo_b, ".git"))

        # Criar pasta que deve ser ignorada (ex: node_modules)
        ignored = os.path.join(tmpdir, "node_modules", "IgnoredRepo")
        os.makedirs(os.path.join(ignored, ".git"))

        def mock_remote(folder):
            if "ProjectA" in folder:
                return "https://github.com/user/ProjectA"
            return ""

        monkeypatch.setattr("backend.app.local_scanner.get_git_remote_url", mock_remote)

        found = scan_installed_repositories(tmpdir, max_depth=2)
        names = [f["name"] for f in found]
        assert "ProjectA" in names
        assert "ProjectB" in names
        assert "IgnoredRepo" not in names

        # Verificar campos do ProjectA
        item_a = next(f for f in found if f["name"] == "ProjectA")
        assert item_a["has_readme"] is True
        assert item_a["remote_url"] == "https://github.com/user/ProjectA"
