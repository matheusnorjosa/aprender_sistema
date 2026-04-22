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
import { waitForRouteReady } from '../helpers/wait';
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

      await aprovacoes.btnAprovar(solicitacao.id).click();

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

      const pageCoord = await authedPage('coord_vidas');
      await pageCoord.goto('/solicitacoes/minhas');
      await waitForRouteReady(pageCoord);

      const linha = pageCoord.getByRole('row').filter({ hasText: String(solicitacao.id) });
      await expect(linha).toBeVisible();
      await expect(linha).toContainText(/aprovad/i);
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

      // Tentativa de achar a linha — deve falhar
      const linha = pageSuper.getByRole('row').filter({ hasText: String(solicitacao.id) });
      await expect(linha).toHaveCount(0);
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

      const pageCoord = await authedPage('coord_vidas');
      await pageCoord.goto('/solicitacoes/minhas');
      await waitForRouteReady(pageCoord);

      const linha = pageCoord.getByRole('row').filter({ hasText: String(solicitacao.id) });
      await expect(linha).toBeVisible();
      await expect(linha).toContainText(/aprovad/i);
    });
  }
);
