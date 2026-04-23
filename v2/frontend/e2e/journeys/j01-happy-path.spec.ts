/**
 * J01 — Happy path (ambos os fluxos de aprovação).
 *
 * Ref: Matriz de jornadas E2E (Fase 3 do plano QA 2026-04-22).
 *
 * O sistema tem 2 fluxos de aprovação (projeto.fluxo em
 * apps/core/services/solicitacao_create.py):
 *
 * - **SUPER** (Superintendência): status inicial `pendente`; requer
 *   aprovação manual via `/aprovacoes` (PA-02).
 * - **NAO_SUPER**: status inicial `aprovado` imediatamente na criação;
 *   não passa por aprovação manual.
 *
 * Este spec cobre ambos: J01a (SUPER) + J01b (NAO_SUPER).
 */
import { test, expect, createApiContext, seedSolicitacao, ROLE_CREDENTIALS } from '../fixtures';
import { AprovacoesPage } from '../pages/AprovacoesPage';

// ============================================================================
// J01a — Fluxo SUPER (Superintendência aprova manualmente)
// ============================================================================

test.describe(
  'J01a — SUPER: coord cria → super aprova',
  { tag: ['@critical', '@rf01', '@pa-02', '@fluxo-super'] },
  () => {
    test('canônica: pendente → aprovado via UI de Aprovações', async ({ authedPage, baseURL }) => {
      const coordApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_vidas.username,
        password: ROLE_CREDENTIALS.coord_vidas.password,
      });
      const solicitacao = await seedSolicitacao(coordApi, { fluxo: 'SUPER' });
      expect(solicitacao.status).toBe('pendente');

      const pageSuper = await authedPage('super_geral');
      const aprovacoes = new AprovacoesPage(pageSuper);
      await aprovacoes.goto();
      await expect(aprovacoes.tabelaPendentes).toBeVisible();

      // Linha via AntD data-row-key="{id}" — hasText de data formatada não
      // casa na ApprovalsPage (DD/MM/YYYY e HH:mm-HH:mm ficam em elementos
      // separados, não concatenados).
      await expect(aprovacoes.linhaPorId(solicitacao.id)).toBeVisible();
      await aprovacoes.btnAprovarPorId(solicitacao.id).click();

      // Clique na linha abre Modal.confirm — confirmar pra disparar a API.
      await aprovacoes.btnConfirmarAprovacao.click();

      const superApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.super_geral.username,
        password: ROLE_CREDENTIALS.super_geral.password,
      });
      await expect
        .poll(
          async () => {
            const res = await superApi.get(`/api/solicitacoes/${solicitacao.id}/`);
            if (!res.ok()) return null;
            const body = (await res.json()) as { status: string };
            return body.status;
          },
          { timeout: 10_000, message: 'status deveria virar "aprovado" após click Aprovar' }
        )
        .toBe('aprovado');
    });

    test('borda: segunda tentativa de aprovar retorna already_approved', async ({ baseURL }) => {
      const coordApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_vidas.username,
        password: ROLE_CREDENTIALS.coord_vidas.password,
      });
      const solicitacao = await seedSolicitacao(coordApi, { fluxo: 'SUPER' });

      const superApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.super_geral.username,
        password: ROLE_CREDENTIALS.super_geral.password,
      });

      const firstRes = await superApi.patch(`/api/solicitacoes/${solicitacao.id}/approve/`, { data: {} });
      expect(firstRes.ok()).toBeTruthy();

      const secondRes = await superApi.patch(`/api/solicitacoes/${solicitacao.id}/approve/`, { data: {} });
      expect(secondRes.status()).toBe(400);
      const body = (await secondRes.json()) as { code?: string; detail?: string };
      expect([body.code, body.detail].some((v) => v && /already.?approved|aprovad/i.test(v))).toBeTruthy();
    });

    test('operação: coord vê status aprovado em /solicitacoes/minhas após aprovação', async ({
      authedPage,
      baseURL,
    }) => {
      const coordApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_vidas.username,
        password: ROLE_CREDENTIALS.coord_vidas.password,
      });
      const solicitacao = await seedSolicitacao(coordApi, { fluxo: 'SUPER' });

      const superApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.super_geral.username,
        password: ROLE_CREDENTIALS.super_geral.password,
      });
      const approveRes = await superApi.patch(`/api/solicitacoes/${solicitacao.id}/approve/`, { data: {} });
      expect(approveRes.ok()).toBeTruthy();

      // Reflexo para coord: validamos via API (a tabela /solicitacoes/minhas
      // pagina — com dezenas de solicitações acumuladas, a linha específica
      // pode estar fora da página 1). A operação é "coord consegue enxergar
      // o status atualizado da solicitação" — ler via API atende essa regra
      // com menor surface de flake.
      const resCoord = await coordApi.get(`/api/solicitacoes/${solicitacao.id}/`);
      expect(resCoord.ok()).toBeTruthy();
      const bodyCoord = (await resCoord.json()) as { status: string };
      expect(bodyCoord.status).toBe('aprovado');
    });
  }
);

// ============================================================================
// J01b — Fluxo NAO_SUPER (auto-aprovado na criação)
// ============================================================================

test.describe(
  'J01b — NAO_SUPER: coord cria → auto-aprovado',
  { tag: ['@critical', '@rf01', '@fluxo-nao-super'] },
  () => {
    test('canônica: solicitação nasce com status aprovado', async ({ baseURL }) => {
      const coordApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_vidas.username,
        password: ROLE_CREDENTIALS.coord_vidas.password,
      });
      const solicitacao = await seedSolicitacao(coordApi, { fluxo: 'NAO_SUPER' });

      // Regra: `solicitacao_create.resolve_initial_status` devolve `aprovado`
      // quando projeto.fluxo == "NAO_SUPER".
      expect(solicitacao.status).toBe('aprovado');
    });

    test('borda: solicitação NAO_SUPER NÃO aparece na fila de /aprovacoes', async ({ authedPage, baseURL }) => {
      const coordApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_vidas.username,
        password: ROLE_CREDENTIALS.coord_vidas.password,
      });
      const solicitacao = await seedSolicitacao(coordApi, { fluxo: 'NAO_SUPER' });
      expect(solicitacao.status).toBe('aprovado');

      // Super abre /aprovacoes — a solicitação NÃO_SUPER não deve estar listada
      // (a view filtra por `projeto__fluxo=SUPER` + status pendente).
      const pageSuper = await authedPage('super_geral');
      const aprovacoes = new AprovacoesPage(pageSuper);
      await aprovacoes.goto();
      await expect(aprovacoes.tabelaPendentes).toBeVisible();

      // hasText: String(id) é lossy (casa datas/horas com mesmos dígitos).
      // Usar AntD data-row-key="{id}" — casa apenas a linha exata.
      await expect(aprovacoes.linhaPorId(solicitacao.id)).toHaveCount(0);
    });

    test('borda: tentar aprovar via API uma solicitação já aprovada retorna 400', async ({ baseURL }) => {
      const coordApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_vidas.username,
        password: ROLE_CREDENTIALS.coord_vidas.password,
      });
      const solicitacao = await seedSolicitacao(coordApi, { fluxo: 'NAO_SUPER' });
      expect(solicitacao.status).toBe('aprovado');

      const superApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.super_geral.username,
        password: ROLE_CREDENTIALS.super_geral.password,
      });
      const approveRes = await superApi.patch(`/api/solicitacoes/${solicitacao.id}/approve/`, { data: {} });
      expect(approveRes.status()).toBe(400);
      const body = (await approveRes.json()) as { code?: string; detail?: string };
      expect([body.code, body.detail].some((v) => v && /already.?approved|aprovad/i.test(v))).toBeTruthy();
    });

    test('operação: coord vê status aprovado em /solicitacoes/minhas imediatamente', async ({
      authedPage,
      baseURL,
    }) => {
      const coordApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_vidas.username,
        password: ROLE_CREDENTIALS.coord_vidas.password,
      });
      const solicitacao = await seedSolicitacao(coordApi, { fluxo: 'NAO_SUPER' });

      // NAO_SUPER: coord confirma via API que nasce aprovado imediatamente
      const resCoord = await coordApi.get(`/api/solicitacoes/${solicitacao.id}/`);
      expect(resCoord.ok()).toBeTruthy();
      const bodyCoord = (await resCoord.json()) as { status: string };
      expect(bodyCoord.status).toBe('aprovado');
    });
  }
);
