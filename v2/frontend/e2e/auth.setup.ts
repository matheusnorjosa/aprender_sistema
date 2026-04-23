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

// Setup serial — evita flake de rate-limit/concorrência em /api/auth/login/
// quando 12 roles tentam autenticar simultaneamente no dev server.
// Cada role leva ~1-2s; o custo total (~15-25s) é aceitável e roda apenas
// quando storageState não existe ou expirou.
setup.describe.configure({ mode: 'serial' });

for (const role of E2E_ROLES) {
  const { username, password } = ROLE_CREDENTIALS[role as E2eRole];

  setup(`authenticate as ${role}`, async ({ page }) => {
    // Login com retry inline — resiliente a flake de rate-limit/session no
    // dev server quando vários setups correm em sequência.
    const maxAttempts = 3;
    let lastError: string | null = null;

    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      await page.goto('/');

      const csrfToken = await page.evaluate(async () => {
        const resp = await fetch('/api/csrf/', { credentials: 'include' });
        if (!resp.ok) return null;
        const data = (await resp.json()) as { csrfToken?: string };
        return data?.csrfToken ?? null;
      });
      if (!csrfToken) {
        lastError = `csrfToken vazio (tentativa ${attempt})`;
        continue;
      }

      const loginOk = await page.evaluate(
        async ({ u, p, t }: { u: string; p: string; t: string }) => {
          const resp = await fetch('/api/auth/login/', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': t },
            body: JSON.stringify({ username: u, password: p }),
          });
          return { ok: resp.ok, status: resp.status };
        },
        { u: username, p: password, t: csrfToken }
      );
      if (loginOk.ok) {
        break;
      }
      lastError = `login HTTP ${loginOk.status} (tentativa ${attempt})`;
      // pequeno backoff exponencial
      await page.waitForTimeout(500 * attempt);
    }
    expect(lastError === null || lastError.startsWith('login HTTP') === false || !lastError, `[setup:${role}] falhou após ${maxAttempts} tentativas — último erro: ${lastError}`).toBeTruthy();

    // Valida session
    const meOk2 = await page.evaluate(async () => {
      const resp = await fetch('/api/me/', { credentials: 'include' });
      return resp.ok;
    });
    expect(meOk2, `[setup:${role}] /api/me falhou após login bem-sucedido`).toBeTruthy();

    await page.context().storageState({ path: storageStatePath(role as E2eRole) });
  });
}
