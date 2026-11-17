/**
 * Helper de time-freeze para testes E2E.
 *
 * Combina duas estratégias para determinismo temporal completo:
 *
 * 1. **Frontend**: `page.clock.setFixedTime` (relógio nativo do Playwright) faz
 *    `Date.now()` e `new Date()` devolverem o instante fixo, inclusive no bundle e
 *    nas bibliotecas de data (dayjs, AntD DatePicker). Os timers seguem rodando.
 *    Até o FER-65 isto era um `Date` falso injetado à mão por `addInitScript`.
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

  // Frontend: relógio nativo; vale para a página atual e as próximas navegações.
  await page.clock.setFixedTime(fixedMs);

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
  // Frontend: o `page.clock` não tem "desinstalar"; para voltar ao tempo real no
  // navegador, use uma página nova.
}
