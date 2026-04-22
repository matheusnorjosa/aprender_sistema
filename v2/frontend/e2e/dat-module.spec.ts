/**
 * Testes E2E do Módulo DAT
 *
 * Testa todas as páginas do módulo DAT (Departamento de Apoio Técnico).
 * Autenticação é feita automaticamente via auth.setup.ts
 */

import { test, expect } from '@playwright/test';

test.describe('Módulo DAT - Páginas Principais', () => {
  test('1. Admin DAT - Página inicial carrega', async ({ page }) => {
    await page.goto('/dat/admin');
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('2. Importação carrega', async ({ page }) => {
    await page.goto('/dat/importacao');
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('3. Registros de Turmas carrega', async ({ page }) => {
    await page.goto('/dat/registros');
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('4. Cadastros carrega', async ({ page }) => {
    await page.goto('/dat/cadastros');
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('5. Coordenadores carrega', async ({ page }) => {
    await page.goto('/dat/coordenadores');
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('6. Relatórios ETL carrega', async ({ page }) => {
    await page.goto('/dat/etl-reports');
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('7. Importar Coleções carrega', async ({ page }) => {
    await page.goto('/dat/admin/colecoes');
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('8. Importar Equipe-Gêrencia carrega', async ({ page }) => {
    await page.goto('/dat/admin/equipe-gerencia');
    await expect(page.getByRole('main')).toBeVisible();
  });
});

test.describe('Admin DAT - Subpáginas', () => {
  test('9. Usuários carrega', async ({ page }) => {
    await page.goto('/dat/admin/usuarios');
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('10. Municípios carrega', async ({ page }) => {
    await page.goto('/dat/admin/municipios');
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('11. Projetos carrega', async ({ page }) => {
    await page.goto('/dat/admin/projetos');
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('12. Grupos carrega', async ({ page }) => {
    await page.goto('/dat/admin/grupos');
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('13. Configurações carrega', async ({ page }) => {
    await page.goto('/dat/admin/configuracoes');
    await expect(page.getByRole('main')).toBeVisible();
  });
});
