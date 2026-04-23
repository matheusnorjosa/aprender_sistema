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

  // Este teste USA a sessão autenticada do setup
  test.describe('Logout', () => {
    test('4. Logout funciona corretamente', async ({ page }) => {
      // Spec legacy pré-programa de jornadas. Mesmo problema do
      // navigation.spec — sidebar às vezes não renderiza dentro do timeout
      // quando carrega /home direto. Marcado test.fail() até migração
      // completa dos specs legacy (backlog).
      test.fail(
        true,
        'Spec legacy instável — sidebar não renderiza dentro do timeout em ~20% das rodadas. Backlog.'
      );
      // Já está logado via setup - ir para home
      await page.goto('/home');

      // Verificar que está logado
      await expect(
        page.getByRole('navigation', { name: 'Navegacao principal' })
      ).toBeVisible({ timeout: 5000 });

      // Clicar no botão de logout (selector explícito para evitar ambiguidades)
      await page.click('[data-testid="app-logout-button"]');

      // Deve voltar para tela de login (h1, não h2)
      await expect(page.locator('h1:has-text("Login")')).toBeVisible({ timeout: 10000 });
    });
  });
});
