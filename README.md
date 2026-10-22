# AI Toolbox

Plataforma integrada de IA e desenvolvimento web para organizar repositórios, projetos locais de código, biblioteca de prompts, skills para agentes autónomos e extração de multimédia. Criada com foco na usabilidade em PC (Windows) e em dispositivos móveis (iPhone / PWA).

---

## Funcionalidades Principais

### 1. Início & Painel Central (Dashboard)
- **Métricas em Tempo Real:** Visualização rápida do número de repositórios catalogados, projetos locais no PC, prompts criados, skills ativos e vídeos guardados.
- **Ações Rápidas:** Acesso imediato para analisar repositórios, criar novos prompts, registar novos skills ou adicionar pastas locais com um só clique.

### 2. Hub de Recursos & Analisador de Repositórios
- **Analisador com Google Gemini:** Cola qualquer ligação do GitHub para obter uma explicação detalhada em português direto (introdução clara, ciclo de funcionamento, arquitetura de ficheiros e requisitos).
- **Catálogo Organizado:** Filtros por categoria, favoritos e pesquisa rápida com persistência local em SQLite (`repos.db`).
- **Repositórios no Computador:** Varredura automática do disco para detetar projetos Git locais, sincronização com o catálogo, `git pull` direto da interface e atalhos para abrir no Explorador ou VS Code.
- **Tendências Mundiais:** Exploração em tempo real dos repositórios mais populares do GitHub e dos melhores modelos/espaços do Hugging Face.

### 3. Facebook & Extrator de Multimédia
- **Fluxo Otimizado para iPhone:** Botão "Colar" de um toque para inserir ligações copiadas na app do Facebook ou Safari.
- **Download Automatizado:** Descarregamento local de vídeos em `.mp4` através de `yt-dlp` para visualização offline sem gastar dados móveis.
- **Resumo por IA:** Extração automática de pontos-chave e categorização inteligente (Jardinagem, Piscinas, Tecnologia, Humor, Geral).
- **Player Integrado (iOS Safari):** Streaming com suporte completo a *HTTP 206 Range Requests* e `playsinline`.

### 4. Os Meus Projetos & Cruzamento Inteligente
- **Espaço de Trabalho:** Gestão dos teus projetos de software locais com acompanhamento de estado (*em desenvolvimento*, *ativo*, *em pausa*, *concluído*) e notas pessoais.
- **Resumo Automático de Código:** Se o projeto não tiver README, o Gemini analisa os ficheiros-chave de código e gera a ficha técnica do projeto.
- **Cruzamento Bidirecional:** A IA analisa os teus projetos e cruza-os com a tua biblioteca de ferramentas do GitHub, sugerindo dependências e integrações ideais.

### 5. Estúdio de Prompts (Prompt Studio)
- **Biblioteca Pessoal:** Criação, edição e organização de prompts estruturados com categorização e contadores.
- **Conversor entre Modelos de IA:** Converte qualquer prompt para a sintaxe e melhores práticas de modelos específicos (Claude 3.7 / 3.5 Sonnet, ChatGPT GPT-4o, Google Gemini 2.5, DeepSeek-R1 / V3, Meta Llama 3).

### 6. Gestão de Skills para Agentes
- **Descoberta Automática:** Deteção de skills instalados no ecossistema **OpenCode** e **Google Antigravity**.
- **Criador de Skills:** Cria novos skills compatíveis (`SKILL.md`) com escolha do modelo recomendado.
- **Conversão de Skills:** Adaptação de instruções de skills entre formatos de diferentes agentes e modelos.

### 7. Sincronização Móvel & Acesso Remoto
- **Ligar ao iPhone (Wi-Fi Local):** Geração de código QR na app para abrir imediatamente no Safari do iPhone na mesma rede.
- **Acesso Remoto Seguro (Cloudflare Tunnel):** Script `Ativar Acesso Remoto.bat` incluído para acederes à aplicação fora de casa em qualquer rede móvel sem necessidade de abrir portas no router.

---

## Instalação e Execução

### Pré-requisitos
- Python 3.10 ou superior
- Git (opcional, para clonagem direta de repositórios)

### Instalação Rápida

1. Clona este repositório:
   ```bash
   git clone https://github.com/teu-utilizador/ai-toolbox.git
   cd ai-toolbox
   ```

2. Cria um ambiente virtual e instala as dependências:
   ```bash
   python -m venv venv
   # No Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # Instalar dependências:
   pip install -r requirements.txt
   ```

3. Configura a tua chave de API do Gemini (opcional, mas recomendada):
   ```bash
   copy .env.example .env
   # Edita o ficheiro .env e adiciona a tua GEMINI_API_KEY
   ```

4. Inicia a aplicação:
   - **No Windows:** basta dar duplo clique em `run.bat` ou executar:
     ```bash
     python launcher.py
     ```
   - **Via Uvicorn:**
     ```bash
     python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
     ```

5. Abre o navegador em `http://localhost:8000`.

---

## Testes Automatizados

O projeto inclui uma suite de 68 testes unitários que cobrem a base de dados SQLite, scanners, rotas de API, gestão de média e serviços de IA:

```bash
pytest
```

---

## Estrutura do Projeto

```text
├── backend/
│   ├── app/
│   │   ├── main.py              # API FastAPI e rotas principais
│   │   ├── db.py                # Camada SQLite (repositórios, projetos, prompts, média)
│   │   ├── models.py            # Schemas Pydantic
│   │   ├── gemini_service.py    # Integração com Google Gemini
│   │   ├── media_service.py     # Download e extração com yt-dlp
│   │   ├── git_service.py       # Gestão Git local
│   │   ├── folder_scanner.py    # Leitura e análise de pastas
│   │   ├── local_scanner.py     # Varredura de repositórios no PC
│   │   ├── skills_scanner.py    # Deteção de skills de agentes
│   │   ├── shortcut_service.py  # Gestão de atalhos e ligações
│   │   └── trending_service.py  # Feed de tendências GitHub e Hugging Face
│   └── static/                  # Interface Web PWA (HTML, Tailwind CSS, JS, ícones)
├── tests/                       # Testes unitários com pytest (68 testes)
├── docs/                        # Especificações e planos de arquitetura
├── .env.example                 # Exemplo de configuração de variáveis de ambiente
├── .gitignore                   # Exclusão de segredos, caches e bases de dados
├── DESIGN.md                    # Especificação de design visual e UI/UX
├── launcher.py                  # Script de arranque com verificação de ambiente
├── run.bat                      # Executável de arranque com 1 clique para Windows
├── Ativar Acesso Remoto.bat     # Ativação de túnel Cloudflare para acesso no iPhone
├── requirements.txt             # Dependências do projeto
└── README.md                    # Documentação do projeto
```

---

## Licença

Distribuído sob a Licença MIT. Consulta o ficheiro [LICENSE](LICENSE) para mais informações.
