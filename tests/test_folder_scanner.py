import os
import pytest
from backend.app.folder_scanner import scan_local_folder

def test_scan_folder_with_readme(tmp_path):
    proj_dir = tmp_path / "MyProject"
    proj_dir.mkdir()
    readme = proj_dir / "README.md"
    readme.write_text("# My Awesome Project\nThis is a cool tool for garden automation.", encoding="utf-8")
    
    # Add a python file
    py_file = proj_dir / "main.py"
    py_file.write_text("print('hello')", encoding="utf-8")

    result = scan_local_folder(str(proj_dir))
    assert result["name"] == "MyProject"
    assert "garden automation" in result["readme_content"]
    assert "Python" in result["technologies"]
    assert len(result["internal_repos"]) == 0

def test_scan_folder_without_readme(tmp_path):
    proj_dir = tmp_path / "BotTelegram"
    proj_dir.mkdir()
    
    # Add js files and package.json
    pkg = proj_dir / "package.json"
    pkg.write_text('{"name": "bot", "dependencies": {"express": "4.18"}}', encoding="utf-8")
    js_file = proj_dir / "index.js"
    js_file.write_text("const express = require('express');", encoding="utf-8")

    result = scan_local_folder(str(proj_dir))
    assert result["name"] == "BotTelegram"
    assert result["readme_content"] is None
    assert "JavaScript" in result["technologies"]
    assert "Node.js" in result["technologies"]
    assert len(result["code_snippets"]) > 0

def test_scan_folder_detects_internal_repo(tmp_path):
    proj_dir = tmp_path / "MainApp"
    proj_dir.mkdir()
    
    # Internal sub-repo
    sub_dir = proj_dir / "modules" / "subtool"
    sub_dir.mkdir(parents=True)
    git_dir = sub_dir / ".git"
    git_dir.mkdir()
    config_file = git_dir / "config"
    config_file.write_text('[remote "origin"]\n\turl = https://github.com/coolauthor/subtool.git\n', encoding="utf-8")

    result = scan_local_folder(str(proj_dir))
    assert len(result["internal_repos"]) == 1
    assert result["internal_repos"][0]["name"] == "subtool"
    assert "github.com/coolauthor/subtool" in result["internal_repos"][0]["url"]

def test_scan_nonexistent_folder():
    with pytest.raises(FileNotFoundError):
        scan_local_folder("C:\\caminho\\que\\nao\\existe_123456")
