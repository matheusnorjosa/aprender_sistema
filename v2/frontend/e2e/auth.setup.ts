/**
 * Setup de autenticação multi-role.
 *
 * Faz login uma vez por role e salva o storageState em
 * `e2e/.auth/{role}.json`. Specs pegam esse arquivo via fixture
 * `authedPage(role)` (ver `fixtures/roles.ts`) ou via `storageState`
 * declarado em `playwright.config.ts`.
 *
 * Rodar roles em paralelo (uma task por role) mantém o setup rápido mesmo
 * com N usuários.
 */
import { test as setup, expect } from '@playwright/test';
import { E2E_ROLES, ROLE_CREDENTIALS, storageStatePath, type E2eRole } from './fixtures/roles';

for (const role of E2E_ROLES) {
  const { username, password } = ROLE_CREDENTIALS[role as E2eRole];

  setup(`authenticate as ${role}`, async ({ page }) => {
    // Abre o shell antes de buscar CSRF para evitar CSP forçando HTTPS
    await page.goto('/');

    const csrfToken = await page.evaluate(async () => {
      const resp = await fetch('/api/csrf/', { credentials: 'include' });
      if (!resp.ok) return null;
      const data = (await resp.json()) as { csrfToken?: string };
      return data?.csrfToken ?? null;
    });
    expect(csrfToken, `[setup:${role}] csrfToken vazio`).toBeTruthy();

    const loginOk = await page.evaluate(
      async ({ u, p, t }: { u: string; p: string; t: string }) => {
        const resp = await fetch('/api/auth/login/', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': t },
          body: JSON.stringify({ username: u, password: p }),
        });
        return resp.ok;
      },
      { u: username, p: password, t: csrfToken! }
    );
    expect(loginOk, `[setup:${role}] login falhou`).toBeTruthy();

    const meOk = await page.evaluate(async () => {
      const resp = await fetch('/api/me/', { credentials: 'include' });
      return resp.ok;
    });
    expect(meOk, `[setup:${role}] /api/me falhou`).toBeTruthy();

    await page.context().storageState({ path: storageStatePath(role as E2eRole) });
  });
}
