import os
import sys
import subprocess

def open_folder_picker(initial_dir: str = None) -> str:
    """
    Abre o diálogo nativo do Windows em primeiro plano (TopMost).
    Retorna o caminho da pasta selecionada.
    """
    default_dir = initial_dir if (initial_dir and os.path.exists(initial_dir)) else r"D:\AI Projects"
    if not os.path.exists(default_dir):
        default_dir = os.getcwd()

    ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$f = New-Object System.Windows.Forms.FolderBrowserDialog
$f.Description = "Seleciona a pasta do projeto"
$f.SelectedPath = "{default_dir}"
$f.ShowNewFolderButton = $false
$topForm = New-Object System.Windows.Forms.Form
$topForm.TopMost = $true
if ($f.ShowDialog($topForm) -eq [System.Windows.Forms.DialogResult]::OK) {{
    Write-Output $f.SelectedPath
}}
"""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=120
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass

    return ""
