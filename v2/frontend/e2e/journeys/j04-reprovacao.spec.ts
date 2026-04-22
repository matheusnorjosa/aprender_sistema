/**
 * J04 — Reprovação (fluxo completo + PA-05 audit).
 *
 * Ref: Regras PA (skill `aprender-domain` confirmada em 2026-04-22):
 *
 * - **PA-02**: Superintendência, DAT ou superuser reprovam (permission
 *   `IsSuperintendencia`).
 * - **PA-05**: AuditLog registra `REJECT` com `details.justificativa`.
 *   A justificativa é opcional ("when applicable") — backend aceita vazio.
 *
 * **Observação sobre PA-04**: PA-04 é sobre status inicial (SUPER=pendente,
 * NAO_SUPER=aprovado) e já está coberta por J01a/J01b. Não existe regra
 * que force motivo obrigatório na reprovação — o motivo é opcional por
 * `aprender-domain`. Se a equipe decidir que deveria ser obrigatório, é
 * decisão de produto, não gap de código.
 *
 * Quatro camadas de asserção:
 *
 * 1. **Canônica**: super reprova com motivo → status `reprovado` + AuditLog
 *    REJECT com `details.justificativa` preservada.
 * 2. **Borda (idempotência)**: segunda tentativa de reprovar → 400
 *    `already_rejected`.
 * 3. **Borda (motivo opcional)**: reprovar **sem** motivo → aceito. Documenta
 *    o comportamento real alinhado à PA-05.
 * 4. **Operação**: coord vê `reprovado` em `/solicitacoes/minhas` e
 *    solicitação some da fila de `/aprovacoes`.
 */
import { test, expect, createApiContext, seedSolicitacao, ROLE_CREDENTIALS } from '../fixtures';
import { waitForRouteReady } from '../helpers/wait';
import { AprovacoesPage } from '../pages/AprovacoesPage';

test.describe(
  'J04 — Reprovação: fluxo completo + AuditLog (PA-05)',
  { tag: ['@critical', '@pa-02', '@pa-05', '@fluxo-super'] },
  () => {
    test('canônica: super reprova com motivo → status=reprovado + AuditLog registra justificativa', async ({
      baseURL,
    }) => {
      const coordApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_vidas.username,
        password: ROLE_CREDENTIALS.coord_vidas.password,
      });
      const solicitacao = await seedSolicitacao(coordApi, { fluxo: 'SUPER' });
      expect(solicitacao.status).toBe('pendente');

      const superApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.super_geral.username,
        password: ROLE_CREDENTIALS.super_geral.password,
      });
      const motivo = 'Data fora da janela de planejamento';
      const rejectRes = await superApi.patch(`/api/solicitacoes/${solicitacao.id}/reject/`, {
        data: { reason: motivo },
      });
      expect(rejectRes.ok()).toBeTruthy();

      // Status final
      const check = await superApi.get(`/api/solicitacoes/${solicitacao.id}/`);
      expect(((await check.json()) as { status: string }).status).toBe('reprovado');

      // PA-05: AuditLog registra justificativa
      const logsRes = await superApi.get(
        `/api/audit-logs/?action=REJECT&model_name=Solicitacao`
      );
      expect(logsRes.ok()).toBeTruthy();
      const logsData = (await logsRes.json()) as
        | { results?: Array<{ details: Record<string, unknown> }> }
        | Array<{ details: Record<string, unknown> }>;
      const logs = Array.isArray(logsData) ? logsData : (logsData.results ?? []);
      const match = logs.find((l) => l.details?.solicitacao_id === solicitacao.id);
      expect(match, 'AuditLog REJECT deveria existir para esta solicitação').toBeTruthy();
      expect(match!.details.justificativa).toBe(motivo);
    });

    test('borda (idempotência): segunda tentativa de reprovar retorna already_rejected', async ({
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

      const first = await superApi.patch(`/api/solicitacoes/${solicitacao.id}/reject/`, {
        data: { reason: 'primeira' },
      });
      expect(first.ok()).toBeTruthy();

      const second = await superApi.patch(`/api/solicitacoes/${solicitacao.id}/reject/`, {
        data: { reason: 'segunda tentativa' },
      });
      expect(second.status()).toBe(400);
      const body = (await second.json()) as { code?: string; detail?: string };
      expect([body.code, body.detail].some((v) => v && /already.?reject|reprovad/i.test(v))).toBeTruthy();
    });

    test('borda (motivo opcional): reprovar sem motivo é aceito (PA-05 justificativa opcional)', async ({
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
      // Sem `reason`/`justificativa` no body
      const res = await superApi.patch(`/api/solicitacoes/${solicitacao.id}/reject/`, { data: {} });
      expect(res.ok(), 'PA-05: justificativa é opcional, backend aceita vazio').toBeTruthy();

      const check = await superApi.get(`/api/solicitacoes/${solicitacao.id}/`);
      expect(((await check.json()) as { status: string }).status).toBe('reprovado');
    });

    test('operação: coord vê reprovado em /solicitacoes/minhas; solicitação some de /aprovacoes', async ({
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
      const rejectRes = await superApi.patch(`/api/solicitacoes/${solicitacao.id}/reject/`, {
        data: { reason: 'conflito com feriado' },
      });
      expect(rejectRes.ok()).toBeTruthy();

      // Coord vê status `reprovado` na sua listagem
      const pageCoord = await authedPage('coord_vidas');
      await pageCoord.goto('/solicitacoes/minhas');
      await waitForRouteReady(pageCoord);
      const linha = pageCoord.getByRole('row').filter({ hasText: String(solicitacao.id) });
      await expect(linha).toBeVisible();
      await expect(linha).toContainText(/reprovad/i);

      // Super abre /aprovacoes — a solicitação reprovada não deve aparecer na fila
      const pageSuper = await authedPage('super_geral');
      const aprovacoes = new AprovacoesPage(pageSuper);
      await aprovacoes.goto();
      const linhaAprov = pageSuper.getByRole('row').filter({ hasText: String(solicitacao.id) });
      await expect(linhaAprov).toHaveCount(0);
    });
  }
);
