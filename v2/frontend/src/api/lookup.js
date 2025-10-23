/**
 * API Client - Lookup (Autocomplete) e Validação
 *
 * Endpoints para autocomplete de municípios, projetos, tipos de evento, usuários
 * e validação de solicitações.
 */

import { fetchAPI, buildUrl } from './config';

/**
 * Buscar municípios (autocomplete)
 *
 * @param {string} q - Query string
 * @returns {Promise<Array<{id, label, kind}>>}
 */
export async function lookupMunicipios(q = '') {
  const url = buildUrl('/lookup/municipios/', { q });
  return await fetchAPI(url);
}

/**
 * Buscar projetos (autocomplete)
 *
 * @param {string} q - Query string
 * @returns {Promise<Array<{id, label, kind}>>}
 */
export async function lookupProjetos(q = '') {
  const url = buildUrl('/lookup/projetos/', { q });
  return await fetchAPI(url);
}

/**
 * Buscar tipos de evento (autocomplete)
 *
 * @param {string} q - Query string
 * @returns {Promise<Array<{id, label, kind}>>}
 */
export async function lookupTiposEvento(q = '') {
  const url = buildUrl('/lookup/tipos-evento/', { q });
  return await fetchAPI(url);
}

/**
 * Buscar usuários (autocomplete)
 *
 * @param {string} q - Query string
 * @param {string} role - Filtro por role/grupo (opcional)
 * @returns {Promise<Array<{id, label, kind, email}>>}
 */
export async function lookupUsuarios(q = '', role = '') {
  const url = buildUrl('/lookup/usuarios/', { q, role });
  return await fetchAPI(url);
}

/**
 * Validar dados de solicitação antes do submit
 *
 * @param {Object} payload - Dados da solicitação
 * @param {string|object} payload.municipio - Nome ou {id}
 * @param {string|object} payload.projeto - Nome ou {id}
 * @param {string|object} payload.tipo_evento - Nome ou {id}
 * @param {string} payload.date - Data (YYYY-MM-DD)
 * @param {string} payload.start - Horário início (HH:MM)
 * @param {string} payload.end - Horário fim (HH:MM)
 * @param {object} payload.participants - {coordenador, formadores[], coord_acompanha[]}
 * @returns {Promise<{ok: boolean, errors: Array, canonical: Object}>}
 */
export async function validateSolic(payload) {
  return await fetchAPI('/solicitacoes/validate/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
