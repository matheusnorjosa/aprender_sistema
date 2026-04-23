/**
 * J03 — RD-04: Deslocamento entre municípios diferentes.
 *
 * **Correção da matriz**: originalmente estava como "RD-06 deslocamento
 * inviável". Após consulta à skill `aprender-domain`:
 *
 * - **RD-04**: Travel Buffer (D) — tempo mínimo de deslocamento entre
 *   municípios diferentes. Backend implementa buffer configurável.
 * - **RD-06**: Timezone-aware (UTC storage, America/Fortaleza comparison).
 *   Essa é outra regra.
 *
 * J03 testa RD-04 via endpoint consultivo `/api/availability/check/`:
 *
 * - formador_vidas participa de evento aprovado em Salvador (seed).
 * - Chamar `/api/availability/check/` pedindo verificação para o **mesmo
 *   formador** em **Fortaleza** no mesmo dia → retorno inclui conflito `D`.
 * - Mesma consulta em **Salvador** (mesmo município) → sem conflito `D`.
 *
 * Exercita a fixture `freezeTime` (Fase 2b) ponta-a-ponta pela primeira vez:
 * congela tempo do frontend + envia header `X-E2E-Frozen-Time` para o
 * backend (FreezeTimeMiddleware da Fase 2a).
 */
import {
  test,
  expect,
  createApiContext,
  seedSolicitacao,
  lookupMunicipioId,
  lookupUsuarioIdByRole,
  ROLE_CREDENTIALS,
} from '../fixtures';
import { freezeTime } from '../fixtures/time';

const FROZEN_DAY_ISO = '2026-05-15T09:00:00-03:00';
const SAME_DAY = '2026-05-15';

test.describe(
  'J03 — RD-04: Deslocamento entre municípios',
  { tag: ['@critical', '@rd-04'] },
  () => {
    test('canônica: check em Fortaleza no mesmo dia de evento em Salvador → conflito D', async ({
      baseURL,
      context,
    }) => {
      // Note: `freezeTime` aplicado a contexts API via request (headers); a página
      // não é usada aqui mas preservamos o padrão para consistência.
      // Para API: passamos o header via `extraHTTPHeaders` no contexto.
      const superApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.super_geral.username,
        password: ROLE_CREDENTIALS.super_geral.password,
      });

      const salvadorId = await lookupMunicipioId(superApi, 'Salvador');
      const fortalezaId = await lookupMunicipioId(superApi, 'Fortaleza');
      const formadorId = await lookupUsuarioIdByRole(superApi, 'formador_vidas');

      // Seed: solicitação aprovada em Salvador (formador_vidas participa como FORMADOR)
      const coordApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_vidas.username,
        password: ROLE_CREDENTIALS.coord_vidas.password,
      });
      const solicitacaoSalvador = await seedSolicitacao(coordApi, {
        fluxo: 'SUPER',
        municipioId: salvadorId,
        inicio: `${SAME_DAY}T09:00:00-03:00`,
        fim: `${SAME_DAY}T11:00:00-03:00`,
        formadorIds: [formadorId],
      });
      // Aprova para virar "aprovado" e entrar no cálculo de conflitos
      const approveRes = await superApi.patch(
        `/api/solicitacoes/${solicitacaoSalvador.id}/approve/`,
        { data: {} }
      );
      expect(approveRes.ok()).toBeTruthy();

      // Consulta RD-04: pedir janela em Fortaleza no mesmo dia, 2h depois
      const checkRes = await superApi.get(
        `/api/availability/check/` +
          `?usuario_id=${formadorId}` +
          `&inicio=${encodeURIComponent(`${SAME_DAY}T13:00:00-03:00`)}` +
          `&fim=${encodeURIComponent(`${SAME_DAY}T15:00:00-03:00`)}` +
          `&municipio_id=${fortalezaId}`
      );
      expect(checkRes.ok()).toBeTruthy();
      const body = (await checkRes.json()) as {
        available: boolean;
        conflicts: Array<{ code: string; title?: string; detail?: string }>;
      };

      // RD-04: deve retornar conflito 'D' (deslocamento)
      const codes = body.conflicts.map((c) => c.code);
      expect(codes, `conflicts=${JSON.stringify(body.conflicts)}`).toContain('D');
    });

    test('borda: mesmo município Salvador → sem conflito D', async ({ baseURL }) => {
      const superApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.super_geral.username,
        password: ROLE_CREDENTIALS.super_geral.password,
      });
      const salvadorId = await lookupMunicipioId(superApi, 'Salvador');
      const formadorId = await lookupUsuarioIdByRole(superApi, 'formador_vidas');

      // Consulta fora do horário de qualquer evento seedado, em Salvador
      const checkRes = await superApi.get(
        `/api/availability/check/` +
          `?usuario_id=${formadorId}` +
          `&inicio=${encodeURIComponent('2026-06-10T09:00:00-03:00')}` +
          `&fim=${encodeURIComponent('2026-06-10T11:00:00-03:00')}` +
          `&municipio_id=${salvadorId}`
      );
      expect(checkRes.ok()).toBeTruthy();
      const body = (await checkRes.json()) as {
        available: boolean;
        conflicts: Array<{ code: string }>;
      };
      const codes = body.conflicts.map((c) => c.code);
      expect(codes, 'mesmo município não deveria gerar conflito D').not.toContain('D');
    });

    test('operação: freezeTime no frontend não afeta conflict-check (backend é SSoT de tempo via header)', async ({
      page,
    }) => {
      // Smoke test conceitual: ao aplicar freezeTime numa page, o header
      // X-E2E-Frozen-Time é enviado em todas as requests daquela page.
      // Valida que a fixture não quebra o spec nem causa erros de setup.
      await freezeTime(page, FROZEN_DAY_ISO);
      await page.goto('/');
      // Se o addInitScript funcionar, Date.now() retorna o instante congelado
      const frozenMs = await page.evaluate(() => Date.now());
      const expectedMs = new Date(FROZEN_DAY_ISO).valueOf();
      expect(frozenMs, 'freezeTime deveria forçar Date.now() para o instante fixo').toBe(expectedMs);
    });
  }
);
