import os
import pytest
from backend.app.git_service import clone_repository, get_default_download_dir

def test_clone_repository_existing_dir(tmp_path, monkeypatch):
    existing_repo = tmp_path / "fastapi_fastapi"
    existing_repo.mkdir()

    success, path, msg = clone_repository("https://github.com/fastapi/fastapi", target_dir=str(tmp_path))
    assert success is True
    assert "já existe" in msg
    assert str(existing_repo) == path

def test_clone_repository_success(tmp_path, monkeypatch):
    called = []
    def mock_run(cmd, *args, **kwargs):
        called.append(cmd)
        target = cmd[-1]
        os.makedirs(target, exist_ok=True)
        class Completed:
            returncode = 0
            stderr = ""
            stdout = "Cloning into..."
        return Completed()

    import subprocess
    monkeypatch.setattr(subprocess, "run", mock_run)

    success, path, msg = clone_repository("https://github.com/psf/requests", target_dir=str(tmp_path))
    assert success is True
    assert len(called) == 1
    assert "git" in called[0][0]
    assert "Clonado com sucesso" in msg

def test_clone_repository_failure(tmp_path, monkeypatch):
    def mock_run(cmd, *args, **kwargs):
        class Completed:
            returncode = 128
            stderr = "fatal: repository not found"
            stdout = ""
        return Completed()

    import subprocess
    monkeypatch.setattr(subprocess, "run", mock_run)

    success, path, msg = clone_repository("https://github.com/tiago/nonexistent", target_dir=str(tmp_path))
    assert success is False
    assert "Erro ao clonar" in msg

def test_check_git_updates_invalid_folder(tmp_path):
    from backend.app.git_service import check_git_updates
    has_updates, msg, count = check_git_updates(str(tmp_path))
    assert has_updates is False
    assert count == 0
    assert "não é um repositório Git válido" in msg

def test_check_git_updates_success_with_updates(tmp_path, monkeypatch):
    from backend.app.git_service import check_git_updates
    (tmp_path / ".git").mkdir()

    import subprocess
    def mock_run(cmd, *args, **kwargs):
        class Completed:
            returncode = 0
            stderr = ""
            stdout = "3\n" if "rev-list" in cmd else ""
        return Completed()

    monkeypatch.setattr(subprocess, "run", mock_run)

    has_updates, msg, count = check_git_updates(str(tmp_path))
    assert has_updates is True
    assert count == 3
    assert "3 atualizações disponíveis" in msg

def test_pull_repository_success(tmp_path, monkeypatch):
    from backend.app.git_service import pull_repository
    (tmp_path / ".git").mkdir()

    import subprocess
    def mock_run(cmd, *args, **kwargs):
        class Completed:
            returncode = 0
            stderr = ""
            stdout = "Updating 1234..5678\nFast-forward\n"
        return Completed()

    monkeypatch.setattr(subprocess, "run", mock_run)

    success, msg = pull_repository(str(tmp_path))
    assert success is True
    assert "Atualizado com sucesso" in msg
