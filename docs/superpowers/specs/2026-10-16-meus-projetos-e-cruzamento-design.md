# Documento de Design: Os Meus Projetos e Cruzamento Inteligente

**Data:** 2026-10-16  
**Autor:** Tiago & Antigravity  
**Estado:** Aprovado  

---

## 1. Contexto e Motivação (Intent & Why)

O Tiago desenvolve vários projetos no seu computador e utiliza o GitHub para encontrar ferramentas e bibliotecas que o ajudem a avançar. No entanto, analisar um repositório isoladamente não responde à pergunta fundamental: *"Isto serve para algum dos projetos que eu estou a criar neste momento?"*

Esta funcionalidade expande o **GitHub Repo Organizer** com:
1. Um separador dedicado **«Os Meus Projetos»**, onde o Tiago cataloga os projetos que está a desenvolver no seu computador.
2. Leitura inteligente de pastas locais: extração automática de documentação (`README.md` ou `.md`) ou geração de resumo por IA através da análise do código existente caso não haja documentação.
3. Deteção de tecnologias e identificação de repositórios/módulos internos já instalados na pasta (com confirmação manual do utilizador para adicionar ao catálogo).
4. Ficha de projeto completa com estado (*Em Desenvolvimento*, *Em Pausa*, *Concluído*), tecnologias, repositórios recomendados e bloco de notas para próximos passos.
5. **Cruzamento Inteligente Bidirecional:**
   - **Na página principal:** Sempre que um repositório do GitHub for analisado, a IA compara-o com os projetos do Tiago e indica se tem utilidade e como pode ajudar.
   - **No projeto pessoal:** Ao registar um projeto novo (ou ao clicar em «Procurar no Histórico»), a aplicação avalia os repositórios que o Tiago já tem no catálogo e lista de imediato os que servem para este novo projeto.

*(Nota: O separador para catalogar Skills instaladas no sistema foi registado e fica reservado para a fase seguinte).*

---

## 2. Objetivos, Não-Objetivos e Anti-Objetivos

### Objetivos (Goals)
- **Tabela de Projetos Pessoais (SQLite):** Guardar nome, caminho local, resumo, tecnologias, estado e notas de cada projeto pessoal.
- **Tabela de Recomendações (SQLite):** Guardar a ligação entre projetos e repositórios (`project_id`, `repo_id`, `reason`).
- **Importação por Pasta Local:** Endpoint e interface onde o utilizador indica o caminho de uma pasta no PC (ex: `d:\AI Projects\...`). A aplicação lê a pasta:
  - Se tiver `README.md` (ou outro `.md`), extrai o texto base.
  - Se não tiver documentação, a IA do Gemini lê a estrutura de ficheiros e ficheiros principais para gerar uma descrição acessível.
  - Identifica extensões e ficheiros de configuração (`requirements.txt`, `package.json`, etc.) para listar as tecnologias e linguagens.
  - Deteta se existem pastas com `.git` dentro do projeto. Se tiver remoto do GitHub, prepara a sua adição ao catálogo; se for puramente local, regista localmente após confirmação do utilizador.
- **Ficha Completa de Projeto:**
  - Nome e caminho no disco.
  - Resumo do projeto.
  - Estado do projeto com seleção rápida (*Em Desenvolvimento*, *Em Pausa*, *Concluído*).
  - Badges das tecnologias detetadas.
  - Bloco de notas pessoais / próximos passos (editável e gravado no disco).
  - Lista de repositórios recomendados pela IA para este projeto, com botão para «Procurar Recomendações no Histórico».
  - Botão para «Re-analisar Pasta» (atualiza tecnologias e resumo sem apagar notas nem alterar o estado).
- **Cruzamento no Analisador:**
  - Ao analisar um URL do GitHub, a IA recebe a lista de projetos do Tiago.
  - Se houver relevância para 1 ou mais projetos, o cartão de análise exibe uma secção destacada: **«Utilidade para os teus Projetos»**, com o nome do projeto e a explicação de como o repositório ajuda.
  - Se não houver utilidade direta, a aplicação informa transparentemente que não tem aplicação aos projetos atuais.

### Não-Objetivos (Non-Goals)
- Não adiciona repositórios internos ao catálogo sem que o utilizador carregue explicitamente no botão de confirmação.
- Não altera nem reescreve os ficheiros do projeto local do utilizador.
- Não inclui nesta fase a varredura do ecossistema de Skills (fica para a fase seguinte conforme acordado).

### Anti-Objetivos (Anti-Goals)
- Não falhar a análise de repositórios se o utilizador ainda não tiver nenhum projeto pessoal registado (deve funcionar perfeitamente sem projetos).
- Não inventar falsas utilidades: se um repositório não tiver ligação com nenhum dos projetos do utilizador, a IA deve dizer claramente que não tem utilidade direta identificada.

---

## 3. Restrições (Constraints)

- **Backend:** Python com FastAPI já existente.
- **Base de Dados:** Extensão da base de dados SQLite existente (`repos.db`).
- **Inteligência Artificial:** Google Gemini API utilizando o modelo ativo `gemini-flash-lite-latest`.
- **Idioma:** Todo o conteúdo e explicações geradas devem estar em Português Europeu claro e acessível.

---

## 4. Decisões do Utilizador (User Decisions)

1. **Leitura automática:** A IA lê o código para gerar o resumo caso a pasta não tenha ficheiro README.
2. **Confirmação manual:** Repositórios já instalados dentro da pasta que não estejam no catálogo só são adicionados após clique num botão de confirmação pelo utilizador.
3. **Cruzamento retroativo:** Ao criar um projeto novo, a aplicação procura logo no histórico de repositórios já analisados se algum é útil para ele.
4. **Composição da ficha:** Inclui linguagens/tecnologias, estado do projeto, repositórios úteis recomendados e bloco de notas/próximos passos.
5. **Faseamento:** Foco total nesta etapa para projetos e cruzamento; separador de skills reservado para a fase seguinte.

---

## 5. Âmbito do Construtor (Builder's Scope)

- **Esquema de Base de Dados:**
  - Tabela `my_projects` (`id`, `name`, `path`, `summary`, `status`, `technologies`, `notes`, `created_at`).
  - Tabela `project_recommendations` (`id`, `project_id`, `repo_id`, `reason`, `created_at`).
- **Analisador de Pastas:** Função de varredura segura que percorre o diretório indicado, lê ficheiros de texto/código sem carregar ficheiros binários pesados (`.exe`, `.png`, `node_modules`, etc.), e deteta subdiretórios com `.git` lendo o `origin url`.
- **Endpoints:**
  - `POST /api/my-projects/scan` - analisa uma pasta do disco e devolve prévia de dados e repositórios internos detetados.
  - `POST /api/my-projects` - guarda o projeto e executa o cruzamento retroativo no histórico.
  - `GET /api/my-projects` - lista todos os projetos.
  - `GET /api/my-projects/{id}` - detalhes do projeto e repositórios recomendados.
  - `PATCH /api/my-projects/{id}` - atualiza estado e notas pessoais.
  - `POST /api/my-projects/{id}/refresh` - re-analisa a pasta preservando notas e estado.
  - `POST /api/my-projects/{id}/find-recommendations` - força busca de recomendações no histórico existente.
- **Integração no Frontend:** Novo separador «Os Meus Projetos» na barra de navegação, modal para adicionar pasta com prévia e confirmação, e secção de utilidade no ecrã de análise do GitHub.
