/**
 * Helpers de seed via API para testes E2E.
 *
 * Princípio: toda criação de estado que NÃO é o foco do teste deve passar
 * por chamada direta de API, não pela UI. Isso deixa os testes mais rápidos
 * e menos suscetíveis a flake de renderização do wizard.
 *
 * Uso esperado dentro de fixtures:
 *
 *   const api = await createApiContext(baseURL, username, password);
 *   const solic = await seedSolicitacao(api, { projeto: 'Vidas' });
 *   await page.goto(`/solicitacoes/${solic.id}/editar`);
 */
import { APIRequestContext, expect, request } from '@playwright/test';

import { ROLE_CREDENTIALS } from './roles';

export interface ApiContextOptions {
  baseURL: string;
  username: string;
  password: string;
}

/**
 * Cria um `APIRequestContext` autenticado via CSRF + login endpoint.
 *
 * Reaproveita o padrão já usado em `auth.setup.ts`: fetch `/api/csrf/`,
 * POST `/api/auth/login/` com `X-CSRFToken` header, mantém cookies.
 *
 * O contexto retornado pode fazer GET/POST/PUT/DELETE autenticados no DRF.
 */
export async function createApiContext(options: ApiContextOptions): Promise<APIRequestContext> {
  // Passo 1: contexto temporário apenas para CSRF + login
  const tmpCtx = await request.newContext({ baseURL: options.baseURL });

  const csrfRes = await tmpCtx.get('/api/csrf/');
  expect(csrfRes.ok(), `[seed] /api/csrf falhou (${csrfRes.status()})`).toBeTruthy();
  const csrfData = (await csrfRes.json()) as { csrfToken?: string };
  const csrfToken = csrfData.csrfToken ?? '';
  expect(csrfToken, '[seed] csrfToken vazio').toBeTruthy();

  const loginRes = await tmpCtx.post('/api/auth/login/', {
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    data: { username: options.username, password: options.password },
  });
  expect(loginRes.ok(), `[seed] login falhou para ${options.username} (${loginRes.status()})`).toBeTruthy();

  // Extrai cookies pós-login (sessionid + csrftoken podem ter rotacionado)
  const state = await tmpCtx.storageState();
  const csrfCookie = state.cookies.find((c) => c.name === 'csrftoken');
  const finalCsrf = csrfCookie?.value ?? csrfToken;
  await tmpCtx.dispose();

  // Passo 2: contexto final com cookies + header X-CSRFToken default em TODAS as requests
  // (DRF exige CSRF em POST/PUT/PATCH/DELETE autenticados)
  const api = await request.newContext({
    baseURL: options.baseURL,
    storageState: state,
    extraHTTPHeaders: { 'X-CSRFToken': finalCsrf },
  });
  return api;
}

/**
 * Payload mínimo de solicitação. Campos opcionais são preenchidos com
 * defaults que correspondem ao projeto "TESTE E2E" seedado por
 * `seed_e2e_users.py`.
 */
/** Fluxo do projeto — define status inicial. */
export type ProjetoFluxo = 'SUPER' | 'NAO_SUPER';

export interface SeedSolicitacaoInput {
  /**
   * ID do projeto. Default: resolve por `fluxo` — `SUPER` → "TESTE E2E",
   * `NAO_SUPER` → "TESTE E2E NAO_SUPER".
   */
  projetoId?: number;
  /**
   * Fluxo a usar quando `projetoId` não é passado. Default: `SUPER`.
   * `NAO_SUPER` usa o projeto vinculado à gerência Vidas (auto-aprovado na criação).
   */
  fluxo?: ProjetoFluxo;
  /** ID do município. Default: busca "Salvador" via API. */
  municipioId?: number;
  /** ID do tipo de evento. Default: primeiro tipo ativo. */
  tipoEventoId?: number;
  /** Início do evento (ISO). Default: amanhã 09:00 Fortaleza. */
  inicio?: string;
  /** Fim do evento (ISO). Default: início + 2h. */
  fim?: string;
  /** IDs de formadores que participam. Default: nenhum. */
  formadorIds?: number[];
}

export interface SeededSolicitacao {
  id: number;
  status: string;
  projeto: number;
  municipio: number;
  /** ISO 8601 em UTC. Usado para buscar a linha em tabelas. */
  inicio: string;
  /** ISO 8601 em UTC. */
  fim: string;
}

/**
 * Cria uma solicitação via API. Retorna o objeto persistido.
 *
 * Os defaults assumem que `seed_e2e_users` já rodou. Se `projetoId` /
 * `municipioId` não forem passados, resolve via lookups.
 */
export async function seedSolicitacao(
  api: APIRequestContext,
  input: SeedSolicitacaoInput = {}
): Promise<SeededSolicitacao> {
  const projetoNome = input.fluxo === 'NAO_SUPER' ? 'TESTE E2E NAO_SUPER' : 'TESTE E2E';
  const projetoId = input.projetoId ?? (await findProjetoId(api, projetoNome));
  const municipioId = input.municipioId ?? (await findMunicipioId(api, 'Salvador'));
  const tipoEventoId = input.tipoEventoId ?? (await findFirstTipoEventoId(api));

  // Default: evento em horário aleatório dentro de uma janela futura larga
  // (7-365 dias), usando Date.now() como entrópia extra. Necessário porque
  // testes paralelos podem colidir em RD-01 (overlap) com o mesmo coord.
  // Também mixamos ms para diferenciar eventos em menos de 1 minuto de offset.
  const entropy = Date.now() % 1_000_000;
  const randomDaysAhead = 7 + ((entropy + Math.floor(Math.random() * 358)) % 358);
  const randomHour = 7 + Math.floor(Math.random() * 10); // 07:00..16:00
  const randomMinute = Math.floor(Math.random() * 60);
  const randomSecond = Math.floor(Math.random() * 60);
  const defaultInicio = new Date();
  defaultInicio.setDate(defaultInicio.getDate() + randomDaysAhead);
  defaultInicio.setHours(randomHour, randomMinute, randomSecond, 0);
  const inicio = input.inicio ?? defaultInicio.toISOString();

  const fim =
    input.fim ??
    (() => {
      const d = new Date(inicio);
      d.setHours(d.getHours() + 2);
      return d.toISOString();
    })();

  const payload: Record<string, unknown> = {
    projeto: projetoId,
    municipio: municipioId,
    tipo_evento: tipoEventoId,
    inicio,
    fim,
  };
  if (input.formadorIds?.length) {
    // Backend espera `extra_participants: { formador_ids: [...] }` — ver
    // views_solicitacao.py::perform_create (PR15).
    payload.extra_participants = { formador_ids: input.formadorIds };
  }

  // Retry loop: se receber 400 `availability_conflict` (RD-01 overlap),
  // desloca o dia (mantendo horários) e tenta de novo. Resolve race-condition
  // entre testes paralelos. Funciona também quando spec passa `inicio`
  // explícito (ex: J03/J06 que querem "mesmo dia" mas o dia pode colidir).
  const maxAttempts = 5;
  let lastStatus = 0;
  let lastBody = '';
  let currentInicio = payload.inicio as string;
  let currentFim = payload.fim as string;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const res = await api.post('/api/solicitacoes/', { data: payload });
    if (res.ok()) {
      return (await res.json()) as SeededSolicitacao;
    }
    lastStatus = res.status();
    lastBody = await res.text();
    if (res.status() !== 400 || !lastBody.includes('availability_conflict')) {
      break;
    }
    // Desloca o DIA do inicio/fim mantendo os horários. Preserva semântica
    // "mesmo dia" que specs J03/J06 dependem (evento + consulta no mesmo dia).
    const dStart = new Date(currentInicio);
    const dFim = new Date(currentFim);
    const shiftDays = Math.floor(Math.random() * 200) + 10; // 10..209 dias
    dStart.setDate(dStart.getDate() + shiftDays);
    dFim.setDate(dFim.getDate() + shiftDays);
    currentInicio = dStart.toISOString();
    currentFim = dFim.toISOString();
    payload.inicio = currentInicio;
    payload.fim = currentFim;
  }

  expect(false, `[seed] POST /api/solicitacoes falhou após ${maxAttempts} tentativas: ${lastStatus} ${lastBody}`).toBeTruthy();
  throw new Error('unreachable');
}

async function findProjetoId(api: APIRequestContext, nome: string): Promise<number> {
  const res = await api.get(`/api/lookup/projetos/?q=${encodeURIComponent(nome)}`);
  expect(res.ok(), `[seed] lookup projetos falhou (${res.status()})`).toBeTruthy();
  // Schema do endpoint: [{ id, label: "CODIGO - NOME", kind: "projeto", fluxo: "SUPER"|"NAO_SUPER" }]
  const data = (await res.json()) as
    | { results?: Array<{ id: number; label: string }> }
    | Array<{ id: number; label: string }>;
  const list = Array.isArray(data) ? data : (data.results ?? []);
  // Match exato por sufixo " - {nome}" (formato "CODIGO - NOME") ou pelo próprio label
  const exact = list.find((p) => p.label === nome || p.label.endsWith(` - ${nome}`));
  expect(exact, `[seed] projeto "${nome}" nao encontrado (rode manage.py seed_e2e_users)`).toBeTruthy();
  return exact!.id;
}

/**
 * Busca o ID de um município pelo nome. Exportado para uso direto em specs
 * que precisam de múltiplos municípios (ex: J03 testa deslocamento entre
 * Salvador e Fortaleza).
 */
export async function lookupMunicipioId(api: APIRequestContext, nome: string): Promise<number> {
  return findMunicipioId(api, nome);
}

/**
 * Busca o ID de um usuário pelo display name (first_name + last_name).
 *
 * Nota: o endpoint `/api/lookup/usuarios/` retorna apenas `{id, label, kind}`
 * onde `label` é o display name. Não há filtro por username/email. Para
 * obter o ID a partir de um role, prefira `lookupUsuarioIdByRole(api, role)`
 * — que usa o `displayName` já cadastrado em `ROLE_CREDENTIALS`.
 */
export async function lookupUsuarioId(api: APIRequestContext, displayName: string): Promise<number> {
  // O endpoint /api/lookup/usuarios/?q=X só faz match em first_name OR last_name
  // (não busca "first last" juntos). Usamos apenas o primeiro token e
  // filtramos o label completo do lado do cliente.
  const firstToken = displayName.split(/\s+/)[0] ?? displayName;
  const res = await api.get(`/api/lookup/usuarios/?q=${encodeURIComponent(firstToken)}`);
  expect(res.ok(), `[seed] lookup usuarios falhou (${res.status()})`).toBeTruthy();
  // Schema: [{ id, label: "First Last", kind: "usuario" }]
  const data = (await res.json()) as
    | { results?: Array<{ id: number; label: string }> }
    | Array<{ id: number; label: string }>;
  const list = Array.isArray(data) ? data : (data.results ?? []);
  const match = list.find((u) => u.label === displayName);
  expect(
    match,
    `[seed] usuario com displayName "${displayName}" nao encontrado (q=${firstToken}; candidatos=${list.map((u) => u.label).join(', ')})`
  ).toBeTruthy();
  return match!.id;
}

/**
 * Busca o ID de um usuário a partir do role declarado em `ROLE_CREDENTIALS`.
 * Helper preferido quando o spec sabe o role, não o display name.
 */
export async function lookupUsuarioIdByRole(
  api: APIRequestContext,
  role: keyof typeof ROLE_CREDENTIALS
): Promise<number> {
  const entry = ROLE_CREDENTIALS[role];
  expect(entry, `[seed] role "${role}" não está em ROLE_CREDENTIALS`).toBeTruthy();
  return lookupUsuarioId(api, entry.displayName);
}

async function findMunicipioId(api: APIRequestContext, nome: string): Promise<number> {
  const res = await api.get(`/api/lookup/municipios/?q=${encodeURIComponent(nome)}`);
  expect(res.ok(), `[seed] lookup municipios falhou (${res.status()})`).toBeTruthy();
  // Schema: [{ id, label: "NOME-UF", kind: "municipio" }]
  const data = (await res.json()) as
    | { results?: Array<{ id: number; label: string }> }
    | Array<{ id: number; label: string }>;
  const list = Array.isArray(data) ? data : (data.results ?? []);
  // Match por prefixo "{nome}-" (formato "Salvador-BA") ou pelo label completo
  const match = list.find((m) => m.label === nome || m.label.startsWith(`${nome}-`));
  expect(match, `[seed] municipio "${nome}" nao encontrado`).toBeTruthy();
  return match!.id;
}

async function findFirstTipoEventoId(api: APIRequestContext): Promise<number> {
  const res = await api.get('/api/lookup/tipos-evento/');
  expect(res.ok(), `[seed] lookup tipos-evento falhou (${res.status()})`).toBeTruthy();
  const data = (await res.json()) as { results?: Array<{ id: number }> } | Array<{ id: number }>;
  const list = Array.isArray(data) ? data : data.results ?? [];
  expect(list.length, '[seed] nenhum tipo_evento encontrado').toBeGreaterThan(0);
  return list[0]!.id;
}
