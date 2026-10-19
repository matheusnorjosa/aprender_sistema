/**
 * Testes E2E do Módulo DAT
 *
 * Smoke de shell: confere só que o <main> aparece nas rotas do módulo DAT
 * (Departamento de Apoio Técnico).
 * Autenticação é feita automaticamente via auth.setup.ts, com o storageState padrão
 * (coord_e2e: papel COORDENADOR na GERENCIA E2E, perfil PADRAO, sem
 * manage_admin_registries nem as demais policies dessas rotas). Nas rotas /dat/* o
 * RequirePolicy mostra "Recurso indisponível" dentro do <main>, e o teste passa sem DAT
 * nem superusuário. Abrir de fato exige authedPage('dat_e2e') (e2e/fixtures/roles.ts;
 * pacote ADMIN_OPERACIONAL) e conferir a ausência de "Recurso indisponível"; a importação
 * (/dat/importacao → /dat/importacoes) e /dat/admin/equipe-gerencia só abrem para o
 * superusuário (`podeImportarPelaTela` em AppRoutes.tsx), e /dat/etl-reports não tem rota.
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
