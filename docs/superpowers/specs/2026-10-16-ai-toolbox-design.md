# AI Toolbox - Documento de Design

**Data:** 2026-10-16  
**Autor:** Tiago & Antigravity  
**Estado:** Implementado & Em Produção  

---

## 1. Contexto e Motivação (Intent & Why)

O Tiago está a iniciar-se em programação e tecnologia. Ao explorar projetos e ferramentas de inteligência artificial, encontrava frequentemente documentação densa e técnica, tornando moroso perceber o que cada ferramenta faz. Além disso, acumulavam-se repositórios, prompts e ficheiros no computador sem uma organização unificada.

A **AI Toolbox** é uma aplicação web local criada para resolver este desafio:
1. Traduzir e descomplicar repositórios do GitHub com explicações claras em português simples e exemplos práticos de uso.
2. Permitir guardar ferramentas como favoritas ou descarregá-las/instalá-las no computador com um clique.
3. Organizar os repositórios por tipos e categorias sugeridas pela inteligência artificial.
4. Manter todo o histórico guardado localmente em SQLite para consulta offline rápida.
5. Mapear os projetos em desenvolvimento no disco do computador e cruzar ferramentas compatíveis.
6. Gerir uma biblioteca própria de Prompts otimizados e Skills para agentes autónomos.
7. Extrair e descarregar multimédia do Facebook e redes sociais com resumo por IA e reprodução no iPhone.

---

## 2. Objetivos Principais

- **Analisador de Repositórios:** Campo simples para inserir qualquer ligação do GitHub. A aplicação consulta o repositório e a IA do Google Gemini gera um resumo estruturado.
- **Explicação Clara e Acessível:** Produzir uma descrição em português europeu corrente, com arquitetura de ficheiros, ciclo operacional e requisitos.
- **Categorização Automática:** A IA sugere categorias com possibilidade de edição direta.
- **Ações Imediatas:** Download via Git clone para o PC e marcação de favoritos.
- **Armazenamento e Histórico Local:** Persistência em SQLite (`repos.db`).
- **Sincronização Móvel (PWA & iPhone):** Acesso local via Wi-Fi e remoto via túnel Cloudflare seguro.
- **Estúdio de Prompts e Skills:** Biblioteca de prompts, conversão entre modelos (Claude, Gemini, ChatGPT, DeepSeek) e descoberta de skills instalados.
- **Extrator de Média:** Suporte a vídeos do Facebook com streaming iOS Safari (Range Requests).

---

## 3. Arquitetura Técnica

- **Backend:** Python com FastAPI e Uvicorn.
- **Base de Dados:** SQLite local (`repos.db`).
- **Frontend:** HTML5 semântico, Tailwind CSS, FontAwesome e JavaScript Vanilla com suporte PWA.
- **Integração de IA:** Google Gemini API (modelos rápidos como Gemini Flash e Flash-Lite).
- **Extrator de Multimédia:** `yt-dlp` em Python para descarregar vídeos em `.mp4`.
