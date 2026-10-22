// State
let currentTab = 'home';
let currentGitHubSubView = 'hub';
let favoritesOnly = false;
let currentResult = null;

// Escape HTML helper
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Escape JavaScript string helper for inline onclick handlers
function escapeJsStr(str) {
  if (!str) return '';
  return String(str)
    .replace(/\\/g, '\\\\')
    .replace(/'/g, "\\'")
    .replace(/"/g, '\\"');
}

// Copy text to clipboard helper
async function copyToClipboard(text, successMsg = 'Copiado para a área de transferência!') {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }
    showToast(successMsg, 'success');
  } catch (err) {
    showToast('Não foi possível copiar.', 'error');
  }
}

// Format ISO date into friendly pt-PT string
function formatDate(isoStr) {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleDateString('pt-PT', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  } catch (e) {
    return '';
  }
}


// Format detailed description with Markdown and sections
function formatDescriptionMarkdown(text) {
  if (!text) return '<p class="text-xs text-slate-400">Sem descrição detalhada disponível.</p>';

  let safe = escapeHtml(text);

  // Convert bold **text**
  safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-slate-900">$1</strong>');

  // Convert inline code `code`
  safe = safe.replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-slate-200/80 text-indigo-700 font-mono text-[11px]">$1</code>');

  // Convert markdown links [text](url)
  safe = safe.replace(/\[(.*?)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-indigo-600 hover:underline font-medium inline-flex items-center gap-0.5">$1 <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i></a>');

  const lines = safe.split('\n');
  let html = '';
  let inList = false;

  for (let line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      if (inList) { html += '</ul>'; inList = false; }
      continue;
    }

    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      if (!inList) {
        html += '<ul class="space-y-2 my-2.5 pl-1">';
        inList = true;
      }
      const itemContent = trimmed.substring(2);
      html += `
        <li class="flex items-start gap-2.5 text-xs sm:text-sm text-slate-700 leading-relaxed">
          <i class="fa-solid fa-circle text-[5px] text-indigo-500 mt-2 shrink-0"></i>
          <span>${itemContent}</span>
        </li>
      `;
    } else {
      if (inList) { html += '</ul>'; inList = false; }

      // Check for section headers (e.g. "Como funciona:", "Requisitos:", "Os ficheiros centrais:")
      const isHeader = trimmed.endsWith(':') || trimmed.startsWith('###') || trimmed.startsWith('##');
      if (isHeader) {
        const title = trimmed.replace(/^#+\s*/, '').replace(/:$/, '');
        let icon = 'fa-solid fa-layer-group text-indigo-600';
        const lower = title.toLowerCase();
        if (lower.includes('funciona')) icon = 'fa-solid fa-gears text-indigo-600';
        else if (lower.includes('ficheiro') || lower.includes('arquitetura')) icon = 'fa-solid fa-folder-tree text-indigo-600';
        else if (lower.includes('requisito')) icon = 'fa-solid fa-microchip text-indigo-600';

        html += `
          <div class="mt-4 pt-3.5 first:mt-0 first:pt-0 border-t border-slate-200/70 first:border-0">
            <h5 class="font-bold text-slate-900 text-xs sm:text-sm mb-2 flex items-center gap-2 text-indigo-950">
              <i class="${icon} text-xs"></i>
              <span>${title}</span>
            </h5>
          </div>
        `;
      } else {
        html += `<p class="text-xs sm:text-sm text-slate-700 leading-relaxed mb-2.5">${trimmed}</p>`;
      }
    }
  }

  if (inList) { html += '</ul>'; }

  return html;
}

// Subview Switching for GitHub Tab
function switchGitHubSubView(subView) {
  currentGitHubSubView = subView;

  // Ensure main GitHub tab is active
  if (currentTab !== 'github') {
    switchTab('github');
  }

  // Toggle subviews
  document.querySelectorAll('.github-subview').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.gh-subtab-btn').forEach(el => el.classList.remove('active'));

  const activeSubview = document.getElementById(`github-subview-${subView}`);
  const activeBtn = document.getElementById(`gh-subtab-${subView}-btn`);

  if (activeSubview) activeSubview.classList.remove('hidden');
  if (activeBtn) activeBtn.classList.add('active');

  // Trigger relevant loaders
  if (subView === 'hub') {
    updateGitHubHubCounts();
  } else if (subView === 'analyze') {
    // Keep current result if available
  } else if (subView === 'catalog') {
    loadCategories();
    loadHistory();
  } else if (subView === 'local') {
    loadLocalRepos();
  } else if (subView === 'trending') {
    loadTrendingRepos();
    loadHuggingFaceTrending();
  } else if (subView === 'facebook') {
    loadMediaItems();
  }
}

// Update badges on GitHub Hub tiles
async function updateGitHubHubCounts() {
  try {
    const [resHist, resLocal, resMedia] = await Promise.all([
      fetch('/api/repos').then(r => r.ok ? r.json() : []),
      fetch('/api/repos?cloned_only=true').then(r => r.ok ? r.json() : []),
      fetch('/api/media').then(r => r.ok ? r.json() : [])
    ]);

    const histCount = Array.isArray(resHist) ? resHist.length : 0;
    const localCount = Array.isArray(resLocal) ? resLocal.length : 0;
    const mediaCount = Array.isArray(resMedia) ? resMedia.length : 0;

    const catalogBadge = document.getElementById('hub-catalog-count-badge');
    if (catalogBadge) catalogBadge.textContent = `${histCount} guardados`;

    const localBadge = document.getElementById('hub-local-count-badge');
    if (localBadge) localBadge.textContent = `${localCount} locais`;

    const mediaBadge = document.getElementById('hub-media-count-badge');
    if (mediaBadge) mediaBadge.textContent = `${mediaCount} guardados`;

    const mediaBtnBadge = document.getElementById('hub-media-badge-btn');
    if (mediaBtnBadge) mediaBtnBadge.textContent = `${mediaCount}`;
  } catch (err) {
    // Non-critical background update
  }
}

// Tab Switching
function switchTab(tab) {
  // Backwards compatibility routing
  if (tab === 'analyze') {
    switchTab('github');
    switchGitHubSubView('analyze');
    return;
  }
  if (tab === 'history') {
    switchTab('github');
    switchGitHubSubView('catalog');
    return;
  }
  if (tab === 'local') {
    switchTab('github');
    switchGitHubSubView('local');
    return;
  }
  if (tab === 'trending') {
    switchTab('github');
    switchGitHubSubView('trending');
    return;
  }

  currentTab = tab;
  document.querySelectorAll('.tab-pane').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.nav-tab').forEach(el => el.classList.remove('active'));

  const activePane = document.getElementById(`tab-${tab}`);
  const activeBtn = document.getElementById(`tab-${tab}-btn`);

  if (activePane) activePane.classList.remove('hidden');
  if (activeBtn) activeBtn.classList.add('active');

  if (tab === 'home') {
    loadHomeDashboard();
  } else if (tab === 'github') {
    if (currentGitHubSubView === 'hub') {
      updateGitHubHubCounts();
    } else {
      switchGitHubSubView(currentGitHubSubView);
    }
  } else if (tab === 'projects') {
    switchProjectsSubTab(currentProjectsSubTab);
  } else if (tab === 'skills') {
    loadSkills();
  } else if (tab === 'prompts') {
    loadMyPrompts();
    loadCommunityPrompts();
  }
}

// Toast Notifications
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  const bgColor = type === 'success' ? 'bg-slate-900 text-white' : 'bg-rose-600 text-white';
  const icon = type === 'success' ? 'fa-circle-check text-emerald-400' : 'fa-circle-exclamation';

  toast.className = `toast px-4 py-3 rounded-xl shadow-lg flex items-center gap-2.5 text-sm font-medium ${bgColor}`;
  toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${escapeHtml(message)}</span>`;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Analyze Handler
async function handleAnalyze(e) {
  e.preventDefault();
  const input = document.getElementById('repo-url-input');
  const url = input.value.trim();
  if (!url) return;
  input.value = '';

  const loadingEl = document.getElementById('analyze-loading');
  const submitBtn = document.getElementById('analyze-submit-btn');
  const resultContainer = document.getElementById('analysis-result-container');

  loadingEl.classList.remove('hidden');
  submitBtn.disabled = true;
  submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
  resultContainer.classList.add('hidden');

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Ocorreu um erro ao analisar o repositório.');
    }

    currentResult = data;
    renderAnalysisResult(data);
    showToast('Repositório analisado com sucesso!');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    loadingEl.classList.add('hidden');
    submitBtn.disabled = false;
    submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
  }
}

// Render Result Card in Analyze Tab
function renderAnalysisResult(repo) {
  const container = document.getElementById('analysis-result-container');
  container.classList.remove('hidden');

  const favIconClass = repo.is_favorite ? 'fa-solid text-amber-500' : 'fa-regular text-slate-400';
  const cloneBtnText = repo.is_cloned ? 'No Computador' : 'Adicionar ao Computador';
  const cloneBtnStyle = repo.is_cloned ? 'bg-emerald-50 text-emerald-700 border-emerald-200 cursor-default' : 'bg-slate-900 text-white hover:bg-slate-800';

  const useCasesHtml = repo.use_cases && repo.use_cases.length > 0 
    ? repo.use_cases.map(uc => `<li class="flex items-start gap-2.5 text-sm text-slate-700"><i class="fa-solid fa-check text-indigo-500 mt-1 shrink-0"></i><span>${escapeHtml(uc)}</span></li>`).join('')
    : '<li class="text-sm text-slate-500">Sem exemplos práticos específicos disponíveis.</li>';

  let projectMatchesHtml = '';
  if (repo.project_matches && repo.project_matches.length > 0) {
    projectMatchesHtml = `
      <div class="p-5 rounded-2xl bg-indigo-50/70 border border-indigo-200">
        <div class="flex items-center justify-between gap-2 mb-3">
          <div class="flex items-center gap-2">
            <i class="fa-solid fa-puzzle-piece text-indigo-600 text-lg"></i>
            <h4 class="text-xs font-bold uppercase tracking-wider text-indigo-900">Utilidade Para os Teus Projetos</h4>
          </div>
          <span class="bg-indigo-600 text-white text-[10px] font-semibold px-2.5 py-0.5 rounded-full">
            ${repo.project_matches.length} ${repo.project_matches.length === 1 ? 'projeto compatível' : 'projetos compatíveis'}
          </span>
        </div>
        <div class="space-y-2.5">
          ${repo.project_matches.map(m => `
            <div class="p-3.5 bg-white rounded-xl border border-indigo-100 shadow-xs">
              <div class="flex items-center gap-2 mb-1.5">
                <span class="px-2 py-0.5 bg-indigo-100 text-indigo-800 rounded font-semibold text-xs">
                  ${escapeHtml(m.project_name)}
                </span>
              </div>
              <p class="text-xs sm:text-sm text-slate-700 leading-relaxed">
                ${escapeHtml(m.relevance_explanation)}
              </p>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  } else {
    projectMatchesHtml = `
      <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500 flex items-center gap-2">
        <i class="fa-solid fa-circle-info text-slate-400 text-sm"></i>
        <span>Nenhum dos teus projetos em desenvolvimento tem necessidade identificada para este repositório no momento.</span>
      </div>
    `;
  }

  container.innerHTML = `
    <div class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm transition-all">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
        <div>
          <div class="flex items-center gap-2.5 flex-wrap">
            <h3 class="text-2xl font-bold text-slate-900">${escapeHtml(repo.name)}</h3>
            <span class="badge-category">
              <i class="fa-solid fa-tag text-[10px] mr-1"></i> ${escapeHtml(repo.category)}
            </span>
            <button onclick="editCategory(${repo.id})" title="Alterar tipo" class="text-xs text-slate-400 hover:text-indigo-600 transition-colors">
              <i class="fa-solid fa-pen-to-square"></i>
            </button>
          </div>
          <p class="text-xs text-slate-500 mt-1">
            Por <span class="font-medium text-slate-700">${escapeHtml(repo.owner)}</span> &bull; 
            <a href="${escapeHtml(repo.url)}" target="_blank" rel="noopener noreferrer" class="text-indigo-600 hover:underline inline-flex items-center gap-1">
              Ver no GitHub <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
            </a>
          </p>
        </div>

        <div class="flex items-center gap-2">
          <button 
            id="reanalyze-btn-${repo.id}"
            onclick="reanalyzeRepo(${repo.id})" 
            title="Reanalisar o repositório com o Gemini para atualizar a descrição"
            class="p-2.5 rounded-xl border border-slate-200 text-slate-600 hover:text-indigo-600 hover:bg-slate-50 transition-colors text-base cursor-pointer"
          >
            <i class="fa-solid fa-arrows-rotate"></i>
          </button>

          <button 
            onclick="toggleFavoriteInCurrent(${repo.id})" 
            title="${repo.is_favorite ? 'Remover dos favoritos' : 'Adicionar aos favoritos'}"
            class="p-2.5 rounded-xl border border-slate-200 hover:bg-slate-50 transition-colors text-lg"
          >
            <i class="fa-star ${favIconClass}"></i>
          </button>

          <button 
            id="clone-btn-${repo.id}"
            onclick="cloneRepo(${repo.id})" 
            ${repo.is_cloned ? 'disabled' : ''}
            class="px-4 py-2.5 rounded-xl font-medium text-sm border transition-all flex items-center gap-2 ${cloneBtnStyle}"
          >
            <i class="fa-solid ${repo.is_cloned ? 'fa-check' : 'fa-download'}"></i>
            <span>${cloneBtnText}</span>
          </button>

          <button 
            onclick="deleteRepoConfirm(${repo.id}, '${escapeHtml(repo.name)}')" 
            title="Eliminar este repositório do catálogo"
            class="p-2.5 rounded-xl border border-slate-200 text-rose-500 hover:bg-rose-50 transition-colors text-lg cursor-pointer"
          >
            <i class="fa-solid fa-trash-can"></i>
          </button>
        </div>
      </div>

      <div class="mt-6 space-y-6">
        <div>
          <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Visão Geral &amp; Como Funciona</h4>
          <div class="p-5 sm:p-6 rounded-2xl bg-slate-50 border border-slate-200/80 text-slate-800 text-sm leading-relaxed">
            ${formatDescriptionMarkdown(repo.description_simple)}
          </div>
        </div>

        <div>
          <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Exemplos Práticos de Utilização</h4>
          <ul class="space-y-2 p-4 rounded-xl bg-slate-50 border border-slate-100">
            ${useCasesHtml}
          </ul>
        </div>

        <div>
          ${projectMatchesHtml}
        </div>

        ${repo.is_cloned && repo.local_path ? `
          <div class="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2">
            <i class="fa-solid fa-folder-check text-emerald-600 text-sm"></i>
            <span>Guardado no computador em: <strong class="font-mono">${escapeHtml(repo.local_path)}</strong></span>
          </div>
        ` : ''}
      </div>
    </div>
  `;
}

// Toggle Favorite
async function toggleFavoriteInCurrent(id) {
  try {
    const res = await fetch(`/api/repos/${id}/favorite`, { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      if (currentResult && currentResult.id === id) {
        currentResult.is_favorite = data.is_favorite;
        renderAnalysisResult(currentResult);
      }
      showToast(data.is_favorite ? 'Adicionado aos favoritos' : 'Removido dos favoritos');
    }
  } catch (err) {
    showToast('Erro ao atualizar favorito', 'error');
  }
}

// Clone Repo
async function cloneRepo(id) {
  const btn = document.getElementById(`clone-btn-${id}`);
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i> <span>A descarregar...</span>`;
  }

  try {
    const res = await fetch(`/api/repos/${id}/clone`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Falha ao clonar repositório.');

    showToast('Repositório descarregado com sucesso para o teu computador!');
    if (currentResult && currentResult.id === id) {
      currentResult.is_cloned = true;
      currentResult.local_path = data.local_path;
      renderAnalysisResult(currentResult);
    }
    if (currentTab === 'history') loadHistory();
    if (currentTab === 'local') loadLocalRepos();
    if (currentTab === 'projects') loadMyProjects();
  } catch (err) {
    showToast(err.message, 'error');
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-download"></i> <span>Adicionar ao Computador</span>`;
    }
  }
}

// Install Repo from Project Recommendations Card
async function installRepoFromProject(id) {
  const btn = document.getElementById(`install-btn-${id}`);
  const originalHtml = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin text-[10px]"></i> <span>A instalar...</span>`;
  }

  try {
    const res = await fetch(`/api/repos/${id}/clone`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Falha ao instalar repositório.');

    showToast('Repositório instalado com sucesso no teu computador!');
    loadMyProjects();
    if (currentTab === 'local') loadLocalRepos();
    if (currentTab === 'history') loadHistory();
  } catch (err) {
    showToast(err.message, 'error');
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
}

// Edit Category
async function editCategory(id) {
  const current = currentResult ? currentResult.category : '';
  const newCat = prompt('Introduz a nova categoria / tipo para este repositório:', current);
  if (!newCat || newCat.trim() === '') return;

  try {
    const res = await fetch(`/api/repos/${id}/category`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category: newCat.trim() })
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Categoria atualizada com sucesso');
      if (currentResult && currentResult.id === id) {
        currentResult.category = data.category;
        renderAnalysisResult(currentResult);
      }
      if (currentTab === 'history') loadHistory();
    }
  } catch (err) {
    showToast('Erro ao atualizar categoria', 'error');
  }
}

// Load Categories for dropdown
async function loadCategories() {
  try {
    const res = await fetch('/api/categories');
    const categories = await res.json();
    const select = document.getElementById('filter-category');
    const currentVal = select.value;
    select.innerHTML = '<option value="">Todos os Tipos</option>';
    categories.forEach(cat => {
      const opt = document.createElement('option');
      opt.value = cat;
      opt.textContent = cat;
      if (cat === currentVal) opt.selected = true;
      select.appendChild(opt);
    });
  } catch (err) {
    console.error('Erro ao carregar categorias:', err);
  }
}

// Toggle Favorite Filter
function toggleFavoriteFilter() {
  favoritesOnly = !favoritesOnly;
  const btn = document.getElementById('filter-favorites-btn');
  if (favoritesOnly) {
    btn.classList.add('bg-amber-50', 'border-amber-300', 'text-amber-800');
    btn.classList.remove('bg-slate-50', 'border-slate-300', 'text-slate-700');
  } else {
    btn.classList.remove('bg-amber-50', 'border-amber-300', 'text-amber-800');
    btn.classList.add('bg-slate-50', 'border-slate-300', 'text-slate-700');
  }
  loadHistory();
}

// Load History
async function loadHistory() {
  const category = document.getElementById('filter-category').value;
  const sortSelect = document.getElementById('filter-sort-history');
  const sortVal = sortSelect ? sortSelect.value : 'date-desc';
  const [sortBy, sortOrder] = sortVal.split('-');
  const grid = document.getElementById('history-grid');
  const countEl = document.getElementById('history-count');

  let url = `/api/repos?sort_by=${encodeURIComponent(sortBy || 'date')}&sort_order=${encodeURIComponent(sortOrder || 'desc')}&`;
  if (category) url += `category=${encodeURIComponent(category)}&`;
  if (favoritesOnly) url += `favorites_only=true&`;

  try {
    const res = await fetch(url);
    const repos = await res.json();

    countEl.textContent = `${repos.length} ${repos.length === 1 ? 'repositório guardado' : 'repositórios guardados'}`;

    if (repos.length === 0) {
      grid.innerHTML = `
        <div class="col-span-full py-12 text-center text-slate-400 bg-white rounded-2xl border border-slate-200">
          <i class="fa-regular fa-folder-open text-3xl mb-2"></i>
          <p class="text-sm font-medium">Nenhum repositório encontrado com os filtros selecionados.</p>
        </div>
      `;
      return;
    }

    grid.innerHTML = repos.map(repo => {
      const favIconClass = repo.is_favorite ? 'fa-solid text-amber-500' : 'fa-regular text-slate-300';
      const formattedDate = formatDate(repo.created_at);
      return `
        <div class="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex flex-col justify-between hover:border-slate-300 transition-all">
          <div>
            <div class="flex items-start justify-between gap-2 mb-2">
              <div>
                <h4 class="font-bold text-slate-900 hover:text-indigo-600 transition-colors cursor-pointer" onclick="viewRepoDetails(${repo.id})">
                  ${escapeHtml(repo.name)}
                </h4>
                <p class="text-xs text-slate-400">${escapeHtml(repo.owner)}</p>
              </div>
              <button onclick="toggleFavoriteInHistory(${repo.id})" class="text-lg p-1 hover:scale-110 transition-transform">
                <i class="fa-star ${favIconClass}"></i>
              </button>
            </div>

            <div class="mb-3 flex items-center justify-between gap-2">
              <span class="badge-category text-[11px]">
                ${escapeHtml(repo.category)}
              </span>
              ${formattedDate ? `
                <span class="text-[11px] text-slate-400 flex items-center gap-1 font-mono">
                  <i class="fa-regular fa-calendar text-[10px]"></i>
                  <span>${escapeHtml(formattedDate)}</span>
                </span>
              ` : ''}
            </div>

            <p class="text-xs text-slate-600 line-clamp-3 leading-relaxed mb-4">
              ${escapeHtml(repo.description_simple)}
            </p>
          </div>

          <div class="flex items-center justify-between pt-3 border-t border-slate-100 text-xs">
            <button onclick="viewRepoDetails(${repo.id})" class="text-indigo-600 font-medium hover:underline">
              Ver Detalhes
            </button>
            <div class="flex items-center gap-2">
              ${repo.is_cloned ? `
                <span class="text-emerald-700 bg-emerald-50 px-2 py-1 rounded-md text-[11px] font-medium flex items-center gap-1">
                  <i class="fa-solid fa-check"></i> No PC
                </span>
              ` : `
                <button onclick="cloneRepo(${repo.id})" class="text-slate-700 hover:text-indigo-600 font-medium flex items-center gap-1">
                  <i class="fa-solid fa-download"></i> Descarregar
                </button>
              `}
              <button onclick="deleteRepoConfirm(${repo.id}, '${escapeHtml(repo.name)}')" title="Eliminar repositório" class="text-slate-400 hover:text-rose-600 p-1 transition-colors text-sm ml-1">
                <i class="fa-solid fa-trash-can"></i>
              </button>
            </div>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    grid.innerHTML = `<div class="col-span-full text-center text-rose-500 text-sm py-8">Erro ao carregar histórico.</div>`;
  }
}

// Toggle Favorite inside History
async function toggleFavoriteInHistory(id) {
  try {
    const res = await fetch(`/api/repos/${id}/favorite`, { method: 'POST' });
    if (res.ok) {
      loadHistory();
    }
  } catch (err) {
    showToast('Erro ao atualizar favorito', 'error');
  }
}

// View Repo Details (switches to analyze tab with that repo)
async function viewRepoDetails(id) {
  try {
    const res = await fetch(`/api/repos/${id}`);
    const repo = await res.json();
    if (res.ok) {
      currentResult = repo;
      switchTab('analyze');
      document.getElementById('repo-url-input').value = repo.url;
      renderAnalysisResult(repo);
    }
  } catch (err) {
    showToast('Erro ao carregar detalhes do repositório', 'error');
  }
}

// Open Local Folder in Windows Explorer
async function openLocalFolder(folderPath) {
  if (!folderPath) {
    showToast('Caminho não disponível', 'error');
    return;
  }
  try {
    const res = await fetch('/api/open-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: folderPath })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Não foi possível abrir a pasta');
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// Open Local Folder in VS Code
async function openInEditor(folderPath) {
  if (!folderPath) {
    showToast('Caminho não disponível', 'error');
    return;
  }
  try {
    const res = await fetch('/api/open-in-editor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: folderPath })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Não foi possível abrir no editor');
    }
    showToast('A abrir no editor...', 'info');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// Load Local Repos (Tab 3)
async function loadLocalRepos() {
  const container = document.getElementById('local-repos-list');
  try {
    const res = await fetch('/api/repos?cloned_only=true');
    const repos = await res.json();

    if (repos.length === 0) {
      container.innerHTML = `
        <div class="py-12 text-center text-slate-400 bg-white rounded-2xl border border-slate-200">
          <i class="fa-solid fa-laptop text-3xl mb-2"></i>
          <p class="text-sm font-medium">Ainda não descarregaste nenhum repositório para o teu computador.</p>
          <p class="text-xs text-slate-400 mt-1">Quando clicares em "Adicionar ao Computador", os repositórios ficarão listados aqui com o caminho do disco.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = repos.map(repo => `
      <div class="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="min-w-0">
          <div class="flex items-center gap-2">
            <h4 class="font-bold text-slate-900">${escapeHtml(repo.name)}</h4>
            <span class="badge-category text-[11px]">${escapeHtml(repo.category)}</span>
          </div>
          <p class="text-xs text-slate-500 mt-1 flex items-center gap-1.5 flex-wrap">
            <span>Caminho local:</span>
            <code class="font-mono text-slate-700 bg-slate-100 px-2 py-0.5 rounded text-[11px] select-all">${escapeHtml(repo.local_path || '')}</code>
          </p>
          <p class="text-xs text-slate-600 mt-2 line-clamp-2">${escapeHtml(repo.description_simple)}</p>
        </div>
        <div class="flex items-center gap-2 shrink-0 flex-wrap">
          ${repo.local_path ? `
            <button onclick="gitPullRepo(${repo.id})" id="btn-pull-${repo.id}" title="Puxar atualizações do GitHub (git pull)" class="px-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-medium flex items-center gap-1.5 transition-all cursor-pointer">
              <i class="fa-solid fa-cloud-arrow-down text-emerald-600"></i>
              <span>Atualizar</span>
            </button>
            <button onclick="openLocalFolder('${escapeJsStr(repo.local_path)}')" title="Abrir pasta no Explorador" class="px-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-medium flex items-center gap-1.5 transition-all cursor-pointer">
              <i class="fa-regular fa-folder-open text-indigo-600"></i>
              <span>Abrir Pasta</span>
            </button>
            <button onclick="openInEditor('${escapeJsStr(repo.local_path)}')" title="Abrir no VS Code" class="px-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-medium flex items-center gap-1.5 transition-all cursor-pointer">
              <i class="fa-solid fa-code text-blue-600"></i>
              <span>VS Code</span>
            </button>
          ` : ''}
          <button onclick="viewRepoDetails(${repo.id})" class="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-medium hover:bg-slate-50 transition-all cursor-pointer">
            Ver Ficha
          </button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<div class="text-center text-rose-500 text-sm py-8">Erro ao carregar repositórios locais.</div>`;
  }
}

// ==================== SCAN DE REPOSITÓRIOS NO DISCO ====================
let selectedLocalScanFolder = null;
let currentScannedLocalRepos = [];

// Choose Folder for Local Scan
async function handleChooseLocalScanFolder() {
  try {
    const res = await fetch('/api/browse-folder', { method: 'POST' });
    const data = await res.json();
    if (data.path) {
      selectedLocalScanFolder = data.path;
      handleScanLocalRepos();
    }
  } catch (err) {
    showToast('Não foi possível abrir o seletor de pastas', 'error');
  }
}

// Scan Installed Repositories on PC
async function handleScanLocalRepos() {
  const btn = document.getElementById('btn-scan-local-repos');
  const infoBar = document.getElementById('local-scan-info-bar');
  const folderText = document.getElementById('local-scan-folder-text');
  const countText = document.getElementById('local-scan-count-text');
  const resultsContainer = document.getElementById('local-scan-results-container');

  const originalBtnHtml = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i><span>A varrer disco...</span>`;
  }

  try {
    const res = await fetch('/api/local-repos/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder: selectedLocalScanFolder })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Falha ao varrer o computador');
    }

    const data = await res.json();
    currentScannedLocalRepos = data.repos || [];

    if (infoBar && folderText && countText) {
      infoBar.classList.remove('hidden');
      folderText.textContent = data.search_folder;
      countText.textContent = `${currentScannedLocalRepos.length} repositórios detetados`;
    }

    if (resultsContainer) {
      resultsContainer.classList.remove('hidden');
    }

    renderLocalScanResults();
    showToast(`Scan concluído: ${currentScannedLocalRepos.length} repositórios encontrados.`, 'success');
  } catch (err) {
    showToast(err.message || 'Erro ao realizar scan', 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalBtnHtml;
    }
  }
}

function renderLocalScanResults() {
  const grid = document.getElementById('local-scan-grid');
  const pendingCountEl = document.getElementById('local-scan-pending-count');
  const btnImportAll = document.getElementById('btn-import-all');
  if (!grid) return;

  if (!currentScannedLocalRepos || currentScannedLocalRepos.length === 0) {
    grid.innerHTML = `
      <div class="col-span-full py-8 text-center text-slate-400 bg-white rounded-2xl border border-slate-200">
        <i class="fa-solid fa-folder-open text-2xl mb-1 text-slate-300"></i>
        <p class="text-sm font-medium">Nenhum repositório Git encontrado nesta pasta.</p>
      </div>
    `;
    if (pendingCountEl) pendingCountEl.textContent = '';
    if (btnImportAll) btnImportAll.classList.add('hidden');
    return;
  }

  const uncataloged = currentScannedLocalRepos.filter(r => !r.is_cataloged).length;
  if (pendingCountEl) {
    pendingCountEl.textContent = `${uncataloged} por adicionar ao catálogo`;
  }

  if (btnImportAll) {
    if (uncataloged > 0) {
      btnImportAll.classList.remove('hidden');
    } else {
      btnImportAll.classList.add('hidden');
    }
  }

  grid.innerHTML = currentScannedLocalRepos.map((repo, idx) => {
    const isGithub = repo.remote_url && repo.remote_url.includes('github.com');
    return `
      <div class="bg-white rounded-2xl p-4 sm:p-5 border ${repo.is_cataloged ? 'border-slate-200 bg-slate-50/50' : 'border-indigo-100 shadow-sm ring-1 ring-indigo-50'} flex flex-col justify-between">
        <div>
          <div class="flex items-start justify-between gap-2 mb-2">
            <div class="flex items-center gap-2.5 min-w-0">
              <span class="w-8 h-8 rounded-lg ${repo.is_cataloged ? 'bg-slate-100 text-slate-600' : 'bg-indigo-50 text-indigo-600'} flex items-center justify-center font-bold text-xs shrink-0">
                <i class="fa-brands fa-git-alt text-base"></i>
              </span>
              <div class="min-w-0">
                <h4 class="font-bold text-slate-900 text-sm truncate">${escapeHtml(repo.name)}</h4>
                <p class="text-[11px] text-slate-400 font-mono truncate">${escapeHtml(repo.remote_url || 'Sem remote origin')}</p>
              </div>
            </div>
            ${repo.is_cataloged ? `
              <span class="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full text-[11px] font-medium border border-emerald-200 flex items-center gap-1 shrink-0">
                <i class="fa-solid fa-check text-[10px]"></i> No Catálogo
              </span>
            ` : `
              <span class="text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full text-[11px] font-medium border border-amber-200 flex items-center gap-1 shrink-0">
                <i class="fa-solid fa-circle text-[8px]"></i> Não Catalogado
              </span>
            `}
          </div>

          <div class="mt-2 text-xs text-slate-500">
            <span class="block truncate font-mono text-[11px] text-slate-600 bg-slate-50 px-2 py-1 rounded" title="${escapeHtml(repo.path)}">
              <i class="fa-regular fa-folder text-slate-400 mr-1"></i>${escapeHtml(repo.path)}
            </span>
          </div>
        </div>

        <div class="flex items-center justify-between gap-2 mt-4 pt-3 border-t border-slate-100 text-xs flex-wrap">
          <div class="flex items-center gap-1.5">
            <button onclick="openLocalFolder('${escapeJsStr(repo.path)}')" title="Abrir pasta no Explorador" class="p-1.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-600 text-xs font-medium flex items-center gap-1 transition-all cursor-pointer">
              <i class="fa-regular fa-folder-open text-indigo-600 text-xs"></i>
            </button>
            <button onclick="openInEditor('${escapeJsStr(repo.path)}')" title="Abrir no VS Code" class="p-1.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-600 text-xs font-medium flex items-center gap-1 transition-all cursor-pointer">
              <i class="fa-solid fa-code text-blue-600 text-xs"></i>
            </button>
          </div>

          <div>
            ${repo.is_cataloged ? `
              <button onclick="viewRepoDetails(${repo.catalog_id})" class="text-indigo-600 font-medium hover:underline text-xs flex items-center gap-1 cursor-pointer">
                <span>Ver Ficha</span>
                <i class="fa-solid fa-arrow-right text-[10px]"></i>
              </button>
            ` : `
              <div class="flex items-center gap-2">
                <button 
                  onclick="importLocalRepo(${idx}, false)" 
                  id="btn-import-${idx}"
                  class="px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 font-medium text-xs flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  <i class="fa-solid fa-plus text-[10px]"></i>
                  <span>Adicionar</span>
                </button>
                ${isGithub ? `
                  <button 
                    onclick="importLocalRepo(${idx}, true)" 
                    id="btn-import-ai-${idx}"
                    class="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white font-medium text-xs flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
                  >
                    <i class="fa-solid fa-wand-magic-sparkles text-[10px]"></i>
                    <span>Analisar com IA</span>
                  </button>
                ` : ''}
              </div>
            `}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// Import Local Repo into DB Catalog
async function importLocalRepo(index, autoAnalyze) {
  const repo = currentScannedLocalRepos[index];
  if (!repo) return;

  const btnId = autoAnalyze ? `btn-import-ai-${index}` : `btn-import-${index}`;
  const btn = document.getElementById(btnId);
  const originalHtml = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i><span>A importar...</span>`;
  }

  try {
    const res = await fetch('/api/local-repos/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: repo.name,
        path: repo.path,
        remote_url: repo.remote_url || '',
        auto_analyze: autoAnalyze
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Falha ao importar repositório');
    }

    const saved = await res.json();
    repo.is_cataloged = true;
    repo.catalog_id = saved.id;

    showToast(`"${repo.name}" adicionado ao catálogo!`, 'success');
    renderLocalScanResults();
    loadLocalRepos();
    loadHistory();
    loadCategories();
  } catch (err) {
    showToast(err.message || 'Erro ao importar repositório', 'error');
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
}

// Import All Uncataloged Repositories in Batch
async function importAllScannedRepos() {
  const uncataloged = currentScannedLocalRepos.filter(r => !r.is_cataloged);
  if (uncataloged.length === 0) {
    showToast('Todos os repositórios já estão catalogados', 'info');
    return;
  }

  const btn = document.getElementById('btn-import-all');
  const originalHtml = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i><span>A importar ${uncataloged.length}...</span>`;
  }

  try {
    const payload = uncataloged.map(r => ({
      name: r.name,
      path: r.path,
      remote_url: r.remote_url || '',
      auto_analyze: false
    }));

    const res = await fetch('/api/local-repos/import-batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repos: payload })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Falha na importação em lote');
    }

    const result = await res.json();
    currentScannedLocalRepos.forEach(r => {
      const found = (result.imported || []).find(imp => imp.local_path === r.path);
      if (found) {
        r.is_cataloged = true;
        r.catalog_id = found.id;
      }
    });

    showToast(`${result.imported_count} repositórios adicionados ao catálogo!`, 'success');
    renderLocalScanResults();
    loadLocalRepos();
    loadHistory();
    loadCategories();
  } catch (err) {
    showToast(err.message || 'Erro ao importar repositórios em lote', 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
}

// QR Code Modal (Ligar ao iPhone)
let qrCodeInstance = null;

async function openQrModal() {
  const modal = document.getElementById('qr-modal');
  const box = document.getElementById('qrcode-box');
  const text = document.getElementById('qr-url-text');

  modal.classList.remove('hidden');

  try {
    const res = await fetch('/api/network-info');
    const data = await res.json();
    const url = data.url;
    text.textContent = url;

    box.innerHTML = '';
    if (typeof QRCode !== 'undefined') {
      qrCodeInstance = new QRCode(box, {
        text: url,
        width: 180,
        height: 180,
        colorDark: '#0f172a',
        colorLight: '#f8fafc',
        correctLevel: QRCode.CorrectLevel.M
      });
    } else {
      box.innerHTML = `<p class="text-xs text-slate-500">Acede no Safari: <br><strong class="text-indigo-600">${escapeHtml(url)}</strong></p>`;
    }
  } catch (err) {
    text.textContent = 'Erro ao obter endereço de rede';
  }
}

function closeQrModal() {
  const modal = document.getElementById('qr-modal');
  modal.classList.add('hidden');
}

// ==================== OS MEUS PROJETOS ====================

let currentScanData = null;

function openAddProjectModal() {
  const modal = document.getElementById('add-project-modal');
  modal.classList.remove('hidden');

  document.getElementById('proj-scan-path').value = '';
  document.getElementById('proj-modal-name').value = '';
  document.getElementById('proj-modal-status').value = 'em desenvolvimento';
  document.getElementById('proj-modal-techs').value = '';
  document.getElementById('proj-modal-summary').value = '';
  document.getElementById('proj-modal-notes').value = '';

  document.getElementById('proj-modal-details').classList.add('hidden');
  document.getElementById('proj-scan-loading').classList.add('hidden');
  document.getElementById('proj-modal-internal-repos-container').classList.add('hidden');
  document.getElementById('proj-modal-internal-repos-list').innerHTML = '';
  currentScanData = null;

  loadQuickFolders();
}

async function loadQuickFolders() {
  const chips = document.getElementById('quick-folders-chips');
  if (!chips) return;

  try {
    const res = await fetch('/api/my-projects/quick-folders');
    const data = await res.json();
    if (res.ok && data.folders && data.folders.length > 0) {
      chips.innerHTML = data.folders.map(f => `
        <button 
          type="button"
          onclick="selectQuickFolder('${escapeJsStr(f.path)}')"
          class="px-2.5 py-1 bg-white hover:bg-indigo-50 text-slate-700 hover:text-indigo-700 border border-slate-200 hover:border-indigo-300 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 shadow-2xs cursor-pointer"
        >
          <i class="fa-regular fa-folder text-indigo-500 text-[11px]"></i>
          <span>${escapeHtml(f.name)}</span>
        </button>
      `).join('');
    } else {
      chips.innerHTML = '<span class="text-xs text-slate-400 py-1">Nenhuma pasta detetada em D:\\AI Projects.</span>';
    }
  } catch (err) {
    chips.innerHTML = '<span class="text-xs text-slate-400 py-1">Não foi possível detetar pastas automaticamente.</span>';
  }
}

function selectQuickFolder(path) {
  const pathInput = document.getElementById('proj-scan-path');
  if (pathInput) {
    pathInput.value = path;
    handleScanFolder();
  }
}

function closeAddProjectModal() {
  const modal = document.getElementById('add-project-modal');
  if (modal) modal.classList.add('hidden');
}

let currentTreePath = 'D:\\AI Projects';
let parentTreePath = null;

async function toggleFolderTreeBrowser() {
  const box = document.getElementById('in-app-tree-browser');
  if (!box) return;
  box.classList.toggle('hidden');
  if (!box.classList.contains('hidden')) {
    const inputPath = (document.getElementById('proj-scan-path')?.value || '').trim();
    loadFolderTree(inputPath || currentTreePath);
  }
}

async function loadFolderTree(targetPath) {
  const pathText = document.getElementById('tree-path-text');
  const drivesContainer = document.getElementById('tree-drives-list');
  const folderList = document.getElementById('tree-folder-list');
  const upBtn = document.getElementById('tree-up-btn');

  if (pathText) pathText.textContent = targetPath || 'A carregar...';
  if (folderList) folderList.innerHTML = '<div class="col-span-full py-4 text-center text-xs text-slate-400"><i class="fa-solid fa-spinner animate-spin mr-1"></i> A carregar pastas...</div>';

  try {
    const query = targetPath ? `?path=${encodeURIComponent(targetPath)}` : '';
    const res = await fetch(`/api/browse-directory${query}`);
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || 'Erro ao aceder ao diretório');
    }

    currentTreePath = data.current_path;
    parentTreePath = data.parent_path;

    if (pathText) pathText.textContent = data.current_path;

    if (upBtn) {
      if (data.parent_path) {
        upBtn.disabled = false;
        upBtn.classList.remove('opacity-50', 'cursor-not-allowed');
      } else {
        upBtn.disabled = true;
        upBtn.classList.add('opacity-50', 'cursor-not-allowed');
      }
    }

    if (drivesContainer && data.drives) {
      drivesContainer.innerHTML = data.drives.map(d => `
        <button
          type="button"
          onclick="navigateFolderTree('${escapeJsStr(d.path)}')"
          class="px-2 py-0.5 ${currentTreePath.toLowerCase().startsWith(d.path.toLowerCase().slice(0, 2)) ? 'bg-indigo-600 text-white font-bold' : 'bg-white hover:bg-slate-200 text-slate-700 border border-slate-200'} rounded text-[11px] transition-all cursor-pointer"
        >
          ${escapeHtml(d.path.slice(0, 2))}
        </button>
      `).join('');
    }

    if (folderList) {
      if (!data.subfolders || data.subfolders.length === 0) {
        folderList.innerHTML = `
          <div class="col-span-full py-4 text-center text-xs text-slate-400">
            Nenhuma subpasta encontrada aqui.
            <button type="button" onclick="selectTreeFolder('${escapeJsStr(currentTreePath)}')" class="block mx-auto mt-2 px-3 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold rounded-lg text-xs">
              Selecionar esta pasta
            </button>
          </div>
        `;
      } else {
        folderList.innerHTML = data.subfolders.map(sf => `
          <div class="flex items-center justify-between p-1.5 bg-white hover:bg-indigo-50/70 border border-slate-200 hover:border-indigo-200 rounded-lg group transition-colors">
            <button
              type="button"
              onclick="navigateFolderTree('${escapeJsStr(sf.path)}')"
              class="flex-1 min-w-0 flex items-center gap-1.5 text-left text-xs font-medium text-slate-700 hover:text-indigo-600 truncate cursor-pointer"
              title="Abrir pasta ${escapeHtml(sf.name)}"
            >
              <i class="fa-regular fa-folder text-amber-500 text-xs shrink-0"></i>
              <span class="truncate">${escapeHtml(sf.name)}</span>
            </button>
            <button
              type="button"
              onclick="selectTreeFolder('${escapeJsStr(sf.path)}')"
              class="p-1 px-2 bg-indigo-50 hover:bg-indigo-600 text-indigo-600 hover:text-white rounded text-[10px] font-semibold transition-colors shrink-0 ml-1 cursor-pointer"
              title="Escolher esta pasta para o projeto"
            >
              <i class="fa-solid fa-check"></i>
            </button>
          </div>
        `).join('');
      }
    }
  } catch (err) {
    if (folderList) {
      folderList.innerHTML = `<div class="col-span-full py-3 text-center text-xs text-rose-500">Erro: ${escapeHtml(err.message)}</div>`;
    }
  }
}

function navigateFolderTree(target) {
  if (target === 'up') {
    if (parentTreePath) {
      loadFolderTree(parentTreePath);
    }
  } else {
    loadFolderTree(target);
  }
}

function selectTreeFolder(folderPath) {
  const pathInput = document.getElementById('proj-scan-path');
  if (pathInput) {
    pathInput.value = folderPath;
  }
  const box = document.getElementById('in-app-tree-browser');
  if (box) {
    box.classList.add('hidden');
  }
  handleScanFolder();
}

async function handleScanFolder() {
  const pathInput = document.getElementById('proj-scan-path');
  const path = pathInput.value.trim();
  if (!path) {
    showToast('Por favor, indica o caminho da pasta no computador.', 'error');
    return;
  }

  const scanBtn = document.getElementById('proj-scan-btn');
  const loading = document.getElementById('proj-scan-loading');
  const details = document.getElementById('proj-modal-details');

  scanBtn.disabled = true;
  loading.classList.remove('hidden');
  details.classList.add('hidden');

  try {
    const res = await fetch('/api/my-projects/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Erro ao analisar pasta.');
    }

    currentScanData = data;
    document.getElementById('proj-modal-name').value = data.name || '';
    document.getElementById('proj-modal-status').value = 'em desenvolvimento';
    document.getElementById('proj-modal-techs').value = (data.technologies || []).join(', ');
    document.getElementById('proj-modal-summary').value = data.summary || '';
    document.getElementById('proj-modal-notes').value = '';

    const intContainer = document.getElementById('proj-modal-internal-repos-container');
    const intList = document.getElementById('proj-modal-internal-repos-list');
    if (data.internal_repos && data.internal_repos.length > 0) {
      intContainer.classList.remove('hidden');
      intList.innerHTML = data.internal_repos.map(r => `
        <label class="flex items-start gap-2 p-2.5 bg-white rounded-lg border border-amber-200 cursor-pointer">
          <input type="checkbox" class="internal-repo-chk mt-0.5" value="${escapeHtml(r.path)}" data-name="${escapeHtml(r.name)}" ${r.is_cataloged ? 'disabled checked' : 'checked'}>
          <div class="text-xs">
            <strong class="text-slate-800">${escapeHtml(r.name)}</strong>
            <span class="text-slate-500 block text-[11px] font-mono">${escapeHtml(r.relative_path)}</span>
            ${r.is_cataloged ? '<span class="text-[10px] text-emerald-600 font-semibold">(Já catalogado)</span>' : ''}
          </div>
        </label>
      `).join('');
    } else {
      intContainer.classList.add('hidden');
      intList.innerHTML = '';
    }

    details.classList.remove('hidden');
    showToast('Pasta analisada com sucesso!');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    scanBtn.disabled = false;
    loading.classList.add('hidden');
  }
}

async function handleSaveProject() {
  const name = document.getElementById('proj-modal-name').value.trim();
  const path = document.getElementById('proj-scan-path').value.trim();
  const status = document.getElementById('proj-modal-status').value;
  const summary = document.getElementById('proj-modal-summary').value.trim();
  const notes = document.getElementById('proj-modal-notes').value.trim();
  const techsRaw = document.getElementById('proj-modal-techs').value;
  const technologies = techsRaw.split(',').map(t => t.trim()).filter(Boolean);

  if (!name || !path) {
    showToast('Nome e caminho do projeto são obrigatórios.', 'error');
    return;
  }

  const saveBtn = document.getElementById('proj-modal-save-btn');
  saveBtn.disabled = true;
  saveBtn.innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i> <span>A gravar...</span>`;

  try {
    const res = await fetch('/api/my-projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        path,
        status,
        summary,
        technologies,
        notes
      })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Erro ao guardar projeto.');
    }

    // Check if any internal repos were selected to catalog
    const checkedInternal = document.querySelectorAll('.internal-repo-chk:checked:not([disabled])');
    for (const chk of checkedInternal) {
      const intPath = chk.value;
      const intName = chk.getAttribute('data-name');
      try {
        const scanRes = await fetch('/api/my-projects/scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: intPath })
        });
        if (scanRes.ok) {
          const scanData = await scanRes.json();
          await fetch('/api/my-projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              name: scanData.name || intName,
              path: scanData.path,
              status: 'em desenvolvimento',
              summary: scanData.summary,
              technologies: scanData.technologies,
              notes: 'Repositório interno catalogado automaticamente'
            })
          });
        }
      } catch (e) {
        console.error('Erro ao catalogar repositório interno:', e);
      }
    }

    showToast('Projeto guardado com sucesso!');
    closeAddProjectModal();
    loadMyProjects();
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    saveBtn.disabled = false;
    saveBtn.innerHTML = `<i class="fa-solid fa-check"></i> <span>Gravar Projeto</span>`;
  }
}

function getStatusBadgeClass(status) {
  switch (status) {
    case 'ativo': return 'badge-status badge-status-active';
    case 'em pausa': return 'badge-status badge-status-paused';
    case 'concluído': return 'badge-status badge-status-done';
    default: return 'badge-status badge-status-dev';
  }
}

async function loadMyProjects() {
  const container = document.getElementById('projects-list');
  const countEl = document.getElementById('projects-count');
  const statusFilter = document.getElementById('filter-project-status').value;
  const sortSelect = document.getElementById('filter-sort-projects');
  const sortVal = sortSelect ? sortSelect.value : 'date-desc';
  const [sortBy, sortOrder] = sortVal.split('-');

  let url = `/api/my-projects?sort_by=${encodeURIComponent(sortBy || 'date')}&sort_order=${encodeURIComponent(sortOrder || 'desc')}`;
  if (statusFilter) url += `&status=${encodeURIComponent(statusFilter)}`;

  try {
    const res = await fetch(url);
    const projects = await res.json();

    countEl.textContent = `${projects.length} ${projects.length === 1 ? 'projeto catalogado' : 'projetos catalogados'}`;

    if (projects.length === 0) {
      container.innerHTML = `
        <div class="py-12 text-center text-slate-400 bg-white rounded-2xl border border-slate-200">
          <i class="fa-solid fa-diagram-project text-3xl mb-2"></i>
          <p class="text-sm font-medium">Nenhum projeto encontrado com os filtros selecionados.</p>
          <p class="text-xs text-slate-400 mt-1">Clica em "Adicionar Projeto Local" para catalogar uma pasta do teu computador.</p>
        </div>
      `;
      return;
    }

    // Fetch recommendations for each project in parallel
    const detailedList = await Promise.all(
      projects.map(async p => {
        try {
          const detailRes = await fetch(`/api/my-projects/${p.id}`);
          if (detailRes.ok) {
            const data = await detailRes.json();
            return { project: data.project, recommendations: data.recommendations || [] };
          }
        } catch (e) {}
        return { project: p, recommendations: [] };
      })
    );

    container.innerHTML = detailedList.map(item => {
      const p = item.project;
      const recs = item.recommendations;
      const statusBadge = getStatusBadgeClass(p.status);
      const formattedDate = formatDate(p.created_at);

      const techsHtml = (p.technologies && p.technologies.length > 0)
        ? p.technologies.map(t => `<span class="px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-100 text-slate-700">${escapeHtml(t)}</span>`).join(' ')
        : '<span class="text-xs text-slate-400">Sem tecnologias especificadas</span>';

      const recsHtml = recs.length > 0 ? `
        <div class="mt-4 p-4 rounded-xl bg-indigo-50/70 border border-indigo-200">
          <div class="flex items-center gap-2 mb-2.5 text-indigo-900 font-semibold text-xs">
            <i class="fa-solid fa-puzzle-piece text-indigo-600"></i>
            <span>Repositórios do Catálogo Recomendados (${recs.length}):</span>
          </div>
          <div class="space-y-2">
            ${recs.map(r => `
              <div class="p-3 bg-white rounded-lg border border-indigo-100 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div class="flex-1">
                  <div class="flex items-center gap-2 flex-wrap">
                    <strong class="text-slate-900 text-xs font-bold">${escapeHtml(r.repo_name)}</strong>
                    ${r.repo_category ? `<span class="badge-category text-[10px]">${escapeHtml(r.repo_category)}</span>` : ''}
                  </div>
                  <p class="text-xs text-slate-600 mt-1">${escapeHtml(r.reason)}</p>
                </div>
                <div class="flex items-center gap-2 shrink-0 self-start sm:self-auto flex-wrap">
                  ${r.is_cloned ? `
                    ${r.is_linked ? `
                      <button 
                        onclick="toggleLinkRepo(${p.id}, ${r.repo_id}, false)" 
                        title="Repositório ligado com atalho! Clica para desligar" 
                        class="px-2.5 py-1 text-xs text-emerald-800 bg-emerald-100 hover:bg-rose-50 hover:text-rose-700 hover:border-rose-300 border border-emerald-300 rounded-lg font-medium flex items-center gap-1.5 transition-all cursor-pointer"
                      >
                        <i class="fa-solid fa-link text-[10px]"></i>
                        <span>Ligado ao Projeto</span>
                      </button>
                    ` : `
                      <button 
                        id="link-btn-${p.id}-${r.repo_id}"
                        onclick="toggleLinkRepo(${p.id}, ${r.repo_id}, true)" 
                        title="Criar atalho direto na pasta deste projeto" 
                        class="px-2.5 py-1 text-xs text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-lg font-medium flex items-center gap-1.5 transition-all cursor-pointer shadow-2xs"
                      >
                        <i class="fa-solid fa-link text-[10px]"></i>
                        <span>Ligar a Projeto</span>
                      </button>
                    `}
                    ${r.repo_local_path ? `
                      <button 
                        onclick="copyToClipboard('${escapeJsStr(r.repo_local_path)}', 'Caminho do repositório copiado!')" 
                        title="Copiar caminho da pasta no computador" 
                        class="p-1.5 text-slate-400 hover:text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-xs transition-colors cursor-pointer"
                      >
                        <i class="fa-regular fa-copy"></i>
                      </button>
                    ` : ''}
                  ` : `
                    <button 
                      id="install-btn-${r.repo_id}"
                      onclick="installRepoFromProject(${r.repo_id})" 
                      title="Instalar repositório no computador" 
                      class="px-2.5 py-1 text-xs text-white bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 rounded-lg font-medium flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
                    >
                      <i class="fa-solid fa-download text-[10px]"></i>
                      <span>Instalar</span>
                    </button>
                  `}
                  <button onclick="viewRepoDetails(${r.repo_id})" class="px-2.5 py-1 text-xs text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg font-medium transition-colors cursor-pointer">
                    Ver Repositório
                  </button>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      ` : `
        <div class="mt-4 p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500 flex items-center justify-between">
          <span>Ainda sem repositórios recomendados para este projeto.</span>
          <button onclick="findProjectRecommendations(${p.id})" class="text-indigo-600 hover:underline font-medium text-xs">
            Procurar agora
          </button>
        </div>
      `;

      return `
        <div class="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200 shadow-sm transition-all hover:border-slate-300">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
            <div>
              <div class="flex items-center gap-2.5 flex-wrap">
                <h3 class="text-lg font-bold text-slate-900">${escapeHtml(p.name)}</h3>
                <span class="${statusBadge}">
                  ${escapeHtml(p.status)}
                </span>
                ${formattedDate ? `
                  <span class="text-xs text-slate-400 flex items-center gap-1 font-mono">
                    <i class="fa-regular fa-calendar text-[10px]"></i>
                    <span>${escapeHtml(formattedDate)}</span>
                  </span>
                ` : ''}
                <select onchange="updateProjectStatus(${p.id}, this.value)" class="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 text-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-500">
                  <option value="em desenvolvimento" ${p.status === 'em desenvolvimento' ? 'selected' : ''}>em desenvolvimento</option>
                  <option value="ativo" ${p.status === 'ativo' ? 'selected' : ''}>ativo</option>
                  <option value="em pausa" ${p.status === 'em pausa' ? 'selected' : ''}>em pausa</option>
                  <option value="concluído" ${p.status === 'concluído' ? 'selected' : ''}>concluído</option>
                </select>
              </div>
              <div class="flex items-center gap-1.5 text-xs text-slate-500 font-mono mt-1 select-all">
                <i class="fa-regular fa-folder text-slate-400"></i>
                <span>${escapeHtml(p.path)}</span>
              </div>
            </div>

            <div class="flex items-center gap-2 shrink-0">
              <button 
                onclick="openLocalFolder('${escapeJsStr(p.path)}')" 
                title="Abrir pasta no Explorador"
                class="p-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 text-xs transition-colors cursor-pointer"
              >
                <i class="fa-regular fa-folder-open text-indigo-600"></i>
              </button>
              <button 
                onclick="openInEditor('${escapeJsStr(p.path)}')" 
                title="Abrir no VS Code"
                class="p-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 text-xs transition-colors cursor-pointer"
              >
                <i class="fa-solid fa-code text-blue-600"></i>
              </button>
              <button 
                onclick="findProjectRecommendations(${p.id})" 
                title="Cruzar com repositórios guardados para encontrar recomendações"
                class="px-3 py-1.5 rounded-lg bg-indigo-50 border border-indigo-200 text-indigo-700 hover:bg-indigo-100 text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <i class="fa-solid fa-wand-magic-sparkles text-indigo-600"></i>
                <span>Cruzar Repositórios</span>
              </button>
              <button 
                onclick="refreshProject(${p.id})" 
                title="Ler novamente o código da pasta e atualizar resumo com IA"
                class="p-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 text-xs transition-colors cursor-pointer"
              >
                <i class="fa-solid fa-rotate"></i>
              </button>
              <button 
                onclick="deleteProjectConfirm(${p.id}, '${escapeHtml(p.name)}')" 
                title="Remover projeto da lista"
                class="p-2 rounded-lg border border-slate-200 text-rose-500 hover:bg-rose-50 text-xs transition-colors cursor-pointer"
              >
                <i class="fa-solid fa-trash-can"></i>
              </button>
            </div>
          </div>

          <div class="mt-3.5 space-y-3">
            <div class="flex items-center gap-1.5 flex-wrap">
              ${techsHtml}
            </div>

            <div class="text-xs sm:text-sm text-slate-700 leading-relaxed p-3.5 bg-slate-50 rounded-xl border border-slate-100">
              ${escapeHtml(p.summary || 'Sem resumo disponível.')}
            </div>

            ${recsHtml}

            <!-- Personal Notes Section -->
            <div class="pt-2">
              <div class="flex items-center justify-between mb-1">
                <span class="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">Notas Pessoais</span>
                <button onclick="saveProjectNotes(${p.id})" class="text-xs text-indigo-600 hover:text-indigo-800 font-medium cursor-pointer">
                  <i class="fa-solid fa-floppy-disk mr-1"></i> Guardar Notas
                </button>
              </div>
              <textarea 
                id="proj-notes-${p.id}" 
                rows="2" 
                placeholder="Escreve aqui notas, tarefas pendentes ou ideias para este projeto..."
                class="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
              >${escapeHtml(p.notes || '')}</textarea>
            </div>
          </div>
        </div>
      `;
    }).join('');
    updateProjectsTabBadges();
  } catch (err) {
    container.innerHTML = `<div class="text-center text-rose-500 text-sm py-8">Erro ao carregar projetos.</div>`;
  }
}

async function updateProjectStatus(id, newStatus) {
  try {
    const res = await fetch(`/api/my-projects/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    });
    if (res.ok) {
      showToast('Estado do projeto atualizado!');
      loadMyProjects();
    } else {
      showToast('Erro ao atualizar estado', 'error');
    }
  } catch (err) {
    showToast('Erro ao comunicar com o servidor', 'error');
  }
}

async function saveProjectNotes(id) {
  const notesEl = document.getElementById(`proj-notes-${id}`);
  if (!notesEl) return;
  const notes = notesEl.value;

  try {
    const res = await fetch(`/api/my-projects/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes })
    });
    if (res.ok) {
      showToast('Notas guardadas com sucesso!');
    } else {
      showToast('Erro ao guardar notas', 'error');
    }
  } catch (err) {
    showToast('Erro ao comunicar com o servidor', 'error');
  }
}

async function refreshProject(id) {
  showToast('A analisar pasta e a atualizar resumo com IA...');
  try {
    const res = await fetch(`/api/my-projects/${id}/refresh`, { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      showToast('Resumo do projeto atualizado!');
      loadMyProjects();
    } else {
      throw new Error(data.detail || 'Erro ao atualizar projeto.');
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function findProjectRecommendations(id) {
  showToast('A cruzar projeto com o catálogo de repositórios...');
  try {
    const res = await fetch(`/api/my-projects/${id}/find-recommendations`, { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      const count = data.recommendations ? data.recommendations.length : 0;
      showToast(`Cruzamento concluído: ${count} recomendações encontradas!`);
      loadMyProjects();
    } else {
      throw new Error(data.detail || 'Erro ao procurar recomendações.');
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function deleteProjectConfirm(id, name) {
  if (!confirm(`Tens a certeza de que queres remover "${name}" da lista de projetos?\n\nOs ficheiros locais no teu computador NÃO serão apagados.`)) {
    return;
  }

  try {
    const res = await fetch(`/api/my-projects/${id}`, { method: 'DELETE' });
    if (res.ok) {
      showToast('Projeto removido da lista!');
      loadMyProjects();
    } else {
      showToast('Erro ao remover projeto', 'error');
    }
  } catch (err) {
    showToast('Erro ao comunicar com o servidor', 'error');
  }
}

async function toggleLinkRepo(projectId, repoId, link) {
  const endpoint = link ? 'link-repo' : 'unlink-repo';
  const btn = document.getElementById(`link-btn-${projectId}-${repoId}`);
  const originalHtml = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin text-[10px]"></i> <span>A processar...</span>`;
  }

  try {
    const res = await fetch(`/api/my-projects/${projectId}/${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_id: repoId })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Falha ao processar atalho do repositório.');

    showToast(data.message || (link ? 'Repositório ligado ao projeto!' : 'Repositório desligado do projeto!'), 'success');
    loadMyProjects();
  } catch (err) {
    showToast(err.message, 'error');
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
}

async function deleteRepoConfirm(id, name) {
  if (!confirm(`Tens a certeza de que queres eliminar o repositório "${name}" do teu catálogo?`)) {
    return;
  }

  try {
    const res = await fetch(`/api/repos/${id}`, { method: 'DELETE' });
    if (res.ok) {
      showToast('Repositório eliminado com sucesso!');
      if (currentResult && currentResult.id === id) {
        currentResult = null;
        const container = document.getElementById('analysis-result-container');
        if (container) container.classList.add('hidden');
      }
      if (currentTab === 'history') loadHistory();
      if (currentTab === 'local') loadLocalRepos();
      if (currentTab === 'projects') loadMyProjects();
    } else {
      showToast('Erro ao eliminar repositório.', 'error');
    }
  } catch (err) {
    showToast('Erro ao comunicar com o servidor.', 'error');
  }
}

// Reanalyze Repository with Gemini
async function reanalyzeRepo(id) {
  const btn = document.getElementById(`reanalyze-btn-${id}`);
  const originalHtml = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i>`;
  }

  showToast('A reanalisar o repositório com o Gemini...', 'info');

  try {
    const res = await fetch(`/api/repos/${id}/reanalyze`, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Falha ao reanalisar repositório');
    }
    const updated = await res.json();
    currentResult = updated;
    renderAnalysisResult(updated);
    showToast('Repositório reanalisado com sucesso!', 'success');
    loadHistory();
    loadCategories();
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
}

// Git Pull for Local Repository
async function gitPullRepo(id) {
  const btn = document.getElementById(`btn-pull-${id}`);
  const originalHtml = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin text-[10px]"></i><span>A atualizar...</span>`;
  }

  try {
    const res = await fetch(`/api/repos/${id}/git-pull`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Erro ao executar git pull');
    }
    showToast(data.message, 'success');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
}

// Check Git Status for Local Repository
async function gitStatusRepo(id) {
  try {
    const res = await fetch(`/api/repos/${id}/git-status`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Erro ao verificar atualizações');
    if (data.has_updates) {
      showToast(data.message, 'info');
    } else {
      showToast(data.message, 'success');
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ==================== SKILLS INSTALADOS ====================

let allSkills = [];

async function loadSkills(force = false) {
  const grid = document.getElementById('skills-grid');
  const countEl = document.getElementById('skills-count');

  if (allSkills.length === 0 || force) {
    grid.innerHTML = `
      <div class="col-span-full py-12 text-center text-slate-500">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-4 border-amber-500 border-t-transparent mb-2"></div>
        <p class="text-sm font-medium">A varrer o computador à procura de skills instalados...</p>
      </div>
    `;
    countEl.textContent = 'A carregar...';

    try {
      const res = await fetch('/api/skills');
      const data = await res.json();
      allSkills = data;

      // Populate source filter dropdown
      const sourceSelect = document.getElementById('filter-skill-source');
      const currentSource = sourceSelect.value;
      const sources = Array.from(new Set(data.map(s => s.source).filter(Boolean))).sort();

      sourceSelect.innerHTML = '<option value="">Todas as Origens</option>';
      sources.forEach(src => {
        const opt = document.createElement('option');
        opt.value = src;
        opt.textContent = src;
        if (src === currentSource) opt.selected = true;
        sourceSelect.appendChild(opt);
      });
    } catch (err) {
      grid.innerHTML = `<div class="col-span-full text-center text-rose-500 text-sm py-8">Erro ao carregar lista de skills.</div>`;
      return;
    }
  }

  handleSkillsFilter();
}

function handleSkillsFilter() {
  const query = (document.getElementById('skills-search-input')?.value || '').toLowerCase().trim();
  const program = (document.getElementById('filter-skill-program')?.value || '').toLowerCase().trim();
  const source = (document.getElementById('filter-skill-source')?.value || '').toLowerCase().trim();
  const model = (document.getElementById('filter-skill-model')?.value || '').toLowerCase().trim();

  const filtered = allSkills.filter(s => {
    if (program && (s.program || '').toLowerCase() !== program) return false;
    if (source && (s.source || '').toLowerCase() !== source) return false;
    if (model && !(s.target_model || '').toLowerCase().includes(model)) return false;
    if (query) {
      const inName = (s.name || '').toLowerCase().includes(query);
      const inDesc = (s.description || '').toLowerCase().includes(query);
      const inPlugin = s.plugin && s.plugin.toLowerCase().includes(query);
      const inSource = (s.source || '').toLowerCase().includes(query);
      const inModel = (s.target_model || '').toLowerCase().includes(query);
      if (!inName && !inDesc && !inPlugin && !inSource && !inModel) return false;
    }
    return true;
  });

  renderSkills(filtered);
}

function renderSkills(skills) {
  const grid = document.getElementById('skills-grid');
  const countEl = document.getElementById('skills-count');

  if (countEl) {
    countEl.textContent = `${skills.length} ${skills.length === 1 ? 'skill encontrado' : 'skills encontrados'}`;
  }

  if (skills.length === 0) {
    grid.innerHTML = `
      <div class="col-span-full py-12 text-center text-slate-400 bg-white rounded-2xl border border-slate-200">
        <i class="fa-solid fa-bolt text-3xl mb-2 text-slate-300"></i>
        <p class="text-sm font-medium">Nenhum skill encontrado com os filtros selecionados.</p>
      </div>
    `;
    return;
  }

  grid.innerHTML = skills.map(s => {
    const isOpencode = s.program === 'OpenCode';
    const programBadgeClass = isOpencode ? 'badge-program-opencode' : 'badge-program-antigravity';
    const programIcon = isOpencode ? 'fa-solid fa-terminal' : 'fa-solid fa-brain';

    const targetModel = s.target_model || 'Claude';
    const modelBadgeClass = getModelBadgeClass(targetModel);

    const safePath = escapeJsStr(s.file_path);
    const safeName = escapeJsStr(s.name);
    const safeProgram = escapeJsStr(s.program || 'Google Antigravity');
    const safeSource = escapeJsStr(s.source || '');
    const safeDesc = escapeJsStr(s.description || '');
    const safeModel = escapeJsStr(targetModel);
    const safeId = escapeJsStr(s.id);

    const customBadgeHtml = s.is_custom 
      ? `<span class="inline-block px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-200/60">Personalizado</span>` 
      : '';

    return `
      <div class="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex flex-col justify-between hover:border-slate-300 transition-all">
        <div>
          <div class="flex items-start justify-between gap-2 mb-2">
            <h4 class="font-bold text-slate-900 text-sm break-all">
              ${escapeHtml(s.name)}
            </h4>
            <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold shrink-0 ${programBadgeClass}">
              <i class="${programIcon} text-[10px]"></i>
              ${escapeHtml(s.program)}
            </span>
          </div>

          <div class="flex flex-wrap items-center gap-1.5 mb-2.5">
            <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full border shrink-0 ${modelBadgeClass}">
              ${escapeHtml(targetModel)}
            </span>
            ${customBadgeHtml}
            <span class="inline-block px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600 truncate max-w-[170px]" title="${escapeHtml(s.source)}">
              ${escapeHtml(s.source)}
            </span>
          </div>

          <p class="text-xs text-slate-600 line-clamp-3 leading-relaxed mb-4">
            ${escapeHtml(s.description)}
          </p>
        </div>

        <div class="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-1.5">
            <button 
              onclick="openSkillDetailModal('${safePath}', '${safeName}', '${safeProgram}', '${safeSource}')"
              class="px-2.5 py-1 text-xs text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg font-medium shrink-0 flex items-center gap-1 transition-colors cursor-pointer"
            >
              <i class="fa-solid fa-file-lines text-[10px]"></i>
              <span>Instruções</span>
            </button>
            <button 
              onclick="openConvertSkillModal('${safeId}', '${safeModel}', '${safeName}', '${safePath}')"
              class="px-2.5 py-1 text-xs text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200/60 rounded-lg font-medium shrink-0 flex items-center gap-1 transition-colors cursor-pointer"
            >
              <i class="fa-solid fa-wand-magic-sparkles text-[10px]"></i>
              <span>Converter</span>
            </button>
          </div>

          <div class="flex items-center gap-1">
            <button 
              onclick="openEditSkillModal('${safeId}', '${safeName}', '${safeModel}', '${safeProgram}', '${safeDesc}', '${safePath}')"
              class="p-1.5 text-slate-500 hover:text-indigo-600 rounded-lg transition-colors cursor-pointer" 
              title="Editar"
            >
              <i class="fa-regular fa-pen-to-square text-xs"></i>
            </button>
            ${s.is_custom ? `
              <button 
                onclick="handleDeleteCustomSkill('${safeId}')" 
                class="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg transition-colors cursor-pointer" 
                title="Eliminar"
              >
                <i class="fa-regular fa-trash-can text-xs"></i>
              </button>
            ` : ''}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

async function openSkillDetailModal(filePath, name, program, source) {
  const modal = document.getElementById('skill-detail-modal');
  modal.classList.remove('hidden');

  document.getElementById('skill-modal-title').textContent = name;
  document.getElementById('skill-modal-path').textContent = filePath;

  const progEl = document.getElementById('skill-modal-program');
  progEl.textContent = program;
  progEl.className = `text-xs font-semibold px-2.5 py-0.5 rounded-full ${program === 'OpenCode' ? 'badge-program-opencode' : 'badge-program-antigravity'}`;

  document.getElementById('skill-modal-source').textContent = source;

  const contentEl = document.getElementById('skill-modal-content');
  const loadingEl = document.getElementById('skill-modal-loading');

  contentEl.textContent = '';
  loadingEl.classList.remove('hidden');

  try {
    const res = await fetch(`/api/skills/content?path=${encodeURIComponent(filePath)}`);
    const data = await res.json();
    if (res.ok) {
      contentEl.textContent = data.content;
    } else {
      contentEl.textContent = data.detail || 'Erro ao carregar conteúdo do skill.';
    }
  } catch (err) {
    contentEl.textContent = 'Erro ao carregar instruções.';
  } finally {
    loadingEl.classList.add('hidden');
  }
}

function closeSkillDetailModal() {
  const modal = document.getElementById('skill-detail-modal');
  modal.classList.add('hidden');
}

// ==================== WORKSPACE (OS MEUS PROJETOS, PROMPTS & SKILLS) ====================

let currentProjectsSubTab = 'code';

function switchProjectsSubTab(subTab) {
  currentProjectsSubTab = subTab;

  document.querySelectorAll('.projects-subview').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.projects-subtab-btn').forEach(el => {
    el.classList.remove('active', 'bg-indigo-600', 'text-white', 'shadow-xs');
    el.classList.add('bg-slate-100', 'text-slate-700');
  });

  const activeView = document.getElementById(`projects-subview-${subTab}`);
  const activeBtn = document.getElementById(`projects-subtab-${subTab}-btn`);

  if (activeView) activeView.classList.remove('hidden');
  if (activeBtn) {
    activeBtn.classList.remove('bg-slate-100', 'text-slate-700');
    activeBtn.classList.add('active', 'bg-indigo-600', 'text-white', 'shadow-xs');
  }

  if (subTab === 'code') {
    loadMyProjects();
  } else if (subTab === 'prompts') {
    loadMyWorkspacePrompts();
  } else if (subTab === 'skills') {
    loadMyWorkspaceSkills();
  }
  updateProjectsTabBadges();
}

function refreshCurrentProjectsSubTab() {
  const icon = document.getElementById('projects-subtab-refresh-icon');
  if (icon) icon.classList.add('animate-spin');
  if (currentProjectsSubTab === 'code') {
    loadMyProjects();
  } else if (currentProjectsSubTab === 'prompts') {
    loadMyWorkspacePrompts();
  } else if (currentProjectsSubTab === 'skills') {
    loadMyWorkspaceSkills();
  }
  updateProjectsTabBadges();
  setTimeout(() => {
    if (icon) icon.classList.remove('animate-spin');
  }, 500);
}

async function updateProjectsTabBadges() {
  try {
    const [resProj, resPrompts, resSkills] = await Promise.all([
      fetch('/api/my-projects').then(r => r.ok ? r.json() : []),
      fetch('/api/prompts').then(r => r.ok ? r.json() : []),
      fetch('/api/skills/my').then(r => r.ok ? r.json() : [])
    ]);

    const projCount = Array.isArray(resProj) ? resProj.length : 0;
    const promptsCount = Array.isArray(resPrompts) ? resPrompts.length : 0;
    const skillsCount = Array.isArray(resSkills) ? resSkills.length : 0;

    const bProj = document.getElementById('my-projects-count-badge');
    if (bProj) bProj.textContent = projCount;

    const bPrompts = document.getElementById('my-prompts-count-badge');
    if (bPrompts) bPrompts.textContent = promptsCount;

    const bSkills = document.getElementById('my-skills-count-badge');
    if (bSkills) bSkills.textContent = skillsCount;
  } catch (e) {
    // Non-critical background update
  }
}

// 1. Prompts do Utilizador no Espaço de Trabalho
let myWorkspacePromptsData = [];

async function loadMyWorkspacePrompts() {
  const grid = document.getElementById('my-prompts-grid');
  const countStatus = document.getElementById('my-prompts-status-count');
  if (!grid) return;

  grid.innerHTML = `
    <div class="col-span-full py-12 text-center text-slate-500">
      <div class="inline-block animate-spin rounded-full h-7 w-7 border-3 border-emerald-500 border-t-transparent mb-2"></div>
      <p class="text-xs font-medium">A carregar os teus prompts...</p>
    </div>
  `;

  try {
    const res = await fetch('/api/prompts?sort_by=date&sort_order=desc');
    const data = await res.json();
    myWorkspacePromptsData = Array.isArray(data) ? data : [];
    filterMyWorkspacePrompts();
    updateProjectsTabBadges();
  } catch (err) {
    grid.innerHTML = `<div class="col-span-full text-center text-rose-500 text-xs py-8">Erro ao carregar prompts.</div>`;
  }
}

function filterMyWorkspacePrompts() {
  const query = (document.getElementById('my-prompts-search-input')?.value || '').toLowerCase().trim();
  const model = (document.getElementById('my-prompts-filter-model')?.value || '').toLowerCase().trim();
  const grid = document.getElementById('my-prompts-grid');
  const countStatus = document.getElementById('my-prompts-status-count');
  if (!grid) return;

  const filtered = myWorkspacePromptsData.filter(p => {
    if (model && !(p.target_model || '').toLowerCase().includes(model)) return false;
    if (query) {
      const inAct = (p.act || '').toLowerCase().includes(query);
      const inPrompt = (p.prompt || '').toLowerCase().includes(query);
      const inCat = (p.category || '').toLowerCase().includes(query);
      if (!inAct && !inPrompt && !inCat) return false;
    }
    return true;
  });

  if (countStatus) {
    countStatus.textContent = `${filtered.length} ${filtered.length === 1 ? 'prompt' : 'prompts'}`;
  }

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div class="col-span-full py-12 text-center text-slate-400 bg-white rounded-2xl border border-slate-200">
        <i class="fa-solid fa-comment-dots text-3xl mb-2 text-slate-300"></i>
        <p class="text-xs sm:text-sm font-medium">Nenhum prompt encontrado no teu espaço.</p>
        <p class="text-[11px] text-slate-400 mt-1">Clica em "Criar Novo Prompt" para adicionar o teu primeiro.</p>
      </div>
    `;
    return;
  }

  grid.innerHTML = filtered.map(p => {
    const targetModel = p.target_model || 'ChatGPT (OpenAI)';
    const modelBadgeClass = getModelBadgeClass(targetModel);
    const safeAct = escapeJsStr(p.act);
    const safePrompt = escapeJsStr(p.prompt);
    const safeCat = escapeJsStr(p.category || 'Geral');
    const safeModel = escapeJsStr(targetModel);

    return `
      <div class="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex flex-col justify-between hover:border-slate-300 transition-all">
        <div>
          <div class="flex items-start justify-between gap-2 mb-2">
            <h4 class="font-bold text-slate-900 text-sm flex items-center gap-1.5 break-all">
              <i class="fa-solid fa-robot text-emerald-600 text-xs shrink-0"></i>
              <span>${escapeHtml(p.act)}</span>
            </h4>
            <span class="text-[11px] font-semibold px-2.5 py-0.5 rounded-full border shrink-0 ${modelBadgeClass}">
              ${escapeHtml(targetModel)}
            </span>
          </div>

          <div class="flex items-center gap-2 mb-3">
            <span class="inline-block px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600">
              ${escapeHtml(p.category || 'Geral')}
            </span>
            <span class="text-[10px] text-slate-400">${formatDate(p.created_at)}</span>
          </div>

          <div class="bg-slate-50 rounded-xl p-3 border border-slate-100 text-xs font-mono text-slate-700 leading-relaxed mb-4 max-h-36 overflow-y-auto whitespace-pre-wrap select-all">
            ${escapeHtml(p.prompt)}
          </div>
        </div>

        <div class="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-1.5">
            <button 
              onclick="copyToClipboard('${safePrompt}')" 
              class="px-2.5 py-1 text-xs text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg font-medium flex items-center gap-1 transition-colors cursor-pointer"
            >
              <i class="fa-regular fa-copy text-[11px]"></i>
              <span>Copiar</span>
            </button>
            <button 
              onclick="openConvertPromptModal(${p.id}, '${safeModel}', '${safeAct}', '${safeCat}')" 
              class="px-2.5 py-1 text-xs text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200/60 rounded-lg font-medium flex items-center gap-1 transition-colors cursor-pointer"
            >
              <i class="fa-solid fa-wand-magic-sparkles text-[11px]"></i>
              <span>Converter</span>
            </button>
          </div>

          <div class="flex items-center gap-1.5">
            <button 
              onclick="openEditPromptModal(${p.id})" 
              class="p-1.5 text-slate-500 hover:text-indigo-600 rounded-lg transition-colors cursor-pointer" 
              title="Editar"
            >
              <i class="fa-regular fa-pen-to-square text-xs"></i>
            </button>
            <button 
              onclick="handleDeletePrompt(${p.id})" 
              class="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg transition-colors cursor-pointer" 
              title="Eliminar"
            >
              <i class="fa-regular fa-trash-can text-xs"></i>
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// 2. Skills do Utilizador no Espaço de Trabalho
let myWorkspaceSkillsData = [];

async function loadMyWorkspaceSkills() {
  const grid = document.getElementById('my-skills-grid');
  const countStatus = document.getElementById('my-skills-status-count');
  if (!grid) return;

  grid.innerHTML = `
    <div class="col-span-full py-12 text-center text-slate-500">
      <div class="inline-block animate-spin rounded-full h-7 w-7 border-3 border-amber-500 border-t-transparent mb-2"></div>
      <p class="text-xs font-medium">A carregar os teus skills...</p>
    </div>
  `;

  try {
    const res = await fetch('/api/skills/my');
    const data = await res.json();
    myWorkspaceSkillsData = Array.isArray(data) ? data : [];
    filterMyWorkspaceSkills();
    updateProjectsTabBadges();
  } catch (err) {
    grid.innerHTML = `<div class="col-span-full text-center text-rose-500 text-xs py-8">Erro ao carregar os teus skills.</div>`;
  }
}

function filterMyWorkspaceSkills() {
  const query = (document.getElementById('my-skills-search-input')?.value || '').toLowerCase().trim();
  const model = (document.getElementById('my-skills-filter-model')?.value || '').toLowerCase().trim();
  const grid = document.getElementById('my-skills-grid');
  const countStatus = document.getElementById('my-skills-status-count');
  if (!grid) return;

  const filtered = myWorkspaceSkillsData.filter(s => {
    if (model && !(s.target_model || '').toLowerCase().includes(model)) return false;
    if (query) {
      const inName = (s.name || '').toLowerCase().includes(query);
      const inDesc = (s.description || '').toLowerCase().includes(query);
      if (!inName && !inDesc) return false;
    }
    return true;
  });

  if (countStatus) {
    countStatus.textContent = `${filtered.length} ${filtered.length === 1 ? 'skill' : 'skills'}`;
  }

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div class="col-span-full py-12 text-center text-slate-400 bg-white rounded-2xl border border-slate-200">
        <i class="fa-solid fa-bolt text-3xl mb-2 text-slate-300"></i>
        <p class="text-xs sm:text-sm font-medium">Ainda não tens skills personalizados ou editados por ti.</p>
        <p class="text-[11px] text-slate-400 mt-1">Clica em "Criar Novo Skill" ou explora a aba "Skills" para converter e guardar qualquer skill nativo.</p>
      </div>
    `;
    return;
  }

  grid.innerHTML = filtered.map(s => {
    const targetModel = s.target_model || 'Claude';
    const modelBadgeClass = getModelBadgeClass(targetModel);
    const safePath = escapeJsStr(s.file_path || '');
    const safeName = escapeJsStr(s.name);
    const safeProgram = escapeJsStr(s.program || 'Google Antigravity');
    const safeSource = escapeJsStr(s.source || 'Antigravity (Personalizado)');
    const safeDesc = escapeJsStr(s.description || '');
    const safeModel = escapeJsStr(targetModel);
    const safeId = escapeJsStr(s.id);

    return `
      <div class="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex flex-col justify-between hover:border-slate-300 transition-all">
        <div>
          <div class="flex items-start justify-between gap-2 mb-2">
            <h4 class="font-bold text-slate-900 text-sm flex items-center gap-1.5 break-all">
              <i class="fa-solid fa-bolt text-amber-500 text-xs shrink-0"></i>
              <span>${escapeHtml(s.name)}</span>
            </h4>
            <span class="text-[11px] font-semibold px-2.5 py-0.5 rounded-full border shrink-0 ${modelBadgeClass}">
              ${escapeHtml(targetModel)}
            </span>
          </div>

          <div class="flex items-center gap-2 mb-3">
            <span class="inline-block px-2 py-0.5 rounded text-[10px] font-medium bg-amber-50 text-amber-800 border border-amber-200/60">
              Personalizado
            </span>
            <span class="inline-block px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600">
              ${escapeHtml(s.program || 'Google Antigravity')}
            </span>
          </div>

          <p class="text-xs text-slate-600 line-clamp-3 leading-relaxed mb-4">
            ${escapeHtml(s.description)}
          </p>
        </div>

        <div class="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-1.5">
            <button 
              onclick="openSkillDetailModal('${safePath}', '${safeName}', '${safeProgram}', '${safeSource}')" 
              class="px-2.5 py-1 text-xs text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg font-medium flex items-center gap-1 transition-colors cursor-pointer"
            >
              <i class="fa-solid fa-file-lines text-[10px]"></i>
              <span>Instruções</span>
            </button>
            <button 
              onclick="openConvertSkillModal('${safeId}', '${safeModel}', '${safeName}', '${safePath}')" 
              class="px-2.5 py-1 text-xs text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200/60 rounded-lg font-medium flex items-center gap-1 transition-colors cursor-pointer"
            >
              <i class="fa-solid fa-wand-magic-sparkles text-[10px]"></i>
              <span>Converter</span>
            </button>
          </div>

          <div class="flex items-center gap-1.5">
            <button 
              onclick="openEditSkillModal('${safeId}', '${safeName}', '${safeModel}', '${safeProgram}', '${safeDesc}', '${safePath}')" 
              class="p-1.5 text-slate-500 hover:text-indigo-600 rounded-lg transition-colors cursor-pointer" 
              title="Editar"
            >
              <i class="fa-regular fa-pen-to-square text-xs"></i>
            </button>
            <button 
              onclick="handleDeleteCustomSkill('${safeId}')" 
              class="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg transition-colors cursor-pointer" 
              title="Eliminar"
            >
              <i class="fa-regular fa-trash-can text-xs"></i>
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// 3. Gestão e Modais de Skills (Criar, Editar, Eliminar)
function openCreateSkillModal() {
  document.getElementById('skill-edit-modal-title').innerHTML = `
    <i class="fa-solid fa-bolt text-amber-500"></i>
    <span>Criar Novo Skill</span>
  `;
  document.getElementById('skill-edit-id').value = '';
  document.getElementById('skill-edit-filepath').value = '';
  document.getElementById('skill-edit-name').value = '';
  document.getElementById('skill-edit-desc').value = '';
  document.getElementById('skill-edit-model').value = 'Claude';
  document.getElementById('skill-edit-program').value = 'Google Antigravity';
  document.getElementById('skill-edit-content').value = `# Instruções do Skill\n\nDescreve aqui as capacidades, passos e diretrizes para o agente executar...`;

  document.getElementById('skill-edit-modal').classList.remove('hidden');
}

async function openEditSkillModal(skillId, name, model, program, desc, filePath) {
  document.getElementById('skill-edit-modal-title').innerHTML = `
    <i class="fa-solid fa-pen-to-square text-indigo-600"></i>
    <span>Editar Skill</span>
  `;
  document.getElementById('skill-edit-id').value = skillId || '';
  document.getElementById('skill-edit-filepath').value = filePath || '';
  document.getElementById('skill-edit-name').value = name || '';
  document.getElementById('skill-edit-desc').value = desc || '';
  document.getElementById('skill-edit-model').value = model || 'Claude';
  document.getElementById('skill-edit-program').value = program || 'Google Antigravity';

  const contentTextarea = document.getElementById('skill-edit-content');
  contentTextarea.value = 'A carregar instruções...';

  document.getElementById('skill-edit-modal').classList.remove('hidden');

  if (filePath) {
    try {
      const res = await fetch(`/api/skills/content?path=${encodeURIComponent(filePath)}`);
      const data = await res.json();
      if (res.ok && data.content) {
        contentTextarea.value = data.content;
      } else {
        contentTextarea.value = `# ${name}\n\n${desc}`;
      }
    } catch (e) {
      contentTextarea.value = `# ${name}\n\n${desc}`;
    }
  } else {
    contentTextarea.value = `# ${name}\n\n${desc}`;
  }
}

function closeSkillEditModal() {
  document.getElementById('skill-edit-modal').classList.add('hidden');
}

async function handleSkillEditSubmit(event) {
  event.preventDefault();
  const skillId = document.getElementById('skill-edit-id').value;
  const filePath = document.getElementById('skill-edit-filepath').value;
  const name = document.getElementById('skill-edit-name').value.trim();
  const description = document.getElementById('skill-edit-desc').value.trim();
  const target_model = document.getElementById('skill-edit-model').value;
  const program = document.getElementById('skill-edit-program').value;
  const content = document.getElementById('skill-edit-content').value.trim();

  if (!name || !description || !content) {
    showToast('Por favor, preenche todos os campos obrigatórios.', 'error');
    return;
  }

  const btn = document.getElementById('skill-edit-submit-btn');
  const originalHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> <span>A guardar...</span>`;

  try {
    let res;
    if (skillId) {
      res = await fetch(`/api/skills/${encodeURIComponent(skillId)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description, content, target_model, program, file_path: filePath })
      });
    } else {
      res = await fetch('/api/skills', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description, content, target_model, program })
      });
    }

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Erro ao guardar skill.');

    showToast(skillId ? 'Skill atualizado com sucesso!' : 'Novo skill criado com sucesso!');
    closeSkillEditModal();

    loadSkills(true);
    if (currentProjectsSubTab === 'skills') {
      loadMyWorkspaceSkills();
    }
    updateProjectsTabBadges();
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
  }
}

async function handleDeleteCustomSkill(skillId) {
  if (!confirm('Tens a certeza de que queres eliminar este skill personalizado?')) {
    return;
  }

  try {
    const res = await fetch(`/api/skills/${encodeURIComponent(skillId)}`, {
      method: 'DELETE'
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Erro ao eliminar skill.');

    showToast('Skill eliminado com sucesso.');
    loadSkills(true);
    loadMyWorkspaceSkills();
    updateProjectsTabBadges();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 4. Conversão de Skills para Outros Modelos
let currentConvertingSkill = null;
let currentConvertingSkillContent = '';
let selectedSkillTargetModel = 'Google Gemini';

async function openConvertSkillModal(skillId, currentModel, skillName, filePath) {
  currentConvertingSkill = { skillId, currentModel, skillName, filePath };
  currentConvertingSkillContent = '';

  document.getElementById('skill-convert-name').textContent = skillName;
  document.getElementById('skill-convert-current-model-badge').textContent = currentModel || 'Claude';

  // Opções de modelos principais disponíveis
  const allModels = [
    { id: 'Claude', name: 'Claude (Anthropic)', desc: 'Tags XML, raciocínio detalhado', icon: 'fa-brain', color: 'text-amber-800', border: 'hover:border-amber-400' },
    { id: 'Google Gemini', name: 'Google Gemini', desc: 'Markdown claro e contextual', icon: 'fa-sparkles', color: 'text-blue-700', border: 'hover:border-blue-400' },
    { id: 'ChatGPT', name: 'ChatGPT (OpenAI)', desc: 'Personas, contexto e tom', icon: 'fa-robot', color: 'text-emerald-700', border: 'hover:border-emerald-400' },
    { id: 'DeepSeek', name: 'DeepSeek', desc: 'Raciocínio lógico e código denso', icon: 'fa-code', color: 'text-purple-700', border: 'hover:border-purple-400' },
    { id: 'Mistral AI', name: 'Mistral AI', desc: 'Instruções compactas e objetivas', icon: 'fa-bolt', color: 'text-orange-700', border: 'hover:border-orange-400' },
    { id: 'xAI Grok', name: 'xAI Grok', desc: 'Direto, analítico e sem rodeios', icon: 'fa-microchip', color: 'text-cyan-700', border: 'hover:border-cyan-400' }
  ];

  // Excluir o modelo atual do skill
  const curLower = (currentModel || '').toLowerCase();
  const availableTargets = allModels.filter(m => !curLower.includes(m.id.toLowerCase()));

  selectedSkillTargetModel = availableTargets[0] ? availableTargets[0].name : 'Google Gemini';

  const container = document.getElementById('skill-convert-model-options');
  container.innerHTML = availableTargets.map((m, idx) => {
    const isSelected = idx === 0;
    return `
      <button 
        type="button" 
        onclick="selectConvertSkillTargetModel('${escapeJsStr(m.name)}')" 
        class="skill-convert-model-btn p-2.5 rounded-xl text-left transition-all cursor-pointer flex flex-col gap-1 ${isSelected ? 'border-2 border-indigo-600 bg-indigo-50/40' : 'border border-slate-200 ' + m.border + ' bg-white'}" 
        data-model="${escapeHtml(m.name)}"
      >
        <span class="text-xs font-bold ${m.color} flex items-center gap-1.5">
          <i class="fa-solid ${m.icon} text-[11px]"></i> ${escapeHtml(m.id)}
        </span>
        <span class="text-[10px] text-slate-500">${escapeHtml(m.desc)}</span>
      </button>
    `;
  }).join('');

  document.getElementById('skill-convert-result-box').classList.add('hidden');
  document.getElementById('skill-convert-loading-state').classList.add('hidden');
  document.getElementById('skill-convert-result-textarea').value = '';

  document.getElementById('skill-convert-modal').classList.remove('hidden');

  // Pre-carregar conteúdo do skill
  if (filePath) {
    try {
      const res = await fetch(`/api/skills/content?path=${encodeURIComponent(filePath)}`);
      const data = await res.json();
      if (res.ok && data.content) {
        currentConvertingSkillContent = data.content;
      }
    } catch (e) {
      currentConvertingSkillContent = '';
    }
  }
}

function closeSkillConvertModal() {
  document.getElementById('skill-convert-modal').classList.add('hidden');
}

function selectConvertSkillTargetModel(modelName) {
  selectedSkillTargetModel = modelName;
  document.querySelectorAll('.skill-convert-model-btn').forEach(btn => {
    if (btn.getAttribute('data-model') === modelName) {
      btn.className = 'skill-convert-model-btn p-2.5 rounded-xl text-left transition-all cursor-pointer flex flex-col gap-1 border-2 border-indigo-600 bg-indigo-50/40';
    } else {
      btn.className = 'skill-convert-model-btn p-2.5 rounded-xl text-left transition-all cursor-pointer flex flex-col gap-1 border border-slate-200 hover:border-slate-400 bg-white';
    }
  });
}

async function handleExecuteSkillConversion() {
  if (!currentConvertingSkill) return;

  const btn = document.getElementById('btn-execute-skill-conversion');
  const btnText = document.getElementById('btn-execute-skill-conversion-text');
  const loading = document.getElementById('skill-convert-loading-state');
  const resultBox = document.getElementById('skill-convert-result-box');
  const textarea = document.getElementById('skill-convert-result-textarea');
  const badge = document.getElementById('skill-convert-result-model-badge');

  btn.disabled = true;
  btnText.textContent = 'A otimizar com IA...';
  loading.classList.remove('hidden');
  resultBox.classList.add('hidden');

  let contentToConvert = currentConvertingSkillContent;
  if (!contentToConvert && currentConvertingSkill.filePath) {
    try {
      const res = await fetch(`/api/skills/content?path=${encodeURIComponent(currentConvertingSkill.filePath)}`);
      const data = await res.json();
      if (res.ok && data.content) {
        contentToConvert = data.content;
      }
    } catch (e) {}
  }

  if (!contentToConvert) {
    contentToConvert = `# ${currentConvertingSkill.skillName}\n\nInstruções do skill.`;
  }

  try {
    const res = await fetch('/api/skills/convert', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        skill_content: contentToConvert,
        skill_name: currentConvertingSkill.skillName,
        current_model: currentConvertingSkill.currentModel,
        target_model: selectedSkillTargetModel
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Erro ao converter skill.');

    textarea.value = data.converted_skill || contentToConvert;
    badge.textContent = selectedSkillTargetModel;
    badge.className = `text-[11px] font-semibold px-2 py-0.5 rounded-full border ${getModelBadgeClass(selectedSkillTargetModel)}`;
    resultBox.classList.remove('hidden');
    showToast(`Skill adaptado para ${selectedSkillTargetModel}!`);
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    loading.classList.add('hidden');
    btn.disabled = false;
    btnText.textContent = 'Converter Skill com IA';
  }
}

async function copyConvertedSkillText() {
  const text = document.getElementById('skill-convert-result-textarea').value;
  if (!text) return;
  await copyToClipboard(text, 'Conteúdo do skill copiado!');
}

async function saveConvertedSkillToLibrary() {
  if (!currentConvertingSkill) return;
  const content = document.getElementById('skill-convert-result-textarea').value.trim();
  if (!content) {
    showToast('Não há conteúdo convertido para guardar.', 'error');
    return;
  }

  const shortModel = selectedSkillTargetModel.split(' ')[0];
  const newName = `${currentConvertingSkill.skillName}-${shortModel.toLowerCase()}`;
  const desc = `Versão otimizada para ${selectedSkillTargetModel}`;

  try {
    const res = await fetch('/api/skills', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: newName,
        description: desc,
        content: content,
        target_model: selectedSkillTargetModel,
        program: 'Google Antigravity'
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Erro ao guardar skill.');

    showToast(`Guardado como "${newName}" nos Meus Skills!`);
    closeSkillConvertModal();
    loadSkills(true);
    if (currentProjectsSubTab !== 'skills') {
      switchProjectsSubTab('skills');
    } else {
      loadMyWorkspaceSkills();
    }
    updateProjectsTabBadges();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ==================== GLOBAL SEARCH (CTRL+K) ====================

let globalSearchData = {
  repos: [],
  projects: [],
  skills: [],
  loaded: false
};
let searchFilterType = 'all'; // 'all', 'repos', 'projects', 'skills'
let selectedResultIndex = -1;
let currentFilteredResults = [];

async function prefetchSearchData(force = false) {
  if (globalSearchData.loaded && !force) return;
  try {
    const [reposRes, projsRes, skillsRes] = await Promise.all([
      fetch('/api/repos').then(r => r.ok ? r.json() : []).catch(() => []),
      fetch('/api/my-projects').then(r => r.ok ? r.json() : []).catch(() => []),
      fetch('/api/skills').then(r => r.ok ? r.json() : []).catch(() => [])
    ]);
    globalSearchData = {
      repos: reposRes || [],
      projects: projsRes || [],
      skills: skillsRes || [],
      loaded: true
    };
  } catch (err) {
    console.error('Erro ao pré-carregar dados de pesquisa:', err);
  }
}

function openGlobalSearch() {
  const modal = document.getElementById('global-search-modal');
  if (!modal) return;
  modal.classList.remove('hidden');

  prefetchSearchData();

  const input = document.getElementById('global-search-input');
  if (input) {
    input.value = '';
    input.focus();
  }
  selectedResultIndex = -1;
  renderGlobalSearchResults([]);
}

function closeGlobalSearch() {
  const modal = document.getElementById('global-search-modal');
  if (modal) modal.classList.add('hidden');
}

function handleSearchBackdropClick(event) {
  if (event.target && event.target.id === 'global-search-modal') {
    closeGlobalSearch();
  }
}

function setSearchFilter(type) {
  searchFilterType = type;
  const buttons = ['all', 'repos', 'projects', 'skills'];
  buttons.forEach(b => {
    const btn = document.getElementById(`search-filter-${b}`);
    if (!btn) return;
    if (b === type) {
      btn.className = 'px-2.5 py-1 rounded-lg font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 shrink-0';
    } else {
      btn.className = 'px-2.5 py-1 rounded-lg font-medium text-slate-600 hover:bg-slate-100 border border-transparent shrink-0';
    }
  });
  executeGlobalSearch();
}

function executeGlobalSearch() {
  const input = document.getElementById('global-search-input');
  const query = (input ? input.value : '').toLowerCase().trim();

  let results = [];

  // Search in Repositories
  if (searchFilterType === 'all' || searchFilterType === 'repos') {
    globalSearchData.repos.forEach(r => {
      const name = (r.name || '').toLowerCase();
      const desc = (r.description_simple || '').toLowerCase();
      const cat = (r.category || '').toLowerCase();
      const useCases = (r.use_cases || []).join(' ').toLowerCase();

      let match = false;
      if (!query) {
        match = true;
      } else if (name.includes(query) || desc.includes(query) || cat.includes(query) || useCases.includes(query)) {
        match = true;
      }

      if (match) {
        results.push({
          type: 'repo',
          id: r.id,
          title: r.name,
          badge: r.category || 'Repositório',
          badgeClass: 'bg-indigo-100 text-indigo-800',
          desc: r.description_simple || 'Sem descrição.',
          icon: 'fa-brands fa-github text-indigo-600',
          action: () => {
            closeGlobalSearch();
            viewRepoDetails(r.id);
          }
        });
      }
    });
  }

  // Search in My Projects
  if (searchFilterType === 'all' || searchFilterType === 'projects') {
    globalSearchData.projects.forEach(p => {
      const name = (p.name || '').toLowerCase();
      const summary = (p.summary || '').toLowerCase();
      const path = (p.path || '').toLowerCase();
      const techs = (p.technologies || []).join(' ').toLowerCase();

      let match = false;
      if (!query) {
        match = true;
      } else if (name.includes(query) || summary.includes(query) || path.includes(query) || techs.includes(query)) {
        match = true;
      }

      if (match) {
        results.push({
          type: 'project',
          id: p.id,
          title: p.name,
          badge: p.status || 'Projeto',
          badgeClass: 'bg-emerald-100 text-emerald-800',
          desc: p.summary || p.path,
          icon: 'fa-solid fa-diagram-project text-emerald-600',
          action: () => {
            closeGlobalSearch();
            switchTab('projects');
          }
        });
      }
    });
  }

  // Search in Skills
  if (searchFilterType === 'all' || searchFilterType === 'skills') {
    globalSearchData.skills.forEach(s => {
      const name = (s.name || '').toLowerCase();
      const desc = (s.description || '').toLowerCase();
      const prog = (s.program || '').toLowerCase();
      const plugin = (s.plugin || '').toLowerCase();

      let match = false;
      if (!query) {
        match = true;
      } else if (name.includes(query) || desc.includes(query) || prog.includes(query) || plugin.includes(query)) {
        match = true;
      }

      if (match) {
        results.push({
          type: 'skill',
          title: s.name,
          badge: s.program || 'Skill',
          badgeClass: s.program === 'OpenCode' ? 'bg-emerald-100 text-emerald-800' : 'bg-indigo-100 text-indigo-800',
          desc: s.description || 'Sem descrição.',
          icon: 'fa-solid fa-bolt text-amber-500',
          action: () => {
            closeGlobalSearch();
            openSkillDetailModal(s.file_path, s.name, s.program, s.source);
          }
        });
      }
    });
  }

  // Limit results to 40 for optimal rendering performance
  currentFilteredResults = results.slice(0, 40);
  selectedResultIndex = currentFilteredResults.length > 0 ? 0 : -1;
  renderGlobalSearchResults(currentFilteredResults);
}

function renderGlobalSearchResults(results) {
  const container = document.getElementById('global-search-results');
  const countEl = document.getElementById('global-search-count');
  if (!container) return;

  if (countEl) {
    countEl.textContent = `${results.length} ${results.length === 1 ? 'resultado' : 'resultados'}`;
  }

  if (results.length === 0) {
    container.innerHTML = `
      <div class="py-10 text-center text-slate-400">
        <i class="fa-solid fa-magnifying-glass text-2xl mb-2 text-slate-300"></i>
        <p class="text-xs sm:text-sm font-medium">Nenhum resultado encontrado.</p>
        <p class="text-[11px] text-slate-400 mt-0.5">Tenta pesquisar por outra palavra-chave ou seleciona outro filtro.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = results.map((item, idx) => {
    const isSelected = idx === selectedResultIndex;
    const bgClass = isSelected ? 'bg-indigo-50/80 border-indigo-200' : 'hover:bg-slate-50 border-transparent';

    return `
      <div 
        id="search-res-item-${idx}"
        onclick="executeSearchResult(${idx})"
        class="p-2.5 sm:p-3 rounded-xl cursor-pointer transition-all border ${bgClass} flex items-center justify-between gap-3 group"
      >
        <div class="flex items-start gap-3 min-w-0">
          <div class="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center shrink-0 mt-0.5 group-hover:scale-105 transition-transform">
            <i class="${item.icon} text-sm"></i>
          </div>
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <span class="text-xs sm:text-sm font-bold text-slate-900 truncate">${escapeHtml(item.title)}</span>
              <span class="text-[10px] font-semibold px-2 py-0.5 rounded-full ${item.badgeClass} shrink-0">
                ${escapeHtml(item.badge)}
              </span>
            </div>
            <p class="text-[11px] sm:text-xs text-slate-500 line-clamp-1 mt-0.5">
              ${escapeHtml(item.desc)}
            </p>
          </div>
        </div>
        <i class="fa-solid fa-arrow-right text-slate-300 group-hover:text-indigo-600 text-xs shrink-0 transition-colors"></i>
      </div>
    `;
  }).join('');
}

function executeSearchResult(index) {
  if (index >= 0 && index < currentFilteredResults.length) {
    currentFilteredResults[index].action();
  }
}

// Global Keyboard Shortcuts (Ctrl+K and Escape)
document.addEventListener('keydown', (e) => {
  // Toggle with Ctrl+K or Cmd+K
  if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
    e.preventDefault();
    const modal = document.getElementById('global-search-modal');
    if (modal && !modal.classList.contains('hidden')) {
      closeGlobalSearch();
    } else {
      openGlobalSearch();
    }
    return;
  }

  const modal = document.getElementById('global-search-modal');
  if (!modal || modal.classList.contains('hidden')) return;

  // Escape to close
  if (e.key === 'Escape') {
    e.preventDefault();
    closeGlobalSearch();
    return;
  }

  // Arrow Down
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    if (currentFilteredResults.length > 0) {
      selectedResultIndex = (selectedResultIndex + 1) % currentFilteredResults.length;
      updateSearchResultSelection();
    }
    return;
  }

  // Arrow Up
  if (e.key === 'ArrowUp') {
    e.preventDefault();
    if (currentFilteredResults.length > 0) {
      selectedResultIndex = (selectedResultIndex - 1 + currentFilteredResults.length) % currentFilteredResults.length;
      updateSearchResultSelection();
    }
    return;
  }

  // Enter to choose
  if (e.key === 'Enter') {
    e.preventDefault();
    if (selectedResultIndex >= 0 && selectedResultIndex < currentFilteredResults.length) {
      executeSearchResult(selectedResultIndex);
    }
    return;
  }
});

function updateSearchResultSelection() {
  document.querySelectorAll('[id^="search-res-item-"]').forEach((el, idx) => {
    if (idx === selectedResultIndex) {
      el.className = el.className.replace('hover:bg-slate-50 border-transparent', 'bg-indigo-50/80 border-indigo-200');
      el.scrollIntoView({ block: 'nearest' });
    } else {
      el.className = el.className.replace('bg-indigo-50/80 border-indigo-200', 'hover:bg-slate-50 border-transparent');
    }
  });
}

// ==================== GITHUB TRENDING ====================

let trendingReposCache = {};

async function loadTrendingRepos(force = false) {
  const select = document.getElementById('trending-since-select');
  const since = select ? select.value : 'daily';
  const grid = document.getElementById('trending-grid');
  const icon = document.getElementById('trending-refresh-icon');

  if (!grid) return;

  if (icon) icon.classList.add('animate-spin');

  if (trendingReposCache[since] && !force) {
    renderTrendingRepos(trendingReposCache[since]);
    if (icon) icon.classList.remove('animate-spin');
    return;
  }

  grid.innerHTML = `
    <div class="col-span-full py-8 text-center text-slate-400">
      <div class="inline-block animate-spin rounded-full h-6 w-6 border-3 border-amber-500 border-t-transparent mb-2"></div>
      <p class="text-xs">A carregar os repositórios em alta do GitHub...</p>
    </div>
  `;

  try {
    const res = await fetch(`/api/trending?since=${encodeURIComponent(since)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Erro ao obter trending do GitHub.');

    trendingReposCache[since] = data;
    renderTrendingRepos(data);
  } catch (err) {
    grid.innerHTML = `
      <div class="col-span-full py-6 text-center text-rose-500 text-xs">
        <i class="fa-solid fa-triangle-exclamation mb-1 text-sm"></i>
        <p>Não foi possível carregar a lista de repositórios em alta neste momento.</p>
        <button onclick="loadTrendingRepos(true)" class="mt-2 text-indigo-600 hover:underline font-medium">Tentar de novo</button>
      </div>
    `;
  } finally {
    if (icon) icon.classList.remove('animate-spin');
  }
}

function renderTrendingRepos(repos) {
  const grid = document.getElementById('trending-grid');
  if (!grid) return;

  if (!repos || repos.length === 0) {
    grid.innerHTML = `
      <div class="col-span-full py-6 text-center text-slate-400 text-xs">
        Nenhum repositório em alta encontrado de momento.
      </div>
    `;
    return;
  }

  grid.innerHTML = repos.map((r, idx) => {
    return `
      <div class="p-4 bg-slate-50/70 hover:bg-white rounded-xl border border-slate-200/80 hover:border-indigo-300 hover:shadow-sm transition-all flex flex-col justify-between group">
        <div>
          <div class="flex items-start justify-between gap-2 mb-1.5">
            <div class="flex items-center gap-1.5 min-w-0">
              <span class="text-xs text-slate-400 font-mono font-medium truncate">${escapeHtml(r.owner)} /</span>
              <span class="text-xs sm:text-sm font-bold text-slate-900 group-hover:text-indigo-600 transition-colors truncate">${escapeHtml(r.name)}</span>
            </div>
            ${r.stars_today ? `
              <span class="text-[10px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full shrink-0 flex items-center gap-1">
                <i class="fa-solid fa-star text-[9px] text-amber-500"></i> ${escapeHtml(r.stars_today)}
              </span>
            ` : ''}
          </div>

          <p class="text-xs text-slate-600 line-clamp-2 leading-relaxed mb-3">
            ${escapeHtml(r.description || 'Sem descrição fornecida.')}
          </p>
        </div>

        <div class="flex items-center justify-between pt-2.5 border-t border-slate-100 text-xs text-slate-500">
          <div class="flex items-center gap-3">
            ${r.language ? `
              <span class="flex items-center gap-1 font-medium text-slate-700">
                <i class="fa-solid fa-circle text-[7px] text-indigo-500"></i> ${escapeHtml(r.language)}
              </span>
            ` : ''}
            ${r.stars ? `
              <span class="flex items-center gap-1">
                <i class="fa-regular fa-star text-[11px] text-slate-400"></i> ${escapeHtml(r.stars)}
              </span>
            ` : ''}
          </div>

          <div class="flex items-center gap-1.5">
            <a 
              href="${escapeHtml(r.url)}" 
              target="_blank" 
              rel="noopener noreferrer"
              title="Abrir no GitHub"
              class="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer text-xs"
            >
              <i class="fa-brands fa-github text-sm"></i>
            </a>
            <button 
              id="trending-install-btn-${idx}"
              onclick="installTrendingRepo('${escapeJsStr(r.url)}', '${escapeJsStr(r.name)}', '${escapeJsStr(r.owner)}', '${escapeJsStr(r.description || '')}', ${idx})"
              title="Instalar (fazer download) no computador"
              class="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-white rounded-lg font-medium text-xs flex items-center gap-1.5 transition-all cursor-pointer shadow-2xs"
            >
              <i class="fa-solid fa-download text-[10px]"></i>
              <span>Instalar</span>
            </button>
            <button 
              onclick="analyzeTrendingRepo('${escapeJsStr(r.url)}')"
              title="Analisar com Inteligência Artificial"
              class="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium text-xs flex items-center gap-1 transition-all cursor-pointer shadow-2xs"
            >
              <i class="fa-solid fa-wand-magic-sparkles text-[10px]"></i>
              <span>Analisar</span>
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

async function installTrendingRepo(url, name, owner, description, btnIdx) {
  const btn = document.getElementById(`trending-install-btn-${btnIdx}`);
  const originalHtml = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin text-[10px]"></i> <span>A instalar...</span>`;
  }

  showToast(`A instalar ${name} no teu computador...`, 'info');

  try {
    const res = await fetch('/api/repos/clone-url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: url,
        name: name,
        owner: owner,
        description: description
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Falha ao instalar o repositório.');

    showToast(`"${name}" instalado com sucesso no teu computador!`, 'success');
    if (btn) {
      btn.className = 'px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-300 rounded-lg font-medium text-xs flex items-center gap-1 cursor-default';
      btn.innerHTML = `<i class="fa-solid fa-check text-[10px]"></i> <span>Instalado</span>`;
      btn.disabled = true;
    }
    if (typeof loadLocalRepos === 'function') loadLocalRepos();
    if (typeof loadHistory === 'function') loadHistory();
  } catch (err) {
    showToast(err.message, 'error');
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
}

function analyzeTrendingRepo(url) {
  switchGitHubSubView('analyze');
  const input = document.getElementById('repo-url-input');
  if (input) {
    input.value = url;
  }
  // Scroll to top of analyze form and trigger
  window.scrollTo({ top: 0, behavior: 'smooth' });
  const form = document.getElementById('analyze-form');
  if (form) {
    handleAnalyze(new Event('submit'));
  }
}

// ==================== HUGGING FACE TRENDING ====================

let hfTrendingCache = {};

async function loadHuggingFaceTrending(force = false) {
  const select = document.getElementById('hf-type-select');
  const cat = select ? select.value : 'models';
  const grid = document.getElementById('hf-grid');
  const icon = document.getElementById('hf-refresh-icon');

  if (!grid) return;

  if (icon) icon.classList.add('animate-spin');

  if (hfTrendingCache[cat] && !force) {
    renderHuggingFaceTrending(hfTrendingCache[cat]);
    if (icon) icon.classList.remove('animate-spin');
    return;
  }

  grid.innerHTML = `
    <div class="col-span-full py-8 text-center text-slate-400">
      <div class="inline-block animate-spin rounded-full h-6 w-6 border-3 border-yellow-500 border-t-transparent mb-2"></div>
      <p class="text-xs">A carregar tendências do Hugging Face...</p>
    </div>
  `;

  try {
    const res = await fetch(`/api/trending/huggingface?category=${encodeURIComponent(cat)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Erro ao obter dados do Hugging Face.');

    hfTrendingCache[cat] = data;
    renderHuggingFaceTrending(data);
  } catch (err) {
    grid.innerHTML = `
      <div class="col-span-full py-6 text-center text-rose-500 text-xs">
        <i class="fa-solid fa-triangle-exclamation mb-1 text-sm"></i>
        <p>Não foi possível carregar as tendências do Hugging Face neste momento.</p>
        <button onclick="loadHuggingFaceTrending(true)" class="mt-2 text-indigo-600 hover:underline font-medium">Tentar de novo</button>
      </div>
    `;
  } finally {
    if (icon) icon.classList.remove('animate-spin');
  }
}

function renderHuggingFaceTrending(items) {
  const grid = document.getElementById('hf-grid');
  if (!grid) return;

  if (!items || items.length === 0) {
    grid.innerHTML = `
      <div class="col-span-full py-6 text-center text-slate-400 text-xs">
        Nenhum item em alta encontrado no Hugging Face de momento.
      </div>
    `;
    return;
  }

  grid.innerHTML = items.map((it) => {
    return `
      <div class="p-4 bg-slate-50/70 hover:bg-white rounded-xl border border-slate-200/80 hover:border-yellow-400 hover:shadow-sm transition-all flex flex-col justify-between group">
        <div>
          <div class="flex items-start justify-between gap-2 mb-1.5">
            <div class="flex items-center gap-1.5 min-w-0">
              <span class="text-xs text-slate-400 font-mono font-medium truncate">${escapeHtml(it.author)} /</span>
              <span class="text-xs sm:text-sm font-bold text-slate-900 group-hover:text-yellow-700 transition-colors truncate">${escapeHtml(it.name)}</span>
            </div>
            <span class="text-[10px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full shrink-0 flex items-center gap-1">
              <i class="fa-solid fa-heart text-[9px] text-amber-500"></i> ${escapeHtml(it.likes)}
            </span>
          </div>

          <div class="flex items-center gap-2 mt-1 mb-2.5">
            <span class="px-2 py-0.5 rounded-md bg-yellow-100/70 text-yellow-800 text-[10px] font-semibold">
              ${escapeHtml(it.task)}
            </span>
            <span class="text-[11px] text-slate-500">
              <i class="fa-solid fa-download text-[9px] text-slate-400 mr-0.5"></i> ${escapeHtml(it.downloads)} downloads
            </span>
          </div>

          ${it.description ? `
            <p class="text-xs text-slate-600 line-clamp-3 mb-3 leading-relaxed">
              ${escapeHtml(it.description)}
            </p>
          ` : ''}
        </div>

        <div class="flex items-center justify-between pt-2.5 border-t border-slate-100 text-xs">
          <span class="text-slate-400 text-[11px]">Hugging Face ${it.type === 'model' ? 'Model' : 'Space'}</span>
          <a 
            href="${escapeHtml(it.url)}" 
            target="_blank" 
            rel="noopener noreferrer"
            title="Abrir no Hugging Face"
            class="px-3 py-1 bg-yellow-50 hover:bg-yellow-100 text-yellow-800 border border-yellow-200 rounded-lg font-medium text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <span>Ver no HF</span>
            <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
          </a>
        </div>
      </div>
    `;
  }).join('');
}

// Initial bootstrap
document.addEventListener('DOMContentLoaded', () => {
  loadHomeDashboard();
  updateGitHubHubCounts();
  loadCategories();
  loadTrendingRepos();
  loadHuggingFaceTrending();

  // Bind global search input listener
  const searchInput = document.getElementById('global-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      executeGlobalSearch();
    });
  }

  // Pre-load data in background
  setTimeout(() => {
    prefetchSearchData();
  }, 1200);

  // Register Service Worker for PWA support
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/service-worker.js').catch((err) => {
        console.warn('Falha ao registar Service Worker:', err);
      });
    });
  }
});

// ==================== PROMPTS TAB LOGIC ====================

let currentPromptsSubTab = 'library';
let communityDebounceTimer = null;
let cachedCommunityPrompts = [];

function switchPromptsSubTab(subTab) {
  currentPromptsSubTab = subTab;
  const libBtn = document.getElementById('prompts-subtab-library-btn');
  const comBtn = document.getElementById('prompts-subtab-community-btn');
  const libView = document.getElementById('prompts-subtab-library');
  const comView = document.getElementById('prompts-subtab-community');

  if (subTab === 'library') {
    libBtn.className = 'px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all bg-indigo-600 text-white shadow-xs cursor-pointer flex items-center gap-1.5';
    comBtn.className = 'px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all bg-slate-100 hover:bg-slate-200 text-slate-700 cursor-pointer flex items-center gap-1.5';
    libView.classList.remove('hidden');
    comView.classList.add('hidden');
    loadMyPrompts();
  } else {
    comBtn.className = 'px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all bg-indigo-600 text-white shadow-xs cursor-pointer flex items-center gap-1.5';
    libBtn.className = 'px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all bg-slate-100 hover:bg-slate-200 text-slate-700 cursor-pointer flex items-center gap-1.5';
    comView.classList.remove('hidden');
    libView.classList.add('hidden');
    loadCommunityCategories();
    if (!cachedCommunityPrompts || cachedCommunityPrompts.length === 0) {
      loadCommunityPrompts();
    }
  }
}

function refreshCurrentPromptsSubTab() {
  const icon = document.getElementById('prompts-refresh-icon');
  if (icon) icon.classList.add('animate-spin');

  if (currentPromptsSubTab === 'library') {
    loadMyPrompts().finally(() => {
      if (icon) icon.classList.remove('animate-spin');
    });
  } else {
    loadCommunityPrompts(true).finally(() => {
      if (icon) icon.classList.remove('animate-spin');
    });
  }
}

// 1. Minha Biblioteca de Prompts
function getModelBadgeClass(modelName) {
  const m = (modelName || '').toLowerCase();
  if (m.includes('claude')) return 'bg-amber-50 text-amber-700 border-amber-200';
  if (m.includes('gemini')) return 'bg-blue-50 text-blue-700 border-blue-200';
  if (m.includes('deepseek')) return 'bg-purple-50 text-purple-700 border-purple-200';
  if (m.includes('llama')) return 'bg-sky-50 text-sky-700 border-sky-200';
  if (m.includes('mistral')) return 'bg-orange-50 text-orange-700 border-orange-200';
  if (m.includes('grok')) return 'bg-cyan-50 text-cyan-700 border-cyan-200';
  return 'bg-emerald-50 text-emerald-700 border-emerald-200';
}

async function loadMyPrompts() {
  const grid = document.getElementById('my-prompts-grid');
  const countText = document.getElementById('my-prompts-count-text');
  const countBadge = document.getElementById('prompts-my-count-badge');
  const searchInput = document.getElementById('my-prompts-search');
  const sortSelect = document.getElementById('my-prompts-sort');

  const search = searchInput ? searchInput.value.trim() : '';
  const sortVal = sortSelect ? sortSelect.value : 'date-desc';
  const [sortBy, sortOrder] = sortVal.split('-');

  let url = `/api/prompts?sort_by=${encodeURIComponent(sortBy || 'date')}&sort_order=${encodeURIComponent(sortOrder || 'desc')}`;
  if (search) url += `&search=${encodeURIComponent(search)}`;

  try {
    const res = await fetch(url);
    const prompts = await res.json();

    if (countBadge) countBadge.textContent = prompts.length;
    if (countText) countText.textContent = `${prompts.length} ${prompts.length === 1 ? 'prompt guardado' : 'prompts guardados'}`;

    if (!prompts || prompts.length === 0) {
      grid.innerHTML = `
        <div class="col-span-full py-12 text-center text-slate-400 bg-white rounded-2xl border border-slate-200">
          <i class="fa-regular fa-comment-dots text-3xl mb-2 text-indigo-400"></i>
          <p class="text-sm font-medium text-slate-700">Ainda não tens prompts guardados.</p>
          <p class="text-xs text-slate-400 mt-1">Clica em "Criar Novo Prompt" ou explora a aba "prompts.chat" para guardar ideias populares.</p>
        </div>
      `;
      return;
    }

    grid.innerHTML = prompts.map(p => {
      const formattedDate = formatDate(p.created_at);
      const modelBadgeClass = getModelBadgeClass(p.target_model);
      const targetModel = p.target_model || 'ChatGPT (OpenAI)';
      return `
        <div class="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex flex-col justify-between hover:border-slate-300 transition-all">
          <div>
            <div class="flex items-start justify-between gap-2 mb-2">
              <h4 class="font-bold text-slate-900 text-sm sm:text-base flex items-center gap-1.5 flex-wrap">
                <i class="fa-regular fa-comment-dots text-indigo-600 text-xs"></i>
                <span>${escapeHtml(p.act)}</span>
                <button 
                  type="button" 
                  onclick="showPromptInfo('${escapeJsStr(p.act)}', '${escapeJsStr(p.prompt)}', '${escapeJsStr(p.category || 'Geral')}', '${escapeJsStr(targetModel)}')" 
                  title="Ver para que serve este prompt" 
                  class="w-5 h-5 rounded-full bg-slate-100 hover:bg-indigo-100 text-slate-500 hover:text-indigo-600 flex items-center justify-center text-[10px] transition-colors cursor-pointer ml-0.5"
                >
                  <i class="fa-solid fa-question"></i>
                </button>
              </h4>
              <div class="flex items-center gap-1 shrink-0">
                <button 
                  onclick="openEditPromptModal(${p.id})" 
                  title="Editar prompt" 
                  class="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-slate-50 rounded-lg text-xs transition-colors cursor-pointer"
                >
                  <i class="fa-solid fa-pen"></i>
                </button>
                <button 
                  onclick="deletePromptConfirm(${p.id}, '${escapeJsStr(p.act)}')" 
                  title="Eliminar prompt" 
                  class="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg text-xs transition-colors cursor-pointer"
                >
                  <i class="fa-solid fa-trash-can"></i>
                </button>
              </div>
            </div>

            <div class="flex items-center gap-2 mb-3 flex-wrap">
              <span class="badge-category text-[10px]">
                ${escapeHtml(p.category || 'Geral')}
              </span>
              <span class="text-[10px] px-2 py-0.5 rounded-md font-semibold border ${modelBadgeClass}">
                <i class="fa-solid fa-microchip text-[9px] mr-1"></i>${escapeHtml(targetModel)}
              </span>
              ${p.source === 'prompts.chat' ? `
                <span class="text-[10px] px-2 py-0.5 rounded-md font-medium bg-amber-50 text-amber-700 border border-amber-200">
                  prompts.chat
                </span>
              ` : `
                <span class="text-[10px] px-2 py-0.5 rounded-md font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Personalizado
                </span>
              `}
              ${formattedDate ? `
                <span class="text-[11px] text-slate-400 font-mono ml-auto">
                  ${escapeHtml(formattedDate)}
                </span>
              ` : ''}
            </div>

            <div class="relative bg-slate-50 rounded-xl p-3 border border-slate-200 mb-4 font-mono text-xs text-slate-700 leading-relaxed max-h-36 overflow-y-auto whitespace-pre-wrap select-all">
              ${escapeHtml(p.prompt)}
            </div>
          </div>

          <div class="flex items-center justify-between pt-3 border-t border-slate-100 text-xs">
            <span class="text-slate-400 text-[11px] font-mono">${(p.prompt || '').length} caracteres</span>
            <div class="flex items-center gap-2">
              <button 
                type="button"
                onclick="openConvertPromptModal('${escapeJsStr(p.act)}', '${escapeJsStr(p.prompt)}', '${escapeJsStr(targetModel)}', '${escapeJsStr(p.category || 'Geral')}')" 
                class="px-2.5 py-1.5 bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200 rounded-lg font-medium text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
                title="Converter ou otimizar para outro modelo de IA"
              >
                <i class="fa-solid fa-arrows-rotate text-[11px]"></i>
                <span>Converter</span>
              </button>
              <button 
                type="button"
                onclick="copyToClipboard('${escapeJsStr(p.prompt)}', 'Prompt copiado com sucesso!')" 
                class="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium text-xs flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
              >
                <i class="fa-regular fa-copy"></i>
                <span>Copiar</span>
              </button>
            </div>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    grid.innerHTML = `<div class="col-span-full text-center text-rose-500 text-sm py-8">Erro ao carregar a biblioteca de prompts.</div>`;
  }
}

let selectedCommunityCategory = 'all';

async function loadCommunityCategories() {
  const container = document.getElementById('community-categories-container');
  if (!container) return;

  try {
    const res = await fetch('/api/prompts/community/categories');
    const categories = await res.json();

    const allBtnHtml = `
      <button 
        type="button"
        onclick="selectCommunityCategory('all')" 
        id="comm-cat-all" 
        class="comm-cat-btn px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${selectedCommunityCategory === 'all' ? 'bg-indigo-600 text-white shadow-2xs' : 'bg-slate-100 hover:bg-slate-200 text-slate-700'} cursor-pointer flex items-center gap-1.5"
      >
        <i class="fa-solid fa-border-all text-[10px]"></i>
        <span>Todas as Categorias</span>
      </button>
    `;

    const chipsHtml = categories.map(cat => {
      const isSelected = selectedCommunityCategory.toLowerCase() === cat.name.toLowerCase();
      let icon = 'fa-tag';
      const n = cat.name.toLowerCase();
      if (n.includes('código') || n.includes('programa')) icon = 'fa-code';
      else if (n.includes('imagem')) icon = 'fa-image';
      else if (n.includes('escrita') || n.includes('cria')) icon = 'fa-pen-nib';
      else if (n.includes('carreira') || n.includes('negócio')) icon = 'fa-briefcase';
      else if (n.includes('educa') || n.includes('ciência')) icon = 'fa-graduation-cap';
      else if (n.includes('idioma') || n.includes('tradu')) icon = 'fa-language';
      else if (n.includes('estilo') || n.includes('saúde')) icon = 'fa-heart-pulse';
      else if (n.includes('jogo') || n.includes('entretenimento')) icon = 'fa-gamepad';

      return `
        <button 
          type="button"
          onclick="selectCommunityCategory('${escapeJsStr(cat.name)}')" 
          class="comm-cat-btn px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${isSelected ? 'bg-indigo-600 text-white shadow-2xs' : 'bg-slate-100 hover:bg-slate-200 text-slate-700'} cursor-pointer flex items-center gap-1.5"
        >
          <i class="fa-solid ${icon} text-[10px] ${isSelected ? 'text-white' : 'text-indigo-500'}"></i>
          <span>${escapeHtml(cat.name)}</span>
          <span class="text-[10px] px-1.5 py-0.2 rounded-full ${isSelected ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-600'} font-normal">
            ${cat.count}
          </span>
        </button>
      `;
    }).join('');

    container.innerHTML = allBtnHtml + chipsHtml;
  } catch (err) {
    console.error('Erro ao carregar categorias:', err);
  }
}

function selectCommunityCategory(catName) {
  selectedCommunityCategory = catName;
  loadCommunityCategories();
  loadCommunityPrompts();
}

// 2. Prompts da Comunidade (prompts.chat)
async function loadCommunityPrompts(forceRefresh = false) {
  const grid = document.getElementById('community-prompts-grid');
  const countText = document.getElementById('community-prompts-count-text');
  const searchInput = document.getElementById('community-prompts-search');
  const search = searchInput ? searchInput.value.trim() : '';

  if (grid.children.length === 0 || forceRefresh) {
    grid.innerHTML = `
      <div class="col-span-full py-12 text-center text-slate-400">
        <div class="inline-block animate-spin rounded-full h-6 w-6 border-2 border-indigo-600 border-t-transparent mb-2"></div>
        <p class="text-xs">A carregar prompts da comunidade do prompts.chat...</p>
      </div>
    `;
  }

  let url = `/api/prompts/community?refresh=${forceRefresh ? 'true' : 'false'}`;
  if (selectedCommunityCategory && selectedCommunityCategory !== 'all') {
    url += `&category=${encodeURIComponent(selectedCommunityCategory)}`;
  }
  if (search) url += `&search=${encodeURIComponent(search)}`;

  try {
    const res = await fetch(url);
    const prompts = await res.json();
    cachedCommunityPrompts = prompts;

    if (countText) countText.textContent = `${prompts.length} prompts encontrados no prompts.chat`;

    if (!prompts || prompts.length === 0) {
      grid.innerHTML = `
        <div class="col-span-full py-12 text-center text-slate-400 bg-white rounded-2xl border border-slate-200">
          <i class="fa-solid fa-globe text-3xl mb-2 text-indigo-400"></i>
          <p class="text-sm font-medium text-slate-700">Nenhum prompt encontrado nesta categoria ou termo.</p>
        </div>
      `;
      return;
    }

    // Display first 80 for high performance, with instant filter
    const displayList = prompts.slice(0, 80);

    grid.innerHTML = displayList.map(p => {
      const targetModel = p.target_model || 'ChatGPT (OpenAI)';
      const modelBadgeClass = getModelBadgeClass(targetModel);
      return `
      <div class="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex flex-col justify-between hover:border-slate-300 transition-all">
        <div>
          <div class="flex items-start justify-between gap-2 mb-2">
            <h4 class="font-bold text-slate-900 text-sm sm:text-base flex items-center gap-1.5 flex-wrap">
              <i class="fa-solid fa-robot text-amber-500 text-xs"></i>
              <span>${escapeHtml(p.act)}</span>
              <button 
                type="button" 
                onclick="showPromptInfo('${escapeJsStr(p.act)}', '${escapeJsStr(p.prompt)}', '${escapeJsStr(p.category || 'Geral')}', '${escapeJsStr(targetModel)}')" 
                title="Saber o que faz este prompt" 
                class="w-5 h-5 rounded-full bg-slate-100 hover:bg-indigo-100 text-slate-500 hover:text-indigo-600 flex items-center justify-center text-[10px] transition-colors cursor-pointer ml-0.5"
              >
                <i class="fa-solid fa-question"></i>
              </button>
            </h4>
            <div class="flex items-center gap-1.5 shrink-0">
              <span class="text-[10px] px-2 py-0.5 rounded-md font-medium bg-indigo-50 text-indigo-700 border border-indigo-200">
                ${escapeHtml(p.category || 'Geral')}
              </span>
              <span class="text-[10px] px-2 py-0.5 rounded-md font-semibold border ${modelBadgeClass}">
                ${escapeHtml(targetModel)}
              </span>
            </div>
          </div>

          <div class="relative bg-slate-50 rounded-xl p-3 border border-slate-200 mb-4 font-mono text-xs text-slate-700 leading-relaxed max-h-36 overflow-y-auto whitespace-pre-wrap select-all">
            ${escapeHtml(p.prompt)}
          </div>
        </div>

        <div class="flex items-center justify-between pt-3 border-t border-slate-100 text-xs">
          <span class="text-slate-400 text-[11px] font-mono">${(p.prompt || '').length} caracteres</span>
          <div class="flex items-center gap-2">
            <button 
              type="button"
              onclick="openConvertPromptModal('${escapeJsStr(p.act)}', '${escapeJsStr(p.prompt)}', '${escapeJsStr(targetModel)}', '${escapeJsStr(p.category || 'Geral')}')" 
              title="Converter para Claude, Gemini, DeepSeek, etc."
              class="px-2.5 py-1.5 bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200 rounded-lg font-medium text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <i class="fa-solid fa-arrows-rotate text-[11px]"></i>
              <span>Converter</span>
            </button>
            <button 
              type="button"
              onclick="copyToClipboard('${escapeJsStr(p.prompt)}', 'Prompt copiado com sucesso!')" 
              class="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <i class="fa-regular fa-copy"></i>
              <span>Copiar</span>
            </button>
            <button 
              type="button"
              onclick="saveCommunityPromptToLibrary('${escapeJsStr(p.act)}', '${escapeJsStr(p.prompt)}', '${escapeJsStr(p.category || 'Geral')}', '${escapeJsStr(targetModel)}')" 
              title="Guardar na Minha Biblioteca para poderes editar mais tarde"
              class="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white rounded-lg font-medium text-xs flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
            >
              <i class="fa-solid fa-bookmark text-[11px]"></i>
              <span>Guardar</span>
            </button>
          </div>
        </div>
      </div>
    `;
    }).join('');
  } catch (err) {
    grid.innerHTML = `<div class="col-span-full text-center text-rose-500 text-sm py-8">Erro ao carregar prompts da comunidade.</div>`;
  }
}

function debounceCommunitySearch() {
  clearTimeout(communityDebounceTimer);
  communityDebounceTimer = setTimeout(() => {
    loadCommunityPrompts();
  }, 350);
}

// 3. Ações: Guardar da Comunidade, Criar, Editar, Eliminar
async function saveCommunityPromptToLibrary(act, promptText, category, targetModel = 'ChatGPT (OpenAI)') {
  try {
    const res = await fetch('/api/prompts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        act,
        prompt: promptText,
        category: category || 'Geral',
        target_model: targetModel,
        source: 'prompts.chat'
      })
    });
    const data = await res.json();
    if (res.ok) {
      showToast(`Prompt "${act}" guardado na tua biblioteca!`);
      loadMyPrompts();
    } else {
      throw new Error(data.detail || 'Erro ao guardar prompt.');
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function openCreatePromptModal() {
  document.getElementById('prompt-modal-id').value = '';
  document.getElementById('prompt-modal-act').value = '';
  document.getElementById('prompt-modal-category').value = '';
  const modelSelect = document.getElementById('prompt-modal-target-model');
  if (modelSelect) modelSelect.value = 'ChatGPT (OpenAI)';
  document.getElementById('prompt-modal-text').value = '';
  document.getElementById('prompt-modal-title').textContent = 'Criar Novo Prompt';
  const modal = document.getElementById('prompt-modal');
  if (modal) modal.classList.remove('hidden');
}

async function openEditPromptModal(id) {
  try {
    const res = await fetch(`/api/prompts/${id}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Erro ao obter detalhes do prompt.');

    document.getElementById('prompt-modal-id').value = data.id;
    document.getElementById('prompt-modal-act').value = data.act;
    document.getElementById('prompt-modal-category').value = data.category || '';
    const modelSelect = document.getElementById('prompt-modal-target-model');
    if (modelSelect) modelSelect.value = data.target_model || 'ChatGPT (OpenAI)';
    document.getElementById('prompt-modal-text').value = data.prompt;
    document.getElementById('prompt-modal-title').textContent = 'Editar Prompt';

    const modal = document.getElementById('prompt-modal');
    if (modal) modal.classList.remove('hidden');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function closePromptModal() {
  const modal = document.getElementById('prompt-modal');
  if (modal) modal.classList.add('hidden');
}

async function handleSavePromptModal() {
  const id = document.getElementById('prompt-modal-id').value;
  const act = document.getElementById('prompt-modal-act').value.trim();
  const category = document.getElementById('prompt-modal-category').value.trim() || 'Geral';
  const modelSelect = document.getElementById('prompt-modal-target-model');
  const target_model = modelSelect ? modelSelect.value : 'ChatGPT (OpenAI)';
  const prompt = document.getElementById('prompt-modal-text').value.trim();

  if (!act || !prompt) {
    showToast('Título e texto do prompt são obrigatórios.', 'error');
    return;
  }

  const saveBtn = document.getElementById('prompt-modal-save-btn');
  saveBtn.disabled = true;

  try {
    let res;
    if (id) {
      // Edit
      res = await fetch(`/api/prompts/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ act, prompt, category, target_model })
      });
    } else {
      // Create
      res = await fetch('/api/prompts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ act, prompt, category, target_model, source: 'personalizado' })
      });
    }

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Erro ao guardar prompt.');

    showToast(id ? 'Prompt atualizado com sucesso!' : 'Prompt criado com sucesso!');
    closePromptModal();
    loadMyPrompts();
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    saveBtn.disabled = false;
  }
}

async function deletePromptConfirm(id, actName) {
  if (!confirm(`Tens a certeza que queres eliminar o prompt "${actName}" da tua biblioteca?`)) {
    return;
  }

  try {
    const res = await fetch(`/api/prompts/${id}`, { method: 'DELETE' });
    if (res.ok) {
      showToast('Prompt eliminado com sucesso.');
      loadMyPrompts();
    } else {
      showToast('Erro ao eliminar prompt.', 'error');
    }
  } catch (err) {
    showToast('Erro de comunicação com o servidor.', 'error');
  }
}

// 4. Modal de Informação / Explicação do Prompt (?)
let currentInfoAct = '';
let currentInfoPromptText = '';
let currentInfoCategory = 'Geral';
let currentInfoModel = 'ChatGPT (OpenAI)';

function generatePromptDescription(act, promptText) {
  const a = (act || '').toLowerCase();
  
  if (a.includes('ethereum developer')) return 'Instrui a Inteligência Artificial a agir como um programador especializado em Ethereum e contratos inteligentes (smart contracts) em Solidity, fornecendo código seguro e arquitetura blockchain.';
  if (a.includes('linux terminal')) return 'Transforma a IA num terminal interativo de Linux. Podes escrever comandos normais (como ls, cd, grep) e ela responde unicamente com a saída de ecrã simulada do terminal.';
  if (a.includes('javascript console')) return 'Transforma a IA numa consola de JavaScript que avalia código, exibe saídas de console.log() e testa pequenos scripts diretamente.';
  if (a.includes('python interpreter')) return 'Age como o interpretador Python oficial, executando e mostrando a saída do código sem conversas secundárias.';
  if (a.includes('excel sheet')) return 'Configura a IA como uma folha de cálculo em texto, permitindo gerar tabelas com linhas, colunas e fórmulas numéricas.';
  if (a.includes('translator') || a.includes('tradutor')) return 'Configura a IA como um especialista em tradução, melhoria gramatical e correção de texto entre línguas.';
  if (a.includes('interviewer') || a.includes('recruiter')) return 'Simula uma entrevista de emprego real, fazendo-te perguntas uma a uma sobre a função pretendida para treinares as tuas respostas.';
  if (a.includes('code review') || a.includes('revisor')) return 'Inspeciona código à procura de potenciais erros, vulnerabilidades de segurança e oportunidades de melhoria de desempenho.';
  if (a.includes('jardin') || a.includes('plant')) return 'Especialista em plantas e jardinagem que dá conselhos práticos de rega, poda, tratamentos e cuidados com o solo.';
  if (a.includes('piscina')) return 'Técnico de piscinas para orientar sobre análise da água, regulação de pH, cloro e manutenção de bombas e filtros.';

  const firstSentence = promptText.split('.')[0].replace(/\n/g, ' ').trim();
  if (firstSentence.length > 20 && firstSentence.length < 220) {
    return `Objetivo: "${firstSentence}". Define o papel e o comportamento da IA para responder como este profissional ou ferramenta.`;
  }

  return `Instrui a Inteligência Artificial a adotar a personalidade e especialização de "${act}", focando as suas respostas exclusivamente nas tarefas e tom desse papel.`;
}

function showPromptInfo(act, promptText, category, targetModel = 'ChatGPT (OpenAI)') {
  currentInfoAct = act;
  currentInfoPromptText = promptText;
  currentInfoCategory = category || 'Geral';
  currentInfoModel = targetModel || 'ChatGPT (OpenAI)';
  
  const titleEl = document.getElementById('prompt-info-title');
  const catEl = document.getElementById('prompt-info-category');
  const modelEl = document.getElementById('prompt-info-model');
  const purposeEl = document.getElementById('prompt-info-purpose');
  const previewEl = document.getElementById('prompt-info-preview');
  const charsEl = document.getElementById('prompt-info-chars');

  if (titleEl) titleEl.textContent = act;
  if (catEl) catEl.textContent = category || 'Geral';
  if (modelEl) modelEl.textContent = targetModel;
  if (purposeEl) purposeEl.textContent = generatePromptDescription(act, promptText);
  if (previewEl) previewEl.textContent = promptText;
  if (charsEl) charsEl.textContent = `${(promptText || '').length} caracteres`;

  const modal = document.getElementById('prompt-info-modal');
  if (modal) modal.classList.remove('hidden');
}

function closePromptInfoModal() {
  const modal = document.getElementById('prompt-info-modal');
  if (modal) modal.classList.add('hidden');
}

function copyPromptInfoModal() {
  if (currentInfoPromptText) {
    copyToClipboard(currentInfoPromptText, 'Prompt copiado com sucesso!');
  }
}

function convertFromInfoModal() {
  closePromptInfoModal();
  openConvertPromptModal(currentInfoAct, currentInfoPromptText, currentInfoModel, currentInfoCategory);
}

// 5. Modal Converter / Otimizar Prompt para Outros Modelos
const AVAILABLE_AI_CONVERSION_MODELS = [
  {
    name: 'Claude (Anthropic)',
    short: 'Claude',
    icon: 'fa-brain',
    desc: 'Tags XML, raciocínio detalhado'
  },
  {
    name: 'Google Gemini',
    short: 'Gemini',
    icon: 'fa-sparkles',
    desc: 'Markdown claro e contextual'
  },
  {
    name: 'DeepSeek',
    short: 'DeepSeek',
    icon: 'fa-code',
    desc: 'R1 Chain-of-Thought e lógica'
  },
  {
    name: 'ChatGPT (OpenAI)',
    short: 'ChatGPT',
    icon: 'fa-robot',
    desc: 'Personas, contexto e tom'
  },
  {
    name: 'Meta Llama',
    short: 'Meta Llama',
    icon: 'fa-microchip',
    desc: 'Diretrizes explícitas e concisas'
  },
  {
    name: 'Mistral AI',
    short: 'Mistral',
    icon: 'fa-wind',
    desc: 'Raciocínio compacto e eficiente'
  },
  {
    name: 'xAI Grok',
    short: 'Grok',
    icon: 'fa-bolt',
    desc: 'Direto, analítico e sem rodeios'
  }
];

function openConvertPromptModal(act, promptText, currentModel, category) {
  const normModel = currentModel || 'ChatGPT (OpenAI)';
  const curLower = normModel.toLowerCase();

  document.getElementById('convert-prompt-act').value = act;
  document.getElementById('convert-prompt-original-text').value = promptText;
  document.getElementById('convert-prompt-category').value = category || 'Geral';
  document.getElementById('convert-prompt-current-model').value = normModel;

  document.getElementById('convert-prompt-title').textContent = act;
  document.getElementById('convert-prompt-current-badge').textContent = normModel;
  document.getElementById('convert-prompt-preview-snippet').textContent = promptText;

  // Filtrar o modelo atual: se o prompt já for para o ChatGPT, não mostra ChatGPT e substitui pelo próximo (Mistral AI), etc.
  const targetModels = AVAILABLE_AI_CONVERSION_MODELS.filter(m => {
    const mLower = m.name.toLowerCase();
    if (curLower.includes('chatgpt') && mLower.includes('chatgpt')) return false;
    if (curLower.includes('claude') && mLower.includes('claude')) return false;
    if (curLower.includes('gemini') && mLower.includes('gemini')) return false;
    if (curLower.includes('deepseek') && mLower.includes('deepseek')) return false;
    if (curLower.includes('llama') && mLower.includes('llama')) return false;
    if (curLower.includes('mistral') && mLower.includes('mistral')) return false;
    if (curLower.includes('grok') && mLower.includes('grok')) return false;
    return true;
  }).slice(0, 5);

  const optionsContainer = document.getElementById('convert-model-options');
  if (optionsContainer) {
    optionsContainer.innerHTML = targetModels.map((m, idx) => `
      <button 
        type="button" 
        onclick="selectConvertTargetModel('${escapeJsStr(m.name)}')" 
        class="convert-model-btn p-2.5 rounded-xl border border-slate-200 hover:border-slate-300 bg-white text-left transition-all cursor-pointer flex flex-col gap-1 ${idx === 4 ? 'col-span-2 sm:col-span-1' : ''}" 
        data-model="${escapeHtml(m.name)}"
        data-last="${idx === 4 ? 'true' : 'false'}"
      >
        <span class="text-xs font-bold text-slate-800 flex items-center gap-1.5">
          <i class="fa-solid ${m.icon} text-[11px] text-indigo-500"></i> ${escapeHtml(m.short)}
        </span>
        <span class="text-[10px] text-slate-500 leading-tight">${escapeHtml(m.desc)}</span>
      </button>
    `).join('');
  }

  // Pre-select first target model in the filtered list
  const defaultTarget = targetModels.length > 0 ? targetModels[0].name : 'Claude (Anthropic)';
  selectConvertTargetModel(defaultTarget);

  // Reset states
  document.getElementById('convert-loading-state').classList.add('hidden');
  document.getElementById('convert-result-box').classList.add('hidden');
  document.getElementById('convert-result-textarea').value = '';
  const btn = document.getElementById('btn-execute-conversion');
  if (btn) btn.disabled = false;

  const modal = document.getElementById('prompt-convert-modal');
  if (modal) modal.classList.remove('hidden');
}

function closeConvertPromptModal() {
  const modal = document.getElementById('prompt-convert-modal');
  if (modal) modal.classList.add('hidden');
}

function selectConvertTargetModel(targetModel) {
  document.getElementById('convert-prompt-selected-target').value = targetModel;
  const buttons = document.querySelectorAll('.convert-model-btn');
  buttons.forEach(btn => {
    const m = btn.getAttribute('data-model');
    const isColSpan = btn.getAttribute('data-last') === 'true' ? 'col-span-2 sm:col-span-1' : '';
    if (m === targetModel) {
      btn.className = `convert-model-btn p-2.5 rounded-xl border-2 border-indigo-600 bg-indigo-50/50 text-left transition-all cursor-pointer flex flex-col gap-1 shadow-xs ${isColSpan}`;
    } else {
      btn.className = `convert-model-btn p-2.5 rounded-xl border border-slate-200 hover:border-slate-300 bg-white text-left transition-all cursor-pointer flex flex-col gap-1 ${isColSpan}`;
    }
  });
}

async function handleExecutePromptConversion() {
  const act = document.getElementById('convert-prompt-act').value;
  const prompt_text = document.getElementById('convert-prompt-original-text').value;
  const current_model = document.getElementById('convert-prompt-current-model').value;
  const target_model = document.getElementById('convert-prompt-selected-target').value;

  const loadingEl = document.getElementById('convert-loading-state');
  const resultBoxEl = document.getElementById('convert-result-box');
  const btn = document.getElementById('btn-execute-conversion');

  if (loadingEl) loadingEl.classList.remove('hidden');
  if (resultBoxEl) resultBoxEl.classList.add('hidden');
  if (btn) btn.disabled = true;

  try {
    const res = await fetch('/api/prompts/convert', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        act,
        prompt_text,
        current_model,
        target_model
      })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Erro ao converter prompt.');
    }

    document.getElementById('convert-result-textarea').value = data.converted_prompt;
    const badge = document.getElementById('convert-result-model-badge');
    if (badge) {
      badge.textContent = target_model;
      badge.className = `text-[11px] font-semibold px-2 py-0.5 rounded-full border ${getModelBadgeClass(target_model)}`;
    }

    if (resultBoxEl) resultBoxEl.classList.remove('hidden');
    showToast(`Prompt otimizado para ${target_model}!`);
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    if (loadingEl) loadingEl.classList.add('hidden');
    if (btn) btn.disabled = false;
  }
}

function copyConvertedPromptText() {
  const text = document.getElementById('convert-result-textarea').value;
  if (text) {
    copyToClipboard(text, 'Prompt convertido copiado para a área de transferência!');
  }
}

async function saveConvertedPromptToLibrary() {
  const act = document.getElementById('convert-prompt-act').value;
  const category = document.getElementById('convert-prompt-category').value;
  const target_model = document.getElementById('convert-prompt-selected-target').value;
  const converted_text = document.getElementById('convert-result-textarea').value.trim();

  if (!converted_text) {
    showToast('Não há texto convertido para guardar.', 'error');
    return;
  }

  // Short model label (e.g., Claude, Gemini, DeepSeek, etc.)
  const shortModel = target_model.split(' ')[0];
  const newAct = `${act} (${shortModel})`;

  try {
    const res = await fetch('/api/prompts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        act: newAct,
        prompt: converted_text,
        category: category || 'Geral',
        target_model,
        source: 'convertido'
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Erro ao guardar prompt.');

    showToast(`Guardado na biblioteca como "${newAct}"!`);
    closeConvertPromptModal();
    if (currentPromptsSubTab !== 'library') {
      switchPromptsSubTab('library');
    } else {
      loadMyPrompts();
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ==================== HOME / INÍCIO DASHBOARD ====================

async function loadHomeDashboard() {
  // 1. Carregar estatísticas e métricas do topo
  loadHomeStats();

  // 2. Carregar projetos de software recentes
  loadHomeRecentProjects();

  // 3. Carregar recursos guardados e tendências
  loadHomeRecentResources();

  // 4. Carregar prompts rápidos
  loadHomeRecentPrompts();

  // 5. Carregar skills em destaque
  loadHomeRecentSkills();
}

async function loadHomeStats() {
  try {
    const [resHist, resPrompts, resSkills, resProjects] = await Promise.all([
      fetch('/api/repos').then(r => r.ok ? r.json() : []).catch(() => []),
      fetch('/api/prompts').then(r => r.ok ? r.json() : []).catch(() => []),
      fetch('/api/skills').then(r => r.ok ? r.json() : []).catch(() => []),
      fetch('/api/my-projects').then(r => r.ok ? r.json() : []).catch(() => [])
    ]);

    const statResources = document.getElementById('home-stat-resources');
    const statPrompts = document.getElementById('home-stat-prompts');
    const statSkills = document.getElementById('home-stat-skills');
    const statProjects = document.getElementById('home-stat-projects');

    if (statResources) statResources.textContent = Array.isArray(resHist) ? resHist.length : 0;
    if (statPrompts) statPrompts.textContent = Array.isArray(resPrompts) ? resPrompts.length : 0;
    if (statSkills) statSkills.textContent = Array.isArray(resSkills) ? resSkills.length : 0;
    if (statProjects) statProjects.textContent = Array.isArray(resProjects) ? resProjects.length : 0;
  } catch (err) {
    console.warn('Erro ao atualizar métricas da página inicial:', err);
  }
}

async function loadHomeRecentProjects() {
  const container = document.getElementById('home-recent-projects');
  if (!container) return;

  try {
    const res = await fetch('/api/my-projects?sort_by=date&sort_order=desc');
    if (!res.ok) throw new Error();
    const projects = await res.json();

    if (!Array.isArray(projects) || projects.length === 0) {
      container.innerHTML = `
        <div class="p-4 rounded-xl bg-slate-50 border border-dashed border-slate-200 text-center text-xs text-slate-500">
          Ainda não registaste nenhum projeto local.
          <div class="mt-2">
            <button onclick="switchTab('projects'); switchProjectsSubTab('code'); openRegisterModal();" class="text-xs font-semibold text-purple-600 hover:underline">
              + Registar agora
            </button>
          </div>
        </div>
      `;
      return;
    }

    const recents = projects.slice(0, 3);
    container.innerHTML = recents.map(p => {
      const badgeClass = getStatusBadgeClass(p.status);
      const safePath = escapeJsStr(p.path);
      return `
        <div class="p-3.5 rounded-2xl bg-slate-50/80 hover:bg-slate-100/90 border border-slate-200/70 hover:border-purple-200 transition-all flex items-center justify-between gap-3 group">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <strong class="text-xs font-bold text-slate-900 truncate group-hover:text-purple-900 transition-colors">${escapeHtml(p.name)}</strong>
              <span class="${badgeClass} text-[10px] px-2 py-0.5 rounded-md font-medium">${escapeHtml(p.status)}</span>
            </div>
            <p class="text-[11px] text-slate-500 line-clamp-1 mt-1">${escapeHtml(p.summary || p.path)}</p>
          </div>
          <div class="flex items-center gap-1.5 shrink-0">
            <button onclick="openLocalFolder('${safePath}')" title="Abrir pasta no Explorador" class="p-2 text-slate-500 hover:text-indigo-600 rounded-xl hover:bg-white border border-transparent hover:border-slate-200 text-xs transition-all cursor-pointer shadow-2xs">
              <i class="fa-regular fa-folder-open text-indigo-600"></i>
            </button>
            <button onclick="openInEditor('${safePath}')" title="Abrir no VS Code" class="p-2 text-slate-500 hover:text-blue-600 rounded-xl hover:bg-white border border-transparent hover:border-slate-200 text-xs transition-all cursor-pointer shadow-2xs">
              <i class="fa-solid fa-code text-blue-600"></i>
            </button>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    container.innerHTML = `<div class="text-xs text-slate-400 py-3 text-center">Sem dados de projetos.</div>`;
  }
}

async function loadHomeRecentResources() {
  const container = document.getElementById('home-recent-resources');
  if (!container) return;

  try {
    const res = await fetch('/api/repos');
    if (!res.ok) throw new Error();
    const repos = await res.json();

    if (!Array.isArray(repos) || repos.length === 0) {
      container.innerHTML = `
        <div class="p-4 rounded-xl bg-slate-50 border border-dashed border-slate-200 text-center text-xs text-slate-500">
          Ainda não guardaste repositórios ou modelos.
          <div class="mt-2">
            <button onclick="switchTab('github'); switchGitHubSubView('analyze');" class="text-xs font-semibold text-blue-600 hover:underline">
              Analisar um link do GitHub
            </button>
          </div>
        </div>
      `;
      return;
    }

    const recents = repos.slice(0, 3);
    container.innerHTML = recents.map(r => `
      <div class="p-3.5 rounded-2xl bg-slate-50/80 hover:bg-slate-100/90 border border-slate-200/70 hover:border-blue-200 transition-all flex items-center justify-between gap-3 group">
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 flex-wrap">
            <strong class="text-xs font-bold text-slate-900 truncate group-hover:text-blue-900 transition-colors">${escapeHtml(r.name)}</strong>
            <span class="badge-category text-[10px] px-2 py-0.5 rounded-full font-semibold">${escapeHtml(r.category || 'Geral')}</span>
          </div>
          <p class="text-[11px] text-slate-500 line-clamp-1 mt-1">${escapeHtml(r.description_simple || r.url)}</p>
        </div>
        <div class="flex items-center gap-1.5 shrink-0">
          <button onclick="viewRepoDetails(${r.id})" class="px-2.5 py-1 text-xs text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200/60 rounded-xl font-semibold transition-all cursor-pointer shadow-2xs">
            Ver
          </button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<div class="text-xs text-slate-400 py-3 text-center">Sem recursos guardados.</div>`;
  }
}

async function loadHomeRecentPrompts() {
  const container = document.getElementById('home-recent-prompts');
  if (!container) return;

  try {
    const res = await fetch('/api/prompts');
    if (!res.ok) throw new Error();
    const prompts = await res.json();

    if (!Array.isArray(prompts) || prompts.length === 0) {
      container.innerHTML = `
        <div class="p-4 rounded-xl bg-slate-50 border border-dashed border-slate-200 text-center text-xs text-slate-500">
          Biblioteca de prompts vazia.
          <div class="mt-2">
            <button onclick="switchTab('prompts'); openCreatePromptModal();" class="text-xs font-semibold text-emerald-600 hover:underline">
              + Criar primeiro prompt
            </button>
          </div>
        </div>
      `;
      return;
    }

    const recents = prompts.slice(0, 3);
    container.innerHTML = recents.map(p => {
      const safePrompt = escapeJsStr(p.prompt);
      const safeAct = escapeJsStr(p.act);
      const safeModel = escapeJsStr(p.target_model || 'Universal');
      const safeCategory = escapeJsStr(p.category || 'Geral');
      const badgeClass = getModelBadgeClass(p.target_model || 'Universal');

      return `
        <div class="p-3.5 rounded-2xl bg-slate-50/80 hover:bg-slate-100/90 border border-slate-200/70 hover:border-emerald-200 transition-all flex items-center justify-between gap-3 group">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <strong class="text-xs font-bold text-slate-900 truncate group-hover:text-emerald-900 transition-colors">${escapeHtml(p.act)}</strong>
              <span class="text-[10px] px-2 py-0.5 rounded-full border font-semibold ${badgeClass}">
                ${escapeHtml(p.target_model || 'Universal')}
              </span>
            </div>
            <p class="text-[11px] text-slate-500 line-clamp-1 mt-1">${escapeHtml(p.prompt)}</p>
          </div>
          <div class="flex items-center gap-1.5 shrink-0">
            <button onclick="copyToClipboard('${safePrompt}', 'Prompt copiado!')" title="Copiar prompt" class="p-2 text-slate-500 hover:text-emerald-700 bg-white hover:bg-emerald-50 border border-slate-200 rounded-xl text-xs transition-all cursor-pointer shadow-2xs">
              <i class="fa-regular fa-copy"></i>
            </button>
            <button onclick="openPromptInfoModal('${safeAct}', '${safePrompt}', '${safeModel}', '${safeCategory}')" title="Ver detalhes" class="p-2 text-slate-500 hover:text-indigo-600 bg-white hover:bg-indigo-50 border border-slate-200 rounded-xl text-xs transition-all cursor-pointer shadow-2xs">
              <i class="fa-solid fa-circle-question"></i>
            </button>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    container.innerHTML = `<div class="text-xs text-slate-400 py-3 text-center">Sem prompts disponíveis.</div>`;
  }
}

async function loadHomeRecentSkills() {
  const container = document.getElementById('home-recent-skills');
  if (!container) return;

  try {
    const res = await fetch('/api/skills');
    if (!res.ok) throw new Error();
    const skills = await res.json();

    if (!Array.isArray(skills) || skills.length === 0) {
      container.innerHTML = `
        <div class="p-4 rounded-xl bg-slate-50 border border-dashed border-slate-200 text-center text-xs text-slate-500">
          Nenhum skill encontrado.
          <div class="mt-2">
            <button onclick="switchTab('skills'); openCreateSkillModal();" class="text-xs font-semibold text-amber-700 hover:underline">
              + Criar primeiro skill
            </button>
          </div>
        </div>
      `;
      return;
    }

    // Preferir skills personalizados ou os 3 primeiros
    const customFirst = [...skills].sort((a, b) => (b.is_custom ? 1 : 0) - (a.is_custom ? 1 : 0)).slice(0, 3);

    container.innerHTML = customFirst.map(s => {
      const safePath = escapeJsStr(s.file_path || '');
      const safeName = escapeJsStr(s.name);
      const safeProgram = escapeJsStr(s.program || '');
      const safeSource = escapeJsStr(s.source || '');
      const modelBadgeClass = getModelBadgeClass(s.target_model || 'Claude');

      return `
        <div class="p-3.5 rounded-2xl bg-slate-50/80 hover:bg-slate-100/90 border border-slate-200/70 hover:border-amber-200 transition-all flex items-center justify-between gap-3 group">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <strong class="text-xs font-bold text-slate-900 truncate group-hover:text-amber-900 transition-colors">${escapeHtml(s.name)}</strong>
              <span class="text-[10px] px-2 py-0.5 rounded-full border font-semibold ${modelBadgeClass}">
                ${escapeHtml(s.target_model || 'Claude')}
              </span>
              ${s.is_custom ? '<span class="text-[9px] px-2 py-0.5 rounded-md bg-amber-50 text-amber-800 border border-amber-200/80 font-bold uppercase tracking-wide">Personalizado</span>' : ''}
            </div>
            <p class="text-[11px] text-slate-500 line-clamp-1 mt-1">${escapeHtml(s.description)}</p>
          </div>
          <div class="flex items-center gap-1.5 shrink-0">
            <button onclick="openSkillDetailModal('${safePath}', '${safeName}', '${safeProgram}', '${safeSource}')" class="px-2.5 py-1 text-xs text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200/60 rounded-xl font-semibold transition-all cursor-pointer shadow-2xs">
              Ver
            </button>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    container.innerHTML = `<div class="text-xs text-slate-400 py-3 text-center">Sem skills disponíveis.</div>`;
  }
}

// ==================== FACEBOOK & MEDIA (IPHONE & PC) ====================

let allMediaItemsData = [];
let currentMediaCategoryFilter = '';

function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s < 10 ? '0' : ''}${s}`;
}

function formatBytes(bytes) {
  if (!bytes || bytes <= 0) return '';
  const mb = bytes / (1024 * 1024);
  if (mb >= 1000) {
    return `${(mb / 1024).toFixed(1)} GB`;
  }
  return `${mb.toFixed(1)} MB`;
}

// Suporte para colar link no iPhone com 1 toque
async function pasteMediaUrlFromClipboard() {
  const input = document.getElementById('media-url-input');
  if (!input) return;

  try {
    if (navigator.clipboard && navigator.clipboard.readText) {
      const text = await navigator.clipboard.readText();
      if (text && text.trim().startsWith('http')) {
        input.value = text.trim();
        showToast('Link colado da área de transferência!', 'success');
        input.focus();
        return;
      }
    }
  } catch (err) {
    // Permissão negada ou restrição de clipboard no navegador
  }

  input.focus();
  showToast('Toca e mantém no campo para colar o link.', 'info');
}

async function handleProcessMedia(event) {
  event.preventDefault();
  const input = document.getElementById('media-url-input');
  const url = input ? input.value.trim() : '';
  if (!url) return;

  const downloadToggle = document.getElementById('media-download-toggle');
  const downloadVideo = downloadToggle ? downloadToggle.checked : true;

  const submitBtn = document.getElementById('media-submit-btn');
  const progressBox = document.getElementById('media-progress-box');
  const progressTitle = document.getElementById('media-progress-title');
  const progressDetail = document.getElementById('media-progress-detail');

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
  }
  if (progressBox) progressBox.classList.remove('hidden');
  if (progressTitle) progressTitle.textContent = 'A extrair conteúdo do link...';
  if (progressDetail) progressDetail.textContent = downloadVideo 
    ? 'A descarregar vídeo com yt-dlp e a gerar resumo com IA.' 
    : 'A analisar metadados e a gerar resumo explicativo com IA.';

  try {
    const res = await fetch('/api/media/process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: url,
        download_video: downloadVideo
      })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Não foi possível extrair o vídeo ou publicação.');
    }

    if (input) input.value = '';
    showToast('Conteúdo extraído e guardado com sucesso!', 'success');
    loadMediaItems();
    updateGitHubHubCounts();
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
    }
    if (progressBox) progressBox.classList.add('hidden');
  }
}

async function loadMediaItems() {
  const grid = document.getElementById('media-grid');
  if (!grid) return;

  try {
    const res = await fetch('/api/media');
    if (!res.ok) throw new Error();
    const data = await res.json();
    allMediaItemsData = Array.isArray(data) ? data : [];
    filterMediaItems();
    updateGitHubHubCounts();
  } catch (err) {
    grid.innerHTML = `<div class="col-span-full py-8 text-center text-rose-500 text-xs">Erro ao carregar vídeos guardados.</div>`;
  }
}

function setMediaCategoryFilter(category) {
  currentMediaCategoryFilter = category || '';
  document.querySelectorAll('.media-cat-pill').forEach(btn => {
    if ((category === '' && btn.textContent.trim() === 'Todas') || btn.textContent.trim() === category) {
      btn.className = 'media-cat-pill active px-2.5 py-1 rounded-lg bg-sky-600 text-white font-medium shrink-0';
    } else {
      btn.className = 'media-cat-pill px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 font-medium shrink-0';
    }
  });
  filterMediaItems();
}

function filterMediaItems() {
  const query = (document.getElementById('media-search-input')?.value || '').toLowerCase().trim();
  const grid = document.getElementById('media-grid');
  if (!grid) return;

  let filtered = allMediaItemsData;

  if (currentMediaCategoryFilter) {
    filtered = filtered.filter(item => (item.category || '').toLowerCase() === currentMediaCategoryFilter.toLowerCase());
  }

  if (query) {
    filtered = filtered.filter(item => 
      (item.title || '').toLowerCase().includes(query) ||
      (item.author || '').toLowerCase().includes(query) ||
      (item.summary_ai || '').toLowerCase().includes(query) ||
      (item.description || '').toLowerCase().includes(query)
    );
  }

  renderMediaGrid(filtered);
}

function renderMediaGrid(items) {
  const grid = document.getElementById('media-grid');
  if (!grid) return;

  if (!items || items.length === 0) {
    grid.innerHTML = `
      <div class="col-span-full py-12 text-center text-slate-400">
        <div class="w-12 h-12 mx-auto rounded-full bg-slate-100 text-slate-400 flex items-center justify-center text-xl mb-3">
          <i class="fa-brands fa-facebook"></i>
        </div>
        <p class="text-sm font-semibold text-slate-600">Nenhum vídeo encontrado</p>
        <p class="text-xs text-slate-400 mt-1">Experimenta colar um link do Facebook ou limpar os filtros de pesquisa.</p>
      </div>
    `;
    return;
  }

  grid.innerHTML = items.map(item => {
    const safeTitle = escapeJsStr(item.title || 'Vídeo');
    const hasLocal = !!item.local_file_path;
    const durationText = formatDuration(item.duration_seconds);
    const sizeText = formatBytes(item.file_size_bytes);
    const sourceIcon = item.source === 'Facebook' ? 'fa-brands fa-facebook text-sky-600' : 'fa-solid fa-play text-indigo-600';

    return `
      <div class="bg-white rounded-2xl border border-slate-200/90 hover:border-sky-300 shadow-xs hover:shadow-md transition-all flex flex-col justify-between overflow-hidden group">
        <div>
          <!-- Thumbnail com overlay de play -->
          <div class="relative aspect-video bg-slate-900 overflow-hidden cursor-pointer" onclick="openMediaPlayerModal(${item.id})">
            ${item.thumbnail_url ? `
              <img src="${escapeHtml(item.thumbnail_url)}" alt="${escapeHtml(item.title)}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" onerror="this.src='/fallback-thumb.png'; this.classList.add('opacity-30')">
            ` : `
              <div class="w-full h-full flex items-center justify-center bg-slate-800 text-slate-500">
                <i class="fa-solid fa-video text-3xl"></i>
              </div>
            `}
            
            <!-- Play button overlay -->
            <div class="absolute inset-0 bg-black/25 flex items-center justify-center opacity-90 group-hover:opacity-100 group-hover:bg-black/35 transition-all">
              <div class="w-11 h-11 rounded-full bg-white/90 text-sky-600 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
                <i class="fa-solid fa-play text-sm ml-0.5"></i>
              </div>
            </div>

            <!-- Duração e tamanho -->
            <div class="absolute bottom-2 right-2 flex items-center gap-1.5">
              ${sizeText ? `<span class="px-2 py-0.5 rounded-md bg-black/75 text-white text-[10px] font-mono font-medium backdrop-blur-xs">${sizeText}</span>` : ''}
              ${durationText ? `<span class="px-2 py-0.5 rounded-md bg-black/75 text-white text-[10px] font-mono font-medium backdrop-blur-xs">${durationText}</span>` : ''}
            </div>

            <!-- Tag de offline / local -->
            <div class="absolute top-2 left-2 flex items-center gap-1">
              <span class="px-2 py-0.5 rounded-md bg-black/60 text-white text-[10px] font-semibold backdrop-blur-xs flex items-center gap-1">
                <i class="${sourceIcon} text-xs"></i>
                <span>${escapeHtml(item.source || 'Facebook')}</span>
              </span>
              ${hasLocal ? `
                <span class="px-2 py-0.5 rounded-md bg-emerald-600/90 text-white text-[10px] font-semibold backdrop-blur-xs flex items-center gap-1">
                  <i class="fa-solid fa-circle-down text-[9px]"></i>
                  <span>Offline</span>
                </span>
              ` : ''}
            </div>
          </div>

          <!-- Informações do Card -->
          <div class="p-4 space-y-2.5">
            <div class="flex items-start justify-between gap-2">
              <h4 class="text-xs sm:text-sm font-bold text-slate-900 line-clamp-2 leading-snug group-hover:text-sky-900 transition-colors" title="${escapeHtml(item.title)}">
                ${escapeHtml(item.title)}
              </h4>
            </div>

            <div class="flex items-center gap-2 text-[11px] text-slate-500 flex-wrap">
              ${item.author ? `<span class="font-medium text-slate-700 truncate max-w-[140px]"><i class="fa-regular fa-user mr-1 text-[10px]"></i>${escapeHtml(item.author)}</span>` : ''}
              <span class="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium text-[10px]">${escapeHtml(item.category || 'Geral')}</span>
            </div>

            <!-- Resumo IA curto -->
            ${item.summary_ai ? `
              <div class="p-2.5 rounded-xl bg-sky-50/70 border border-sky-100 text-[11px] text-slate-700 leading-relaxed line-clamp-3">
                <strong class="font-semibold text-sky-900 block mb-0.5 flex items-center gap-1">
                  <i class="fa-solid fa-wand-magic-sparkles text-[9px] text-amber-500"></i> Resumo IA:
                </strong>
                ${escapeHtml(item.summary_ai)}
              </div>
            ` : ''}
          </div>
        </div>

        <!-- Ações do Card -->
        <div class="px-4 py-3 bg-slate-50/80 border-t border-slate-100 flex items-center justify-between gap-2">
          <button 
            onclick="openMediaPlayerModal(${item.id})" 
            class="px-3 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-2xs transition-colors cursor-pointer"
          >
            <i class="fa-solid fa-play text-[10px]"></i>
            <span>Ver Vídeo</span>
          </button>

          <div class="flex items-center gap-1">
            <a 
              href="${escapeHtml(item.url)}" 
              target="_blank" 
              rel="noopener noreferrer" 
              title="Abrir no Facebook" 
              class="p-1.5 text-slate-400 hover:text-sky-600 rounded-lg hover:bg-white transition-colors cursor-pointer"
            >
              <i class="fa-solid fa-arrow-up-right-from-square text-xs"></i>
            </a>
            <button 
              onclick="deleteMediaItemConfirm(${item.id}, '${safeTitle}')" 
              title="Eliminar vídeo" 
              class="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-white transition-colors cursor-pointer"
            >
              <i class="fa-regular fa-trash-can text-xs"></i>
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function openMediaPlayerModal(id) {
  const item = allMediaItemsData.find(m => m.id === id);
  if (!item) return;

  const modal = document.getElementById('media-player-modal');
  const title = document.getElementById('media-player-modal-title');
  const source = document.getElementById('media-player-source');
  const author = document.getElementById('media-player-author');
  const category = document.getElementById('media-player-category');
  const summary = document.getElementById('media-player-summary');
  const origLink = document.getElementById('media-player-original-link');
  const video = document.getElementById('media-player-video');

  if (title) title.textContent = item.title || 'Reproduzir Vídeo';
  if (source) source.textContent = item.source || 'Facebook';
  if (author) author.textContent = item.author ? `Por ${item.author}` : '';
  if (category) category.textContent = item.category || 'Geral';
  if (summary) summary.textContent = item.summary_ai || item.description || 'Sem resumo disponível.';
  if (origLink) {
    origLink.href = item.url || '#';
    origLink.textContent = `Ver no ${item.source || 'Facebook'} original`;
  }

  if (video) {
    // Se tiver ficheiro guardado localmente, usa o streaming endpoint do backend
    if (item.local_file_path) {
      video.src = `/api/media/${item.id}/stream`;
    } else {
      // Se não tiver local, tenta usar o url direto se existir
      video.src = item.url;
    }
    video.load();
    video.play().catch(() => {});
  }

  if (modal) modal.classList.remove('hidden');
}

function closeMediaPlayerModal() {
  const modal = document.getElementById('media-player-modal');
  const video = document.getElementById('media-player-video');
  if (video) {
    video.pause();
    video.removeAttribute('src');
    video.load();
  }
  if (modal) modal.classList.add('hidden');
}

async function deleteMediaItemConfirm(id, title) {
  if (!confirm(`Tens a certeza de que queres eliminar "${title}"?\n\nO vídeo e os dados guardados serão removidos.`)) {
    return;
  }

  try {
    const res = await fetch(`/api/media/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Falha ao eliminar vídeo');
    showToast('Vídeo eliminado com sucesso!');
    allMediaItemsData = allMediaItemsData.filter(m => m.id !== id);
    filterMediaItems();
    updateGitHubHubCounts();
  } catch (err) {
    showToast(err.message, 'error');
  }
}




