/**
 * Menu lateral pelo teclado (Programa C, C1): o Enter num link navega em toda largura.
 *
 * Abaixo de 1280 px a navegação abre POR CIMA do conteúdo (sobreposta < 992 px; recolhida
 * de 992 a 1279 px). O rc-menu chama o `onClick` do Menu já no keydown do Enter; se a
 * sidebar fechasse ali, o foco voltaria ao ☰ antes da ação padrão do <a>, o link não
 * navegaria e o keypress reabriria o menu pelo ☰. O jsdom não reproduz essa ordem de
 * eventos: por isso o teste é no Chromium.
 *
 * Com a navegação aberta, o ☰ fica inerte: o botão "Fechar menu", dentro dela, é a saída
 * para quem usa leitor de tela no toque (sem Esc).
 *
 * Roda no projeto `checklist` (job "[required] checklist tests" do frontend-ci), com o
 * backend semeado por `seed_frontend_contract_data`.
 */
import { test, expect, type Page } from '@playwright/test';
import { entrar } from './sem-rolagem-horizontal.medicao';

/** O ☰ por CSS: aberto o menu, ele fica inerte e sai da árvore de acessibilidade. */
const botaoMenu = (page: Page) => page.locator('.mobile-menu-toggle');
const navegacao = (page: Page) => page.getByRole('navigation', { name: 'Navegacao principal' });

async function abrirPeloTeclado(page: Page, largura: number): Promise<void> {
  await entrar(page, 'coordenador', largura);
  await page.goto('/home');
  await expect(botaoMenu(page)).toBeVisible();
  await botaoMenu(page).focus();
  await page.keyboard.press('Enter');
  await expect(botaoMenu(page)).toHaveAttribute('aria-expanded', 'true');
  await expect(navegacao(page).getByRole('link', { name: 'Página Inicial' })).toBeFocused();
}

for (const largura of [360, 1024]) {
  test.describe(`Menu lateral a ${largura} px (aberto por cima do conteúdo)`, () => {
    test('Enter num link navega e fecha o menu', async ({ page }) => {
      await abrirPeloTeclado(page, largura);

      await page.keyboard.press('ArrowDown');
      await expect(navegacao(page).getByRole('link', { name: 'Meus Eventos' })).toBeFocused();
      await page.keyboard.press('Enter');

      await expect(page).toHaveURL(/\/solicitacoes\/meus-eventos$/);
      await expect(botaoMenu(page)).toHaveAttribute('aria-expanded', 'false');
      await expect(page.locator('.mobile-sidebar-overlay')).toHaveCount(0);
    });

    test('"Fechar menu", dentro da navegação, fecha e devolve o foco ao ☰', async ({ page }) => {
      await abrirPeloTeclado(page, largura);

      const fechar = navegacao(page).getByRole('button', { name: 'Fechar menu' });
      await expect(fechar).toBeVisible();
      expect(await fechar.evaluate((el) => el.closest('[inert]') === null)).toBe(true);
      await fechar.press('Enter');

      await expect(botaoMenu(page)).toHaveAttribute('aria-expanded', 'false');
      await expect(botaoMenu(page)).toBeFocused();
      await expect(page).toHaveURL(/\/home$/);
    });
  });
}

test('a 1280 px (menu sempre aberto) o Enter num link navega', async ({ page }) => {
  await entrar(page, 'coordenador', 1280);
  await page.goto('/home');
  const inicio = navegacao(page).getByRole('link', { name: 'Página Inicial' });
  await expect(inicio).toBeVisible();
  await expect(botaoMenu(page)).toBeHidden();
  await expect(navegacao(page).getByRole('button', { name: 'Fechar menu' })).toHaveCount(0);

  await inicio.focus();
  await page.keyboard.press('ArrowDown');
  await expect(navegacao(page).getByRole('link', { name: 'Meus Eventos' })).toBeFocused();
  await page.keyboard.press('Enter');

  await expect(page).toHaveURL(/\/solicitacoes\/meus-eventos$/);
});
