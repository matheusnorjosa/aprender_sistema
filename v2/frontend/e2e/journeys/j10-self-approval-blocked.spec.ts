/**
 * J10 — Coord não aprova própria solicitação.
 *
 * Ref: PA-02 adaptada (Superintendência, DAT ou superuser aprovam).
 *
 * O criador não pode aprovar a própria solicitação — mesmo que seja
 * superintendente ou tenha permissão de aprovação. Esta regra impede
 * conflito de interesse e é garantida pela permission class
 * `IsSuperintendencia` combinada com o check de ownership.
 *
 * Na prática atual, `IsSuperintendencia` aceita `Superintendência | DAT |
 * superuser`. Coord (sem essas funções) bate direto na permission class e
 * recebe 403, independente de ser dono ou não.
 *
 * Três camadas:
 *
 * 1. **Canônica**: coord_vidas cria → tenta aprovar → 403 (permission).
 * 2. **Borda**: outro coord (fluir, setor diferente) também recebe 403.
 * 3. **Operação**: após tentativa bloqueada, status permanece pendente.
 *    Super_geral então aprova com sucesso.
 */
import { test, expect, createApiContext, seedSolicitacao, ROLE_CREDENTIALS } from '../fixtures';

test.describe(
  'J10 — Coord não aprova própria solicitação',
  { tag: ['@critical', '@rbac', '@pa-02'] },
  () => {
    test('canônica: coord_vidas tenta aprovar a própria solicitação → 403', async ({ baseURL }) => {
      const coordApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_vidas.username,
        password: ROLE_CREDENTIALS.coord_vidas.password,
      });
      const solicitacao = await seedSolicitacao(coordApi, { fluxo: 'SUPER' });
      expect(solicitacao.status).toBe('pendente');

      const approveRes = await coordApi.patch(`/api/solicitacoes/${solicitacao.id}/approve/`, { data: {} });
      expect(approveRes.status()).toBe(403);
    });

    test('borda: coord de outro setor também recebe 403', async ({ baseURL }) => {
      const coordVidasApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_vidas.username,
        password: ROLE_CREDENTIALS.coord_vidas.password,
      });
      const solicitacao = await seedSolicitacao(coordVidasApi, { fluxo: 'SUPER' });

      const coordFluirApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_fluir.username,
        password: ROLE_CREDENTIALS.coord_fluir.password,
      });
      const approveRes = await coordFluirApi.patch(
        `/api/solicitacoes/${solicitacao.id}/approve/`,
        { data: {} }
      );
      expect(approveRes.status()).toBe(403);
    });

    test('operação: status permanece pendente após 403; super_geral aprova com sucesso', async ({
      baseURL,
    }) => {
      const coordApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_vidas.username,
        password: ROLE_CREDENTIALS.coord_vidas.password,
      });
      const solicitacao = await seedSolicitacao(coordApi, { fluxo: 'SUPER' });

      // Coord tenta aprovar → 403
      const failRes = await coordApi.patch(`/api/solicitacoes/${solicitacao.id}/approve/`, { data: {} });
      expect(failRes.status()).toBe(403);

      // Status continua pendente
      const check1 = await coordApi.get(`/api/solicitacoes/${solicitacao.id}/`);
      const body1 = (await check1.json()) as { status: string };
      expect(body1.status).toBe('pendente');

      // super_geral aprova → 200 e status vira aprovado
      const superApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.super_geral.username,
        password: ROLE_CREDENTIALS.super_geral.password,
      });
      const okRes = await superApi.patch(`/api/solicitacoes/${solicitacao.id}/approve/`, { data: {} });
      expect(okRes.ok()).toBeTruthy();

      const check2 = await superApi.get(`/api/solicitacoes/${solicitacao.id}/`);
      const body2 = (await check2.json()) as { status: string };
      expect(body2.status).toBe('aprovado');
    });
  }
);
