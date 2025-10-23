/**
 * API Client - Operations (Controle & DAT)
 *
 * Endpoints para importação e listagem de:
 * - COMPRAS (Controle)
 * - AÇÕES (Controle)
 * - CADASTROS (DAT)
 *
 * IMPORTANTE: Todas as rotas usam trailing slash (/)
 * Usa proxy do Vite em dev (/api → http://localhost:8002/api)
 */

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

/**
 * Extrai token CSRF do cookie.
 *
 * @returns {string|null} CSRF token ou null se não encontrado
 */
function getCSRFToken() {
  const name = 'csrftoken';
  let cookieValue = null;

  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }

  return cookieValue;
}

/**
 * Helper para upload de arquivo (multipart/form-data).
 *
 * @param {string} url - URL do endpoint (com trailing slash)
 * @param {File} file - Arquivo a enviar
 * @param {boolean} dryRun - Se true, apenas preview (não aplica)
 * @returns {Promise<object>} Relatório de import
 */
async function postMultipart(url, file, dryRun = true) {
  const formData = new FormData();
  formData.append('file', file);

  const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`;
  const queryParam = dryRun ? '?dry_run=true' : '?dry_run=false';

  // Obter token CSRF
  const csrfToken = getCSRFToken();
  const headers = {};
  if (csrfToken) {
    headers['X-CSRFToken'] = csrfToken;
  }

  const response = await fetch(`${fullUrl}${queryParam}`, {
    method: 'POST',
    headers: headers,
    body: formData,
    credentials: 'include', // Incluir cookies de sessão
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Importa COMPRAS de CSV/XLSX.
 *
 * @param {File} file - Arquivo a enviar
 * @param {boolean} dryRun - Se true, apenas preview
 * @returns {Promise<object>} Relatório com stats e pendências
 */
export async function importCompras(file, dryRun = true) {
  return await postMultipart('/api/controle/import-compras/', file, dryRun);
}

/**
 * Importa AÇÕES de Controle de CSV/XLSX.
 *
 * @param {File} file - Arquivo a enviar
 * @param {boolean} dryRun - Se true, apenas preview
 * @returns {Promise<object>} Relatório com stats e pendências
 */
export async function importAcoes(file, dryRun = true) {
  return await postMultipart('/api/controle/import-acoes/', file, dryRun);
}

/**
 * Importa CADASTROS DAT de CSV/XLSX.
 *
 * @param {File} file - Arquivo a enviar
 * @param {boolean} dryRun - Se true, apenas preview
 * @returns {Promise<object>} Relatório com stats e pendências
 */
export async function importCadastros(file, dryRun = true) {
  return await postMultipart('/api/dat/import-cadastros/', file, dryRun);
}

/**
 * Lista COMPRAS com filtros opcionais.
 *
 * @param {object} filters - Filtros opcionais
 * @param {string} filters.municipio - Nome do município
 * @param {string} filters.projeto - Nome do projeto
 * @param {string} filters.uf - UF do município
 * @param {string} filters.from - Data início (YYYY-MM-DD)
 * @param {string} filters.to - Data fim (YYYY-MM-DD)
 * @param {string} filters.q - Busca em uso/código
 * @returns {Promise<Array>} Lista de compras
 */
export async function listCompras(filters = {}) {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.append(key, value);
  });

  const url = `/api/controle/compras/?${params.toString()}`;
  const response = await fetch(`${API_BASE}${url}`, {
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const data = await response.json();

  // Lidar com paginação DRF (results) ou array direto
  return data.results || data;
}

/**
 * Lista AÇÕES de Controle com filtros opcionais.
 *
 * @param {object} filters - Filtros opcionais
 * @returns {Promise<Array>} Lista de ações
 */
export async function listAcoes(filters = {}) {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.append(key, value);
  });

  const url = `/api/controle/acoes/?${params.toString()}`;
  const response = await fetch(`${API_BASE}${url}`, {
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const data = await response.json();

  // Lidar com paginação DRF (results) ou array direto
  return data.results || data;
}

/**
 * Lista CADASTROS DAT com filtros opcionais.
 *
 * @param {object} filters - Filtros opcionais
 * @returns {Promise<Array>} Lista de cadastros
 */
export async function listCadastros(filters = {}) {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.append(key, value);
  });

  const url = `/api/dat/acoes/?${params.toString()}`;
  const response = await fetch(`${API_BASE}${url}`, {
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const data = await response.json();

  // Lidar com paginação DRF (results) ou array direto
  return data.results || data;
}
