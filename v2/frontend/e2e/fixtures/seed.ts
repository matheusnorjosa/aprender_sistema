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
  const api = await request.newContext({ baseURL: options.baseURL });

  const csrfRes = await api.get('/api/csrf/');
  expect(csrfRes.ok(), `[seed] /api/csrf falhou (${csrfRes.status()})`).toBeTruthy();
  const csrfData = (await csrfRes.json()) as { csrfToken?: string };
  const csrfToken = csrfData.csrfToken ?? '';
  expect(csrfToken, '[seed] csrfToken vazio').toBeTruthy();

  const loginRes = await api.post('/api/auth/login/', {
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    data: { username: options.username, password: options.password },
  });
  expect(loginRes.ok(), `[seed] login falhou para ${options.username} (${loginRes.status()})`).toBeTruthy();

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

  const amanha = new Date();
  amanha.setDate(amanha.getDate() + 1);
  amanha.setHours(9, 0, 0, 0);
  const inicio = input.inicio ?? amanha.toISOString();

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
    payload.formador_ids = input.formadorIds;
  }

  const res = await api.post('/api/solicitacoes/', { data: payload });
  expect(res.ok(), `[seed] POST /api/solicitacoes falhou: ${res.status()} ${await res.text()}`).toBeTruthy();
  const created = (await res.json()) as SeededSolicitacao;
  return created;
}

async function findProjetoId(api: APIRequestContext, nome: string): Promise<number> {
  const res = await api.get(`/api/lookup/projetos/?q=${encodeURIComponent(nome)}`);
  expect(res.ok(), `[seed] lookup projetos falhou (${res.status()})`).toBeTruthy();
  const data = (await res.json()) as
    | { results?: Array<{ id: number; nome: string }> }
    | Array<{ id: number; nome: string }>;
  const list = Array.isArray(data) ? data : (data.results ?? []);
  // Match exato por nome; fallback no primeiro — mas aviso se desambiguou assim.
  const exact = list.find((p) => p.nome === nome);
  expect(exact, `[seed] projeto "${nome}" nao encontrado (rode manage.py seed_e2e_users)`).toBeTruthy();
  return exact!.id;
}

async function findMunicipioId(api: APIRequestContext, nome: string): Promise<number> {
  const res = await api.get(`/api/lookup/municipios/?q=${encodeURIComponent(nome)}`);
  expect(res.ok(), `[seed] lookup municipios falhou (${res.status()})`).toBeTruthy();
  const data = (await res.json()) as { results?: Array<{ id: number; nome: string }> } | Array<{ id: number; nome: string }>;
  const list = Array.isArray(data) ? data : data.results ?? [];
  const match = list.find((m) => m.nome === nome) ?? list[0];
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
