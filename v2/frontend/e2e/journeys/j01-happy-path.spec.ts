/**
 * J01 — Happy path: coord cria solicitação → super aprova.
 *
 * Ref: Matriz de jornadas E2E (Fase 3 do plano QA 2026-04-22).
 * Regras: RF01 (criar solicitação), PA-02 (Superintendência aprova).
 *
 * Três camadas de asserção:
 *
 * 1. **Canônica**: coord cria solicitação via API → fica `pendente` →
 *    super_geral abre /aprovacoes, clica "Aprovar" → status vira `aprovado`.
 *
 * 2. **Borda (idempotência)**: tentar aprovar a mesma solicitação duas vezes
 *    → segunda chamada retorna 400 com `code=already_approved`.
 *
 * 3. **Operação**: após aprovação, coord vê a mesma solicitação com status
 *    "aprovado" em /solicitacoes/minhas (reflexo cruzado entre telas).
 */
import { test, expect, createApiContext, seedSolicitacao, ROLE_CREDENTIALS } from '../fixtures';
import { waitForRouteReady } from '../helpers/wait';
import { AprovacoesPage } from '../pages/AprovacoesPage';

test.describe('J01 — Happy path: coord cria → super aprova', { tag: ['@critical', '@rf01', '@pa-02'] }, () => {
  test('canônica: pendente → aprovada via UI de Aprovações', async ({ authedPage, baseURL }) => {
    // Arrange: coord cria via API (sidecar, mais rápido que wizard)
    const coordApi = await createApiContext({
      baseURL: baseURL!,
      username: ROLE_CREDENTIALS.coord_vidas.username,
      password: ROLE_CREDENTIALS.coord_vidas.password,
    });
    const solicitacao = await seedSolicitacao(coordApi);
    expect(solicitacao.status).toBe('pendente');

    // Act: super_geral aprova via UI
    const pageSuper = await authedPage('super_geral');
    const aprovacoes = new AprovacoesPage(pageSuper);
    await aprovacoes.goto();
    await expect(aprovacoes.tabelaPendentes).toBeVisible();

    await aprovacoes.btnAprovar(solicitacao.id).click();

    // Assert canônica: status aprovado via API (evita flake de UI refresh)
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
    const solicitacao = await seedSolicitacao(coordApi);

    const superApi = await createApiContext({
      baseURL: baseURL!,
      username: ROLE_CREDENTIALS.super_geral.username,
      password: ROLE_CREDENTIALS.super_geral.password,
    });

    // Primeira aprovação: sucesso
    const firstRes = await superApi.patch(`/api/solicitacoes/${solicitacao.id}/approve/`, { data: {} });
    expect(firstRes.ok()).toBeTruthy();

    // Segunda aprovação: deve bloquear
    const secondRes = await superApi.patch(`/api/solicitacoes/${solicitacao.id}/approve/`, { data: {} });
    expect(secondRes.status()).toBe(400);
    const body = (await secondRes.json()) as { code?: string; detail?: string };
    // Aceita tanto `code` quanto mensagem — contrato pode variar entre ValidationAPIError e DRF default
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
    const solicitacao = await seedSolicitacao(coordApi);

    // Aprova via API (foco do teste é o reflexo na tela do coord, não a UI de aprovação)
    const superApi = await createApiContext({
      baseURL: baseURL!,
      username: ROLE_CREDENTIALS.super_geral.username,
      password: ROLE_CREDENTIALS.super_geral.password,
    });
    const approveRes = await superApi.patch(`/api/solicitacoes/${solicitacao.id}/approve/`, { data: {} });
    expect(approveRes.ok()).toBeTruthy();

    // Coord abre /solicitacoes/minhas e confirma reflexo
    const pageCoord = await authedPage('coord_vidas');
    await pageCoord.goto('/solicitacoes/minhas');
    await waitForRouteReady(pageCoord);

    const linha = pageCoord.getByRole('row').filter({ hasText: String(solicitacao.id) });
    await expect(linha).toBeVisible();
    // Status renderizado na linha da tabela — aceita variações comuns de rótulo
    await expect(linha).toContainText(/aprovad/i);
  });
});
