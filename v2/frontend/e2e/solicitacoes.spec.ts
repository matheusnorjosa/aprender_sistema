/**
 * Testes E2E de Solicitações
 *
 * Testa o fluxo de solicitações: criar, visualizar, aprovar/reprovar.
 * Autenticação é feita automaticamente via auth.setup.ts
 */

import { test, expect } from './fixtures';

test.describe('Fluxo de Solicitações', () => {
  test('1. Minhas Solicitações - Página carrega com tabela', async ({ page }) => {
    await page.goto('/solicitacoes/minhas');
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('2. Nova Solicitação - Página carrega', async ({ page }) => {
    await page.goto('/solicitacoes/nova');
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('3. Aprovações - Página carrega para a aprovadora', async ({ authedPage }) => {
    // O storageState padrão (coord_e2e) não aprova: a tela cairia em "Recurso indisponível" dentro
    // do <main>. super_geral tem o vínculo GERENTE na SUPERINTENDENCIA (aprova pela lotação).
    const page = await authedPage('super_geral');
    await page.goto('/aprovacoes');
    await expect(page.getByRole('main')).toBeVisible();
    await expect(page.getByText('Recurso indisponível')).toHaveCount(0);
  });

  test('4. Pré-Agenda - Página carrega', async ({ page }) => {
    await page.goto('/pre-agenda');
    await expect(page.getByRole('main')).toBeVisible();
  });
});

test.describe('Controle e Operações', () => {
  test('5. Painel de Controle carrega', async ({ page }) => {
    await page.goto('/controle');
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('7. Deslocamentos carrega', async ({ page }) => {
    await page.goto('/deslocamentos');
    await expect(page.getByRole('main')).toBeVisible();
  });
});
