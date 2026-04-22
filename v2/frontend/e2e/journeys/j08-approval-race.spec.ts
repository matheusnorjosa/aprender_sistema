/**
 * J08 — Aprovação concorrente (race-condition).
 *
 * Ref: PA-07 ("Mandatory Tests") não define race explicitamente, mas o
 * service `approve_solicitacao` usa `select_for_update()` para garantir
 * exclusão mútua. Esta jornada é a prova E2E do comportamento pretendido:
 * dois aprovadores disparam PATCH `/approve/` simultaneamente, **apenas um
 * vence**; o outro recebe 400 `already_approved`.
 *
 * Sem o `select_for_update`, teríamos race: ambos leriam `status=pendente`,
 * ambos escreveriam `aprovado`, e AuditLog registraria **dois** APPROVE —
 * violando integridade.
 *
 * Três camadas:
 *
 * 1. **Canônica**: dois supers em paralelo → exatamente 1 sucesso, 1 falha
 *    com `already_approved`.
 * 2. **Borda**: múltiplos paralelos (N=3) → exatamente 1 sucesso, N-1 falhas.
 * 3. **Operação**: AuditLog após race tem exatamente 1 entrada APPROVE
 *    (não 2) — confirma integridade do `select_for_update`.
 */
import { test, expect, createApiContext, seedSolicitacao, ROLE_CREDENTIALS } from '../fixtures';

test.describe(
  'J08 — Aprovação concorrente (race-condition)',
  { tag: ['@critical', '@race', '@pa-07'] },
  () => {
    test('canônica: dois supers aprovam em paralelo → 1 vence, 1 recebe already_approved', async ({
      baseURL,
    }) => {
      const coordApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_vidas.username,
        password: ROLE_CREDENTIALS.coord_vidas.password,
      });
      const solicitacao = await seedSolicitacao(coordApi, { fluxo: 'SUPER' });

      // Dois aprovadores distintos: super_geral + dat_e2e (ambos passam IsSuperintendencia)
      const superApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.super_geral.username,
        password: ROLE_CREDENTIALS.super_geral.password,
      });
      const datApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.dat_e2e.username,
        password: ROLE_CREDENTIALS.dat_e2e.password,
      });

      // Promise.all dispara as duas requests simultaneamente.
      const [resSuper, resDat] = await Promise.all([
        superApi.patch(`/api/solicitacoes/${solicitacao.id}/approve/`, { data: {} }),
        datApi.patch(`/api/solicitacoes/${solicitacao.id}/approve/`, { data: {} }),
      ]);

      const statuses = [resSuper.status(), resDat.status()].sort();
      // Exatamente 1 sucesso (200) + 1 conflito (400)
      expect(statuses, `statuses=${statuses} — esperado [200, 400]`).toEqual([200, 400]);

      // Lado que falhou deve ter code `already_approved`
      const loser = resSuper.status() === 400 ? resSuper : resDat;
      const body = (await loser.json()) as { code?: string; detail?: string };
      expect([body.code, body.detail].some((v) => v && /already.?approved|aprovad/i.test(v))).toBeTruthy();

      // Status final persistido
      const check = await superApi.get(`/api/solicitacoes/${solicitacao.id}/`);
      expect(((await check.json()) as { status: string }).status).toBe('aprovado');
    });

    test('borda: 3 aprovadores em paralelo → 1 sucesso, 2 already_approved', async ({ baseURL }) => {
      const coordApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_vidas.username,
        password: ROLE_CREDENTIALS.coord_vidas.password,
      });
      const solicitacao = await seedSolicitacao(coordApi, { fluxo: 'SUPER' });

      const ctx1 = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.super_geral.username,
        password: ROLE_CREDENTIALS.super_geral.password,
      });
      const ctx2 = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.super_e2e.username,
        password: ROLE_CREDENTIALS.super_e2e.password,
      });
      const ctx3 = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.dat_e2e.username,
        password: ROLE_CREDENTIALS.dat_e2e.password,
      });

      const responses = await Promise.all([
        ctx1.patch(`/api/solicitacoes/${solicitacao.id}/approve/`, { data: {} }),
        ctx2.patch(`/api/solicitacoes/${solicitacao.id}/approve/`, { data: {} }),
        ctx3.patch(`/api/solicitacoes/${solicitacao.id}/approve/`, { data: {} }),
      ]);
      const statuses = responses.map((r) => r.status()).sort();
      expect(statuses, `statuses=${statuses} — esperado [200, 400, 400]`).toEqual([200, 400, 400]);
    });

    test('operação: AuditLog tem exatamente 1 APPROVE após race (integridade select_for_update)', async ({
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
      const datApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.dat_e2e.username,
        password: ROLE_CREDENTIALS.dat_e2e.password,
      });

      await Promise.all([
        superApi.patch(`/api/solicitacoes/${solicitacao.id}/approve/`, { data: {} }),
        datApi.patch(`/api/solicitacoes/${solicitacao.id}/approve/`, { data: {} }),
      ]);

      const logsRes = await superApi.get(`/api/audit-logs/?action=APPROVE&model_name=Solicitacao`);
      expect(logsRes.ok()).toBeTruthy();
      const logsData = (await logsRes.json()) as
        | { results?: Array<{ details: Record<string, unknown> }> }
        | Array<{ details: Record<string, unknown> }>;
      const logs = Array.isArray(logsData) ? logsData : (logsData.results ?? []);
      const matches = logs.filter((l) => l.details?.solicitacao_id === solicitacao.id);

      expect(matches.length, `Esperado exatamente 1 AuditLog APPROVE; got ${matches.length}`).toBe(1);
    });
  }
);
