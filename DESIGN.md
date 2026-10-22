# Especificação de Design e Sistema Visual — AI Toolbox

## 1. Visão Geral & Filosofia de Design
A **AI Toolbox** combina a potência de um gestor de repositórios, organizador de projetos locais, estúdio de prompts, catálogo de skills e extrator de multimédia numa interface unificada, intuitiva e moderna.

O design foi concebido com uma filosofia **Mobile-First / PWA**:
- Otimizado para utilização diária no **iPhone** (acesso Wi-Fi e remoto) com botões táteis acessíveis ao polegar, botões de ação rápida como "Colar" de 1 toque e streaming de vídeo nativo (iOS Safari).
- Experiência completa e expansiva no **Desktop** com atalhos de teclado (ex.: `Ctrl + K`), grelhas adaptativas e painéis laterais de detalhes.

---

## 2. Paleta de Cores & Tokens Visuais

A paleta de cores apoia-se em tons neutros sofisticados combinados com acentos funcionais que identificam cada área da toolbox:

### Cores Base & Superfície
- **Background Principal:** `#f8fafc` (`slate-50`)
- **Superfície dos Cartões:** `#ffffff` (`white`) com bordas suaves `#e2e8f0` (`slate-200`)
- **Texto Principal:** `#0f172a` (`slate-900`) para títulos com máxima legibilidade
- **Texto Secundário / Labels:** `#64748b` (`slate-500`) e `#475569` (`slate-600`)

### Cores de Acento Funcional
- **Recursos & Hub:** `#4f46e5` (`indigo-600`) / `#6366f1` (`indigo-500`)
- **Prompts & IA:** `#059669` (`emerald-600`) / `#10b981` (`emerald-500`)
- **Skills de IA:** `#d97706` (`amber-600`) / `#f59e0b` (`amber-500`)
- **Facebook & Multimédia:** `#0284c7` (`sky-600`) / `#0ea5e9` (`sky-500`)
- **Ações Críticas / Alertas:** `#e11d48` (`rose-600`)

---

## 3. Tipografia
- **Família Tipográfica:** `Inter`, `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `Roboto`, `sans-serif`
- **Código / Snippets / Prompts:** `ui-monospace`, `SFMono-Regular`, `Menlo`, `Monaco`, `Consolas`, `monospace`
- **Escala de Tamanhos:**
  - Títulos de secção: `1.25rem` a `1.5rem` (`text-xl` / `text-2xl`) com peso `font-bold` ou `font-extrabold`.
  - Cabeçalhos de cartão: `0.875rem` a `1rem` (`text-sm` / `text-base`) com peso `font-semibold`.
  - Corpo de texto: `0.75rem` a `0.875rem` (`text-xs` / `text-sm`) com entrelinha relaxada (`leading-relaxed`).
  - Badges e metadados: `0.6875rem` (`text-[11px]`) com `font-semibold`.

---

## 4. Componentes de UI

### Cartões Interativos (Cards)
- **Borda e Sombra:** Bordas discretas de 1px com sombra suave `shadow-xs` que transita para `shadow-md` ao passar o rato (`group-hover`).
- **Raio de Curvatura:** `rounded-2xl` (16px) para superfícies principais e `rounded-xl` (12px) para botões e inputs.
- **Micro-interações:** Elevação sutil em hover (`group-hover:scale-105`), transições de cor suaves de 200ms a 300ms.

### Navegação & Separadores
- **Barra de Navegação Superior:** Fixa com efeito de desfoque translúcido (`backdrop-blur-md` e fundo branco a 85%).
- **Navegação em Abas (Tabs & Subviews):** Pílulas arredondadas com estado ativo destacado a cor sólida e contraste elevado.

### Modais & Diálogos
- Fundo escurecido suave com `backdrop-blur-xs` (`bg-slate-900/60`).
- Cartões de diálogo centrados com `max-height: 90vh` e scroll interno suave.
- Fecho imediato no botão `X`, clique no fundo ou tecla `Escape`.

---

## 5. Experiência Móvel (iPhone / Safari)
- **Áreas de Toque Mínimas:** Botões com altura mínima de 40px para facilitar o toque com o polegar.
- **Suporte a PWA:** Metatags `apple-mobile-web-app-capable`, `apple-mobile-web-app-status-bar-style` e ícones para o ecrã inicial.
- **Reprodutor de Vídeo:** Suporte a `playsinline` e `webkit-playsinline` para reprodução direta sem ecrã preto.
- **Área de Transferência:** Botão de 1 toque para colar ligações diretamente do Safari/Facebook.
