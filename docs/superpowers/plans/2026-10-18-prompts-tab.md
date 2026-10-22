# Separador de Prompts (prompts.chat & Biblioteca Pessoal) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

Implementar uma nova aba/separador "Prompts" na aplicação GitHub Repo Organizer que permite:
1. Explorar os prompts da comunidade do repositório `f/prompts.chat` (com cache local e pesquisa instantânea).
2. Guardar qualquer prompt na biblioteca pessoal com um clique.
3. Criar prompts personalizados a partir do zero.
4. Editar e eliminar os prompts guardados na biblioteca.
5. Copiar prompts com um clique para a área de transferência.

---

## File Structure & Responsibilities

- **`backend/app/models.py`**:
  - `PromptModel`: `id`, `act` (título/papel), `prompt` (conteúdo), `category`, `source` ("prompts.chat" ou "personalizado"), `created_at`.
  - `PromptCreateRequest` e `PromptUpdateRequest`.
- **`backend/app/db.py`**:
  - `CREATE TABLE IF NOT EXISTS prompts`
  - `save_prompt`, `get_prompt`, `list_prompts`, `update_prompt`, `delete_prompt`.
- **`backend/app/prompts_service.py`**:
  - `fetch_community_prompts()`: obtém os prompts de `f/prompts.chat` (via raw CSV ou cache local `data/prompts_chat_cache.json`) para 0-latência offline.
- **`backend/app/main.py`**:
  - `GET /api/prompts/community`: lista prompts da comunidade com suporte a filtro de pesquisa `?search=...`.
  - `GET /api/prompts`: lista prompts guardados na biblioteca do utilizador.
  - `POST /api/prompts`: cria um novo prompt na biblioteca pessoal.
  - `PUT /api/prompts/{prompt_id}`: atualiza um prompt existente.
  - `DELETE /api/prompts/{prompt_id}`: elimina um prompt da biblioteca.
- **`backend/static/index.html`**:
  - Adiciona o botão da aba `Prompts` na barra de navegação superior (`#tab-prompts-btn`).
  - Cria a secção `<section id="tab-prompts">` com duas sub-secções: "A Minha Biblioteca" e "Comunidade (prompts.chat)".
  - Cria o modal de criação/edição de prompt (`#prompt-modal`).
- **`backend/static/app.js`**:
  - Lógica de alternar para a aba `prompts`.
  - `loadCommunityPrompts(search)` e `loadMyPrompts(search)`.
  - `savePromptFromCommunity(act, prompt)`.
  - `openCreatePromptModal()`, `openEditPromptModal(id)`, `handleSavePrompt()`, `deletePromptConfirm(id)`.
  - `copyPromptText(text)`.
- **`tests/test_prompts.py`**:
  - Testes unitários para a base de dados de prompts e endpoints da API FastAPI.

---

## Tasks

- [ ] **Task 1: Modelos e Tabela de Base de Dados para Prompts**
  - Adicionar `PromptModel`, `PromptCreateRequest`, `PromptUpdateRequest` a `backend/app/models.py`.
  - Adicionar tabela `prompts` e funções CRUD em `backend/app/db.py`.
  - Criar testes unitários em `tests/test_prompts_db.py`.

- [ ] **Task 2: Serviço de Prompts da Comunidade (`prompts.chat`)**
  - Criar `backend/app/prompts_service.py` para carregar dados do `prompts.chat` com fallback de cache embutido.
  - Criar endpoints em `backend/app/main.py`:
    - `GET /api/prompts/community`
    - `GET /api/prompts`
    - `POST /api/prompts`
    - `PUT /api/prompts/{prompt_id}`
    - `DELETE /api/prompts/{prompt_id}`
  - Adicionar testes de API em `tests/test_prompts_api.py`.

- [ ] **Task 3: Interface Web (HTML & Modais)**
  - Adicionar a aba "Prompts" na barra de navegação em `backend/static/index.html`.
  - Adicionar a vista da aba `tab-prompts` com tabs secundárias ou grelhas para "Biblioteca Pessoal" e "Comunidade".
  - Adicionar modal para criar/editar prompt.

- [ ] **Task 4: JavaScript da Aplicação (`app.js`)**
  - Implementar em `backend/static/app.js` as funções de carregamento, pesquisa, cópia, criação, edição e eliminação.
  - Testar fluxos de copiar, guardar da comunidade, editar e eliminar.

- [ ] **Task 5: Verificação e Testes Finais**
  - Executar toda a suite de testes pytest.
  - Reiniciar servidor e validar a funcionalidade.
