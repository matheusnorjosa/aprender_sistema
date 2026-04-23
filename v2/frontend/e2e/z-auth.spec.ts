/**
 * Testes E2E para fluxo de Login/Logout
 *
 * Testes que verificam o fluxo de autenticação.
 */

import { test, expect } from '@playwright/test';

// Credenciais de teste (usuários E2E)
const ADMIN_USER = {
  username: 'coord_e2e@test.com',
  password: 'testpass123',
};

test.describe('Fluxo de Autenticação', () => {
  // Estes 3 primeiros testes NÃO usam o estado de autenticação salvo
  test.describe('Login', () => {
    test.use({ storageState: { cookies: [], origins: [] } });

    test('1. Página de login carrega corretamente', async ({ page }) => {
      await page.goto('/');

      // Deve mostrar formulário de login (h1, não h2)
      await expect(page.locator('h1:has-text("Login")')).toBeVisible();
      await expect(page.locator('input[id="login_username"]')).toBeVisible();
      await expect(page.locator('input[id="login_password"]')).toBeVisible();
      await expect(page.locator('button[type="submit"]')).toBeVisible();
    });

    test('2. Login com superuser funciona e mostra dashboard', async ({ page }) => {
      await page.goto('/');

      // Preencher formulário
      await page.fill('input[id="login_username"]', ADMIN_USER.username);
      await page.fill('input[id="login_password"]', ADMIN_USER.password);

      // Clicar no botão de login
      await page.click('button[type="submit"]');

      // Verificar que o sidebar está visível (indica que logou)
      await expect(
        page.getByRole('navigation', { name: 'Navegacao principal' })
      ).toBeVisible({ timeout: 15000 });
    });

    test('3. Login com credenciais inválidas mostra erro', async ({ page }) => {
      await page.goto('/');

      // Preencher com credenciais inválidas
      await page.fill('input[id="login_username"]', 'usuario_invalido');
      await page.fill('input[id="login_password"]', 'senha_errada');

      // Clicar no botão de login
      await page.click('button[type="submit"]');

      // Deve mostrar mensagem de erro
      await expect(page.locator('.ant-message-error')).toBeVisible({ timeout: 5000 });
    });
  });

  // Logout é destrutivo (invalida sessão server-side). Não pode usar o
  // storageState compartilhado dos setups — runs consecutivos/paralelos
  // se contaminariam. Isola com storage vazio + login inline.
  test.describe('Logout', () => {
    test.use({ storageState: { cookies: [], origins: [] } });

    test('4. Logout funciona corretamente', async ({ page }) => {
      // Login inline (storage vazio, sessão autocontida)
      await page.goto('/');
      await page.fill('input[id="login_username"]', ADMIN_USER.username);
      await page.fill('input[id="login_password"]', ADMIN_USER.password);
      await page.click('button[type="submit"]');
      await expect(
        page.getByRole('navigation', { name: 'Navegacao principal' })
      ).toBeVisible({ timeout: 15000 });

      // Click no botão "Sair" do AppHeader. Selector antigo
      // `[data-testid="app-logout-button"]` não existe mais no componente
      // (AppHeader.tsx:179-186 renderiza `<Button>Sair</Button>` sem
      // data-testid).
      await page.getByRole('button', { name: /sair/i }).click();

      // Volta para tela de login
      await expect(page.locator('h1:has-text("Login")')).toBeVisible({ timeout: 10000 });
    });
  });
});
