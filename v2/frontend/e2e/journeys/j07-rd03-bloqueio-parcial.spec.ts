/**
 * J07 — RD-03: Bloqueio parcial (tipo P).
 *
 * **Correção da matriz**: inicialmente descrita como "RD-04 bloqueio pontual".
 * Após consulta à skill `aprender-domain`:
 *
 * - **RD-03** = Partial Block (P) — impede eventos **dentro** do subintervalo
 *   bloqueado; fora dele, tudo certo.
 * - **RD-04** = Travel Buffer (D) — deslocamento entre municípios (J03).
 *
 * Complementa J06, que cobriu RD-01 (overlap X) + RD-02 (bloqueio total T).
 * Com J07, a família de bloqueios está completa.
 *
 * Regra de negócio (apps/core/services/availability_service.py:9):
 *
 * > RD-03: Bloqueio Parcial (P) impede dentro do subintervalo
 *
 * Três camadas:
 *
 * 1. **Canônica**: formador cria `AvailabilityBlock` tipo `P` 09:00-11:00;
 *    check dentro do intervalo → `conflicts` inclui `P`.
 * 2. **Borda**: check fora do intervalo no mesmo dia (ex: 14:00-16:00) →
 *    sem `P` (regra de "fora do subintervalo está livre").
 * 3. **Operação**: após criação, `GET /api/availability-blocks/?owner=me` retorna o
 *    bloqueio com `tipo=P` — espelho de persistência.
 */
import {
  test,
  expect,
  createApiContext,
  lookupMunicipioId,
  lookupUsuarioIdByRole,
  ROLE_CREDENTIALS,
} from '../fixtures';

/**
 * Gera um dia futuro único por execução (evita colisão entre rodadas
 * paralelas/retries do mesmo spec no mesmo banco).
 */
function uniqueFutureDay(offsetDays = 0): string {
  const d = new Date();
  const extra = Math.floor(Math.random() * 200);
  d.setDate(d.getDate() + 30 + extra + offsetDays);
  return d.toISOString().slice(0, 10);
}

test.describe(
  'J07 — RD-03: Bloqueio parcial (P)',
  { tag: ['@critical', '@rd-03'] },
  () => {
    test('canônica: check dentro do subintervalo bloqueado → conflito P', async ({ baseURL }) => {
      const DAY = uniqueFutureDay();
      // formador_fluir cria bloqueio P 09:00-11:00 no DAY (usa formador diferente do J06 para
      // evitar acoplamento de estado entre jornadas que rodam em paralelo)
      const formadorApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.formador_fluir.username,
        password: ROLE_CREDENTIALS.formador_fluir.password,
      });
      const blockRes = await formadorApi.post('/api/availability-blocks/', {
        data: {
          tipo: 'P',
          start_date: DAY,
          end_date: DAY,
          start_time: '09:00:00',
          end_time: '11:00:00',
        },
      });
      expect(blockRes.ok(), `bloqueio P deveria criar: ${blockRes.status()} ${await blockRes.text()}`).toBeTruthy();

      const superApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.super_geral.username,
        password: ROLE_CREDENTIALS.super_geral.password,
      });
      const salvadorId = await lookupMunicipioId(superApi, 'Salvador');
      const formadorId = await lookupUsuarioIdByRole(superApi, 'formador_fluir');

      // Consulta DENTRO do subintervalo (10:00-10:30 cai em 09:00-11:00)
      const checkRes = await superApi.get(
        `/api/availability/check/` +
          `?usuario_id=${formadorId}` +
          `&inicio=${encodeURIComponent(`${DAY}T10:00:00-03:00`)}` +
          `&fim=${encodeURIComponent(`${DAY}T10:30:00-03:00`)}` +
          `&municipio_id=${salvadorId}`
      );
      expect(checkRes.ok()).toBeTruthy();
      const body = (await checkRes.json()) as {
        conflicts: Array<{ code: string }>;
      };
      const codes = body.conflicts.map((c) => c.code);
      expect(codes, `conflicts=${JSON.stringify(body.conflicts)}`).toContain('P');
    });

    test('borda: check fora do subintervalo no mesmo dia → sem conflito P', async ({ baseURL }) => {
      const DAY = uniqueFutureDay();
      // Cria bloqueio P 09:00-11:00 para ESTE dia específico do teste.
      const formadorApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.formador_fluir.username,
        password: ROLE_CREDENTIALS.formador_fluir.password,
      });
      await formadorApi.post('/api/availability-blocks/', {
        data: {
          tipo: 'P',
          start_date: DAY,
          end_date: DAY,
          start_time: '09:00:00',
          end_time: '11:00:00',
        },
      });

      const superApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.super_geral.username,
        password: ROLE_CREDENTIALS.super_geral.password,
      });
      const salvadorId = await lookupMunicipioId(superApi, 'Salvador');
      const formadorId = await lookupUsuarioIdByRole(superApi, 'formador_fluir');

      // Consulta FORA do intervalo (14:00-16:00, completamente fora de 09:00-11:00)
      const checkRes = await superApi.get(
        `/api/availability/check/` +
          `?usuario_id=${formadorId}` +
          `&inicio=${encodeURIComponent(`${DAY}T14:00:00-03:00`)}` +
          `&fim=${encodeURIComponent(`${DAY}T16:00:00-03:00`)}` +
          `&municipio_id=${salvadorId}`
      );
      expect(checkRes.ok()).toBeTruthy();
      const body = (await checkRes.json()) as {
        conflicts: Array<{ code: string }>;
      };
      const codes = body.conflicts.map((c) => c.code);
      expect(codes, 'fora do subintervalo não deveria gerar conflito P').not.toContain('P');
    });

    test('operação: GET /api/bloqueios/ lista o bloqueio tipo P criado', async ({ baseURL }) => {
      const formadorApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.formador_fluir.username,
        password: ROLE_CREDENTIALS.formador_fluir.password,
      });

      // Cria (ou revalida) bloqueio P específico para este teste
      const MARKER_DAY = uniqueFutureDay();
      const createRes = await formadorApi.post('/api/availability-blocks/', {
        data: {
          tipo: 'P',
          start_date: MARKER_DAY,
          end_date: MARKER_DAY,
          start_time: '13:00:00',
          end_time: '15:00:00',
        },
      });
      expect(createRes.ok()).toBeTruthy();

      // Lista bloqueios do próprio formador
      const listRes = await formadorApi.get('/api/availability-blocks/?owner=me');
      expect(listRes.ok()).toBeTruthy();
      const data = (await listRes.json()) as
        | { results?: Array<{ tipo: string; start_date: string; end_date: string }> }
        | Array<{ tipo: string; start_date: string; end_date: string }>;
      const list = Array.isArray(data) ? data : (data.results ?? []);
      const match = list.find(
        (b) => b.tipo === 'P' && b.start_date === MARKER_DAY && b.end_date === MARKER_DAY
      );
      expect(match, `bloqueio P em ${MARKER_DAY} deveria estar listado`).toBeTruthy();
    });
  }
);
