@echo off
title AI Toolbox - Acesso Remoto (Cloudflare Tunnel)
color 0b
echo ===================================================
echo     AI TOOLBOX - ACESSO REMOTO SEGURO
echo ===================================================
echo.
echo A iniciar o tunel Cloudflare seguro...
echo O teu link publico HTTPS estara pronto em segundos.
echo.

"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:8000

pause
