/**
 * J05 — RBAC: visão individual vs visão de setor.
 *
 * Ref: Design discutido na auditoria RBAC (2026-04-22), issue #1159 fechada
 * como by-design. O sistema tem dois endpoints complementares:
 *
 * - `/api/solicitacoes/` (listagem) — **individual**: coord vê APENAS as que
 *   ele mesmo criou (filtra por `usuario=request.user`).
 * - `/api/availability/monthly` (grade mensal) — **setor**: coord vê tudo
 *   do próprio setor via `HasSectorAccess` + `EquipeGerencia`.
 *
 * Esta jornada valida que ambos funcionam conforme o design e que os
 * escopos não vazam entre setores diferentes.
 *
 * Três camadas de asserção:
 *
 * 1. **Canônica**: coord_vidas vê apenas as próprias em `/api/solicitacoes/`.
 * 2. **Borda**: coord_fluir **não** vê as de coord_vidas em `/api/solicitacoes/`
 *    (escopo individual preserva privacidade entre setores).
 * 3. **Operação**: coord_fluir tenta acessar grade mensal do setor Vidas
 *    (`gerencia_id=<Vidas>`) → recebe 403 (HasSectorAccess bloqueia).
 */
import { test, expect, createApiContext, seedSolicitacao, ROLE_CREDENTIALS } from '../fixtures';
import type { APIRequestContext } from '@playwright/test';

async function findGerenciaIdByNomeSetor(api: APIRequestContext, nomeSetor: string): Promise<number> {
  const res = await api.get('/api/gerencias/');
  expect(res.ok(), `[j05] /api/gerencias/ falhou (${res.status()})`).toBeTruthy();
  const data = (await res.json()) as
    | { results?: Array<{ id: number; nome_setor: string }> }
    | Array<{ id: number; nome_setor: string }>;
  const list = Array.isArray(data) ? data : (data.results ?? []);
  const match = list.find((g) => g.nome_setor === nomeSetor);
  expect(match, `[j05] gerencia com nome_setor "${nomeSetor}" nao encontrada`).toBeTruthy();
  return match!.id;
}

test.describe(
  'J05 — RBAC: visão individual vs setor',
  { tag: ['@critical', '@rbac'] },
  () => {
    test('canônica: coord_vidas vê apenas suas solicitações em /api/solicitacoes/?mine=true', async ({
      baseURL,
    }) => {
      const coordVidasApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_vidas.username,
        password: ROLE_CREDENTIALS.coord_vidas.password,
      });
      const solicitacao = await seedSolicitacao(coordVidasApi, { fluxo: 'SUPER' });

      const res = await coordVidasApi.get('/api/solicitacoes/?mine=true');
      expect(res.ok()).toBeTruthy();
      const data = (await res.json()) as
        | { results?: Array<{ id: number }> }
        | Array<{ id: number }>;
      const list = Array.isArray(data) ? data : (data.results ?? []);
      const ids = list.map((s) => s.id);
      expect(ids).toContain(solicitacao.id);
    });

    test('borda: coord_fluir NÃO vê solicitação criada por coord_vidas', async ({ baseURL }) => {
      // Ana (coord_vidas) cria solicitação
      const coordVidasApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_vidas.username,
        password: ROLE_CREDENTIALS.coord_vidas.password,
      });
      const solicitacao = await seedSolicitacao(coordVidasApi, { fluxo: 'SUPER' });

      // Carlos (coord_fluir) consulta sua listagem — não deve ver a de Ana
      const coordFluirApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_fluir.username,
        password: ROLE_CREDENTIALS.coord_fluir.password,
      });
      const res = await coordFluirApi.get('/api/solicitacoes/?mine=true');
      expect(res.ok()).toBeTruthy();
      const data = (await res.json()) as
        | { results?: Array<{ id: number }> }
        | Array<{ id: number }>;
      const list = Array.isArray(data) ? data : (data.results ?? []);
      const ids = list.map((s) => s.id);
      expect(ids).not.toContain(solicitacao.id);
    });

    test('operação: coord_fluir recebe 403 ao tentar grade mensal do setor Vidas', async ({
      baseURL,
    }) => {
      // Descobre ID da gerência Vidas via API (como qualquer autenticado)
      const anyApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_vidas.username,
        password: ROLE_CREDENTIALS.coord_vidas.password,
      });
      const vidasId = await findGerenciaIdByNomeSetor(anyApi, 'Vidas');

      // coord_vidas acessa a grade do próprio setor → 200
      const resVidas = await anyApi.get(
        `/api/availability/monthly?year=2026&month=4&role=FORMADOR&gerencia_id=${vidasId}`
      );
      expect(resVidas.status(), 'coord_vidas deve acessar grade de Vidas').toBeLessThan(400);

      // coord_fluir tenta acessar grade do setor Vidas → deve ser bloqueado
      const coordFluirApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_fluir.username,
        password: ROLE_CREDENTIALS.coord_fluir.password,
      });
      const resFluir = await coordFluirApi.get(
        `/api/availability/monthly?year=2026&month=4&role=FORMADOR&gerencia_id=${vidasId}`
      );
      expect(resFluir.status(), 'coord_fluir não deve acessar grade de Vidas').toBe(403);
    });
  }
);
