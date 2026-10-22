import os
import sys
import time
import subprocess
import webbrowser
import winreg
import socket
import uvicorn

def is_server_running(host: str = "127.0.0.1", port: int = 8000) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False

def get_standalone_browser_command(url: str):
    """
    Procura navegadores Chromium instalados (Brave, Chrome, Edge)
    para abrir o site como janela de aplicação independente (--app=URL).
    """
    candidates = []

    # 1. Registo do Windows App Paths
    for app_name in ["brave.exe", "chrome.exe", "msedge.exe"]:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{app_name}") as key:
                val = winreg.QueryValue(key, "")
                if val and os.path.exists(val) and val not in candidates:
                    candidates.append(val)
        except Exception:
            pass

    # 2. Caminhos habituais de instalação no Windows
    std_paths = [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for p in std_paths:
        if os.path.exists(p) and p not in candidates:
            candidates.append(p)

    for exe in candidates:
        return [exe, f"--app={url}"]

    return None

def open_app_window(url: str = "http://127.0.0.1:8000"):
    cmd = get_standalone_browser_command(url)
    if cmd:
        try:
            subprocess.Popen(cmd)
            return
        except Exception:
            pass
    webbrowser.open_new(url)

def main():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)

    url = "http://127.0.0.1:8000"

    # Se o servidor já estiver a correr em segundo plano, abre a janela diretamente
    if is_server_running():
        print("=" * 60)
        print("              AI Toolbox - Já em execução!")
        print("=" * 60)
        print(f"\nA abrir a janela da aplicação em: {url}\n")
        open_app_window(url)
        return

    print("=" * 60)
    print("              AI Toolbox - A Iniciar...")
    print("=" * 60)
    print(f"\nAplicação disponível no PC em: {url}")
    print("Para ligar no iPhone: abre o botão 'Ligar ao iPhone'\n")

    # Abrir navegador numa janela à parte dedicada
    import threading
    def delayed_open():
        time.sleep(1.2)
        open_app_window(url)

    threading.Thread(target=delayed_open, daemon=True).start()

    # Iniciar servidor FastAPI
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    main()
