# GitHub Repo Organizer - Documento de Design

**Data:** 2026-10-16  
**Autor:** Tiago & Antigravity  
**Estado:** Em Revisão  

---

## 1. Contexto e Motivação (Intent & Why)

O Tiago está a iniciar-se em programação e tecnologia. Ao explorar projetos e repositórios no GitHub, encontra frequentemente documentação (README) densa, técnica e de difícil interpretação, tornando moroso perceber se uma ferramenta serve para o que precisa. Além disso, com o tempo, acumulam-se repositórios no computador sem se saber exatamente onde estão guardados ou com que programas/ferramentas estão relacionados.

O **GitHub Repo Organizer** é uma aplicação web local pensada para resolver este problema:
1. Traduzir e descomplicar repositórios do GitHub com explicações em linguagem natural e exemplos práticos de utilização.
2. Permitir guardar o repositório como favorito ou descarregá-lo/instalá-lo no computador com um clique.
3. Organizar os repositórios por tipos/categorias sugeridos pela inteligência artificial.
4. Manter todo o histórico guardado localmente no computador para consulta offline e rápida.
5. (Fase 2) Mapear os projetos e repositórios existentes no disco do computador e identificar as suas ligações.

---

## 2. Objetivos, Não-Objetivos e Anti-Objetivos

### Objetivos (Goals)
- **Analisador de Repositórios:** Campo simples para inserir qualquer URL do GitHub. A aplicação consulta o repositório (metadados e README) e envia à IA do Google Gemini.
- **Explicação Clara e Acessível:** Produzir uma descrição em português europeu corrente, sem jargão desnecessário, acompanhada de exemplos práticos de cenários de uso reais.
- **Categorização Automática:** A IA sugere uma categoria para o projeto (ex.: Ferramentas, Inteligência Artificial, Utilitários, Web, Automação), com possibilidade de edição.
- **Ações Imediatas:**
  - Botão para **Descarregar/Instalar no computador** (clona o repositório via `git clone` para uma pasta de projetos local configurada).
  - Botão para **Adicionar aos Favoritos** (marca e destaca o repositório na lista para consulta futura sem descarregar código).
- **Armazenamento e Histórico Local:** Gravação persistente no computador (ex.: base de dados SQLite local ou ficheiros JSON estruturados). Todas as análises efetuadas ficam disponíveis instantaneamente sem novas chamadas à API.
- **Filtros e Organização:** Possibilidade de filtrar e agrupar projetos por tipo/categoria e consultar favoritos.
- **Interface Intuitiva e Limpa:** Web app local responsiva, moderna e fácil de usar.

### Não-Objetivos (Non-Goals)
- Não é um cliente Git completo (não substitui ferramentas como GitHub Desktop ou comandos de commit/push).
- Não executa automaticamente código não verificado ou comandos desconhecidos do repositório no sistema.
- A Fase 1 não inclui a varredura exaustiva de todo o disco rígido à procura de repositórios perdidos (isso é o foco da Fase 2).

### Anti-Objetivos (Anti-Goals)
- Não gerar respostas técnicas complexas ou em inglês; o utilizador quer explicações simples e fáceis de assimilar.
- Não depender de serviços pagos ou servidores na nuvem externos além da API do Gemini.
- Não perder dados de pesquisas ou análises quando a aplicação é reiniciada.

---

## 3. Restrições (Constraints)

- **Sistema Operativo:** Windows.
- **Linguagem / Plataforma:** Python para o backend (ex.: FastAPI ou Flask) com frontend em HTML/CSS/JavaScript (Tailwind ou CSS moderno).
- **Inteligência Artificial:** Google Gemini API (modelo rápido e económico como Gemini Flash) para gerar o resumo, exemplos e categorias.
- **Autenticação / Credenciais:** Chave de API da Google Gemini (GEMINI_API_KEY) configurada localmente ou inserida na aplicação.
- **Git Local:** Uso do `git` instalado no Windows para a funcionalidade de clonar repositórios para o computador.

---

## 4. Decisões do Utilizador (User Decisions)

1. **Estrutura por separadores:** A aplicação terá separadores claros (Analisador, Histórico / Favoritos, e Repositórios Locais).
2. **Linguagem acessível:** Explicações claras e concisas, sem tecnicismos, com foco no "para que serve" e "como usar".
3. **Persistência local obrigatória:** Todos os dados extraídos e gerados têm de ficar gravados no disco do computador.
4. **Ações:** Botões dedicados para "Adicionar ao Computador" (clone) e "Adicionar aos Favoritos".
5. **Categorização automática:** A IA propõe a categoria/tipo de projeto automaticamente no momento da análise.
6. **Faseamento:** 
   - Fase 1: Analisador + Histórico + Favoritos + Download/Clone + Categorias.
   - Fase 2: Pesquisa e mapeamento dos repositórios locais existentes no computador e relação com programas.

---

## 5. O que fica ao critério do Construtor (Builder's Scope)

- **Base de Dados Local:** SQLite via Python (por ser um ficheiro único, leve e robusto).
- **Estrutura de Pastas de Destino para Clones:** Criar uma pasta padrão (ex.: `d:\AI Projects\Downloaded_Repos` ou configurável na interface) para onde os projetos são clonados quando o utilizador clica em "Adicionar ao Computador".
- **Comunicação com o GitHub:** Usar a API pública do GitHub (ou scraping básico de README via GitHub API) para obter nome, descrição e o README.md do repositório sem exigir obrigatoriamente um GitHub Token pessoal para repositórios públicos.
- **Design Visual da Interface:** Tema limpo, moderno, com bom contraste, suporte a cartões expansíveis e separadores claros.
- **Tratamento de Erros:** Mensagens amigáveis caso o URL do GitHub seja inválido ou o repositório seja privado/inexistente.
