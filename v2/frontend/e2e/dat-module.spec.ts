/**
 * Testes E2E do Módulo DAT
 *
 * Testa todas as páginas do módulo DAT (Departamento de Apoio Técnico).
 * Autenticação é feita automaticamente via auth.setup.ts
 */

import { test, expect } from '@playwright/test';

test.describe('Módulo DAT - Páginas Principais', () => {
  test('1. Admin DAT - Página inicial carrega', async ({ page }) => {
    await page.goto('/admin-dat');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('2. Importação carrega', async ({ page }) => {
    await page.goto('/importacao');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('3. Registros de Turmas carrega', async ({ page }) => {
    await page.goto('/dat-module/registros');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('4. Ações carrega', async ({ page }) => {
    await page.goto('/dat-module/acoes');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('5. Compras carrega', async ({ page }) => {
    await page.goto('/dat-module/compras');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('6. Cadastros carrega', async ({ page }) => {
    await page.goto('/dat-module/cadastros');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('7. Formações carrega', async ({ page }) => {
    await page.goto('/dat-module/formacoes');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('8. Plano Anual carrega', async ({ page }) => {
    await page.goto('/dat-module/plano-formacoes');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('9. Coordenadores carrega', async ({ page }) => {
    await page.goto('/dat-module/coordenadores');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });
});

test.describe('Admin DAT - Subpáginas', () => {
  test('10. Usuários carrega', async ({ page }) => {
    await page.goto('/admin-dat/usuarios');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('11. Municípios carrega', async ({ page }) => {
    await page.goto('/admin-dat/municipios');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('12. Projetos carrega', async ({ page }) => {
    await page.goto('/admin-dat/projetos');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('13. Grupos carrega', async ({ page }) => {
    await page.goto('/admin-dat/grupos');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('14. Configurações carrega', async ({ page }) => {
    await page.goto('/admin-dat/configuracoes');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });
});
