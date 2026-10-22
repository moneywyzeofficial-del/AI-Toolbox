import os
import subprocess
from typing import Tuple

def create_project_shortcut(target_dir: str, destination_dir: str, shortcut_name: str) -> Tuple[bool, str]:
    """
    Cria um atalho (.lnk) na pasta destination_dir a apontar para target_dir.
    No Windows, utiliza o WScript.Shell através do PowerShell.
    Em sistemas Unix, cria um symlink.
    """
    if not os.path.exists(target_dir):
        return False, f"A pasta de destino não existe: {target_dir}"
    if not os.path.exists(destination_dir):
        return False, f"A pasta do projeto não existe: {destination_dir}"

    clean_name = shortcut_name.strip()
    if not clean_name.lower().endswith(".lnk") and os.name == "nt":
        clean_name += ".lnk"

    shortcut_file = os.path.join(destination_dir, clean_name)

    try:
        if os.name == "nt":
            ps_script = (
                f'$WshShell = New-Object -ComObject WScript.Shell; '
                f'$Shortcut = $WshShell.CreateShortcut("{shortcut_file}"); '
                f'$Shortcut.TargetPath = "{target_dir}"; '
                f'$Shortcut.Description = "Atalho para o repositorio partilhado {os.path.basename(target_dir)}"; '
                f'$Shortcut.Save()'
            )
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                check=False,
                timeout=10
            )
            if res.returncode == 0 and os.path.exists(shortcut_file):
                return True, shortcut_file
            else:
                err = res.stderr.strip() or res.stdout.strip()
                return False, f"Erro ao criar atalho no Windows: {err}"
        else:
            symlink_path = os.path.join(destination_dir, shortcut_name)
            if os.path.islink(symlink_path) or os.path.exists(symlink_path):
                os.remove(symlink_path)
            os.symlink(target_dir, symlink_path)
            return True, symlink_path
    except Exception as e:
        return False, f"Falha ao criar atalho: {str(e)}"

def remove_project_shortcut(shortcut_path: str) -> bool:
    """
    Remove o ficheiro de atalho se existir.
    """
    try:
        if shortcut_path and os.path.exists(shortcut_path):
            os.remove(shortcut_path)
            return True
        return False
    except Exception:
        return False
