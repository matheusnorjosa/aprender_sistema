/**
 * Helper de time-freeze para testes E2E.
 *
 * Combina duas estratégias para determinismo temporal completo:
 *
 * 1. **Frontend**: `page.addInitScript` sobrescreve `Date.now()` e o construtor
 *    `Date` para retornar um instante fixo. Afeta `new Date()` no JS do bundle,
 *    bibliotecas de formatação (date-fns, dayjs, AntD DatePicker), timers.
 *
 * 2. **Backend**: header `X-E2E-Frozen-Time` enviado em TODAS as requests via
 *    `page.setExtraHTTPHeaders`. Lido pelo `FreezeTimeMiddleware` (Fase 2a)
 *    quando `DEBUG_E2E=true + INCLUDE_DEV_TOOLS=true` no Django settings.
 *
 * Sem os dois, as RD-01..RD-08 podem falhar por divergência entre "agora" do
 * browser e "agora" do servidor.
 */
import type { Page } from '@playwright/test';

/**
 * Congela o tempo em um instante ISO-8601 fixo.
 *
 * @param page Página Playwright
 * @param isoDatetime ISO com timezone obrigatório (ex: '2026-04-21T09:00:00-03:00').
 *                    Sem timezone → erro (evita ambiguidade).
 *
 * @example
 *   test('RD-06 bloqueia deslocamento inviável', async ({ page }) => {
 *     await freezeTime(page, '2026-04-21T09:00:00-03:00');
 *     await page.goto('/solicitacoes/nova');
 *     // ...
 *   });
 */
export async function freezeTime(page: Page, isoDatetime: string): Promise<void> {
  const parsed = new Date(isoDatetime);
  if (Number.isNaN(parsed.valueOf())) {
    throw new Error(`freezeTime: ISO datetime inválido: ${isoDatetime}`);
  }
  if (!/[+-]\d{2}:?\d{2}|Z$/.test(isoDatetime)) {
    throw new Error(
      `freezeTime: ISO datetime precisa de timezone explícito (ex: '+...' ou 'Z'). Recebido: ${isoDatetime}`
    );
  }

  const fixedMs = parsed.valueOf();

  // Frontend: sobrescreve Date antes do bundle carregar
  await page.addInitScript(
    ({ fixedMs: ms }: { fixedMs: number }) => {
      const RealDate = Date;
      const fixedIso = new RealDate(ms).toISOString();

      // eslint-disable-next-line @typescript-eslint/no-extraneous-class
      class FrozenDate extends RealDate {
        constructor(...args: unknown[]) {
          if (args.length === 0) {
            super(ms);
          } else {
            // @ts-expect-error — passthrough para construtor real
            super(...args);
          }
        }
        static now() {
          return ms;
        }
        static parse = RealDate.parse;
        static UTC = RealDate.UTC;
      }

      // @ts-expect-error — substituição global deliberada
      globalThis.Date = FrozenDate;
      // Marcador para debug
      (globalThis as unknown as { __FROZEN_TIME__?: string }).__FROZEN_TIME__ = fixedIso;
    },
    { fixedMs }
  );

  // Backend: header em cada request
  await page.setExtraHTTPHeaders({
    'X-E2E-Frozen-Time': isoDatetime,
  });
}

/**
 * Remove o congelamento (se quiser voltar ao tempo real no meio do teste).
 * Raramente necessário — normalmente um teste congela uma vez e não volta.
 */
export async function unfreezeTime(page: Page): Promise<void> {
  await page.setExtraHTTPHeaders({});
  // Frontend: não há como remover `addInitScript` em runtime; recarregar página
  // restauraria `Date`, mas quase sempre é mais simples criar uma nova página.
}
