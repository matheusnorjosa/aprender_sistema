/**
 * J06 — Indisponibilidade: RD-01 (overlap) + RD-02 (bloqueio total).
 *
 * **Correção da matriz**: originalmente "Formador fora de janela → RD-01".
 * Após consulta à skill `aprender-domain`, RD-01 é sobreposição de eventos.
 * "Fora de janela" é melhor coberta por RD-02 (bloqueio total) ou RD-03
 * (bloqueio parcial).
 *
 * Regras testadas (ref: apps/core/services/availability_service.py):
 *
 * - **RD-01**: overlap ≥ 1 minuto entre eventos aprovados → conflito `X`.
 *   Edge case: eventos adjacentes (end == start) NÃO são conflito.
 * - **RD-02**: AvailabilityBlock tipo `T` (total) impede qualquer evento
 *   no intervalo → conflito `T`.
 *
 * Três camadas:
 *
 * 1. **Canônica (RD-01)**: seed evento aprovado; check em janela sobreposta
 *    → retorna conflito `X`.
 * 2. **Borda (RD-01)**: check em janela adjacente (end do seed == start da
 *    consulta) → sem conflito `X` (regra de adjacência).
 * 3. **Operação (RD-02)**: formador cria bloqueio total `T` para o dia;
 *    check nesse dia → conflito `T`.
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

const DAY_RD01 = '2026-07-05';
const DAY_RD02 = '2026-07-12';

test.describe(
  'J06 — Indisponibilidade: RD-01 (overlap) + RD-02 (bloqueio total)',
  { tag: ['@critical', '@rd-01', '@rd-02'] },
  () => {
    test('canônica (RD-01): overlap ≥ 1min entre eventos aprovados → conflito X', async ({ baseURL }) => {
      const superApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.super_geral.username,
        password: ROLE_CREDENTIALS.super_geral.password,
      });
      const salvadorId = await lookupMunicipioId(superApi, 'Salvador');
      const formadorId = await lookupUsuarioIdByRole(superApi, 'formador_vidas');

      // Seed evento aprovado: 09:00-11:00
      const coordApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_vidas.username,
        password: ROLE_CREDENTIALS.coord_vidas.password,
      });
      const solic = await seedSolicitacao(coordApi, {
        fluxo: 'SUPER',
        municipioId: salvadorId,
        inicio: `${DAY_RD01}T09:00:00-03:00`,
        fim: `${DAY_RD01}T11:00:00-03:00`,
        formadorIds: [formadorId],
      });
      const approveRes = await superApi.patch(`/api/solicitacoes/${solic.id}/approve/`, { data: {} });
      expect(approveRes.ok()).toBeTruthy();

      // Consulta janela sobreposta: 10:30-12:30 (overlap de 30min com 09:00-11:00)
      const checkRes = await superApi.get(
        `/api/availability/check/` +
          `?usuario_id=${formadorId}` +
          `&inicio=${encodeURIComponent(`${DAY_RD01}T10:30:00-03:00`)}` +
          `&fim=${encodeURIComponent(`${DAY_RD01}T12:30:00-03:00`)}` +
          `&municipio_id=${salvadorId}`
      );
      expect(checkRes.ok()).toBeTruthy();
      const body = (await checkRes.json()) as {
        conflicts: Array<{ code: string }>;
      };
      const codes = body.conflicts.map((c) => c.code);
      expect(codes, `conflicts=${JSON.stringify(body.conflicts)}`).toContain('X');
    });

    test('borda (RD-01): janela adjacente (end == start) NÃO é conflito X', async ({ baseURL }) => {
      const superApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.super_geral.username,
        password: ROLE_CREDENTIALS.super_geral.password,
      });
      const salvadorId = await lookupMunicipioId(superApi, 'Salvador');
      const formadorId = await lookupUsuarioIdByRole(superApi, 'formador_vidas');

      // Seed evento aprovado: 09:00-11:00
      const coordApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.coord_vidas.username,
        password: ROLE_CREDENTIALS.coord_vidas.password,
      });
      const solic = await seedSolicitacao(coordApi, {
        fluxo: 'SUPER',
        municipioId: salvadorId,
        inicio: `${DAY_RD01}T14:00:00-03:00`,
        fim: `${DAY_RD01}T16:00:00-03:00`,
        formadorIds: [formadorId],
      });
      const approveRes = await superApi.patch(`/api/solicitacoes/${solic.id}/approve/`, { data: {} });
      expect(approveRes.ok()).toBeTruthy();

      // Consulta janela adjacente: 16:00-18:00 (começa exatamente quando o outro acaba)
      const checkRes = await superApi.get(
        `/api/availability/check/` +
          `?usuario_id=${formadorId}` +
          `&inicio=${encodeURIComponent(`${DAY_RD01}T16:00:00-03:00`)}` +
          `&fim=${encodeURIComponent(`${DAY_RD01}T18:00:00-03:00`)}` +
          `&municipio_id=${salvadorId}`
      );
      expect(checkRes.ok()).toBeTruthy();
      const body = (await checkRes.json()) as {
        conflicts: Array<{ code: string }>;
      };
      const codes = body.conflicts.map((c) => c.code);
      expect(codes, 'evento adjacente não é overlap RD-01').not.toContain('X');
    });

    test('operação (RD-02): bloqueio total cobre o dia → conflito T', async ({ baseURL }) => {
      // formador_vidas cria bloqueio total para o dia inteiro
      const formadorApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.formador_vidas.username,
        password: ROLE_CREDENTIALS.formador_vidas.password,
      });
      const blockRes = await formadorApi.post('/api/bloqueios/', {
        data: {
          tipo: 'T',
          start_date: DAY_RD02,
          end_date: DAY_RD02,
          start_time: '00:00:00',
          end_time: '23:59:00',
        },
      });
      expect(blockRes.ok(), `bloqueio total deveria criar: ${blockRes.status()} ${await blockRes.text()}`).toBeTruthy();

      const superApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.super_geral.username,
        password: ROLE_CREDENTIALS.super_geral.password,
      });
      const salvadorId = await lookupMunicipioId(superApi, 'Salvador');
      const formadorId = await lookupUsuarioIdByRole(superApi, 'formador_vidas');

      // Consulta janela no dia bloqueado
      const checkRes = await superApi.get(
        `/api/availability/check/` +
          `?usuario_id=${formadorId}` +
          `&inicio=${encodeURIComponent(`${DAY_RD02}T10:00:00-03:00`)}` +
          `&fim=${encodeURIComponent(`${DAY_RD02}T12:00:00-03:00`)}` +
          `&municipio_id=${salvadorId}`
      );
      expect(checkRes.ok()).toBeTruthy();
      const body = (await checkRes.json()) as {
        available: boolean;
        conflicts: Array<{ code: string }>;
      };
      const codes = body.conflicts.map((c) => c.code);
      expect(codes, `conflicts=${JSON.stringify(body.conflicts)}`).toContain('T');
    });
  }
);
