/**
 * Wait helpers que substituem `waitForLoadState('networkidle')` (deprecado).
 *
 * Observação da Fase 1: a troca `networkidle → load` foi agressiva demais —
 * `load` dispara antes do React hidratar o `#root`, causando falsos
 * negativos em asserções sobre DOM estrutural (ex: `<main>`, `<h1>`).
 *
 * Padrão correto: aguardar EVIDÊNCIA OBSERVÁVEL de que o React renderizou.
 */
import type { Page } from '@playwright/test';

/**
 * Aguarda o shell do React hidratar.
 *
 * Critério: `#root` existe e tem children. Esse é o sinal mais leve e
 * confiável de que `ReactDOM.createRoot(root).render(...)` terminou.
 *
 * Tempo típico: <500ms em dev server, <200ms em build estático.
 *
 * @param page Página Playwright
 * @param timeout Tempo máximo em ms (default 15000)
 */
export async function waitForAppReady(page: Page, timeout = 15000): Promise<void> {
  await page.waitForLoadState('domcontentloaded');
  await page.waitForFunction(
    () => {
      const root = document.getElementById('root');
      return !!root && root.children.length > 0;
    },
    null,
    { timeout }
  );
}

/**
 * Aguarda overlay de loading do AntD sumir.
 *
 * Útil em páginas autenticadas que mostram `<Spin fullscreen>` durante
 * carga inicial do `/api/me/` e permissions. Complemento (não substituto)
 * de `waitForAppReady`.
 */
export async function waitForLoadingOverlayGone(page: Page, timeout = 15000): Promise<void> {
  await page.waitForFunction(
    () => {
      const overlay = document.querySelector('.ant-spin-fullscreen.ant-spin-fullscreen-show');
      if (!overlay) return true;
      const style = window.getComputedStyle(overlay);
      return style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0';
    },
    null,
    { timeout }
  );
}

/**
 * Combo: shell renderizou + overlay sumiu. Uso típico após navegação
 * para rota autenticada.
 */
export async function waitForRouteReady(page: Page, timeout = 15000): Promise<void> {
  await waitForAppReady(page, timeout);
  await waitForLoadingOverlayGone(page, timeout);
}
