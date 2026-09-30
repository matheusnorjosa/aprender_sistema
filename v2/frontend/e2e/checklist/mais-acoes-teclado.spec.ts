/**
 * "Mais ações" pelo teclado (Programa C, C1): escolher uma ação com Enter abre o modal dela e
 * NÃO reabre o menu.
 *
 * Abaixo de 576 px (`compacto`) as ações da linha de Usuários ficam todas no "Mais ações". O
 * rc-menu chama o `onClick` do item já no keydown do Enter, e o foco volta ao botão ali mesmo
 * (para o modal devolvê-lo ao botão quando fechar). Sem cancelar o keydown, o keypress cai no
 * botão, o Chromium gera o clique e o menu reabre por cima do modal. O jsdom não gera esse
 * keypress: por isso o teste é no Chromium.
 *
 * Roda no projeto `checklist` (job "[required] checklist tests" do frontend-ci), com o backend
 * semeado por `seed_frontend_contract_data`. Só abre e cancela: nada é salvo nem excluído.
 */
import { test, expect, type Page } from '@playwright/test';
import { entrar } from './sem-rolagem-horizontal.medicao';
import { TEXTOS_DO_SEED } from './sem-rolagem-horizontal.rotas';

const PESSOA = TEXTOS_DO_SEED.pessoa;

const linhaDaPessoa = (page: Page) => page.locator('.ant-table-row').filter({ hasText: PESSOA });
const maisAcoes = (page: Page) => linhaDaPessoa(page).getByRole('button', { name: /^Mais ações: / });

for (const { acao, setas, dialogo } of [
  { acao: 'Redefinir senha', setas: 1, dialogo: 'Redefinir senha —' },
  { acao: 'Excluir', setas: 2, dialogo: 'Confirmar exclusão' },
]) {
  test(`a 360 px, "${acao}" pelo Enter abre o modal sem reabrir o menu, e o Esc devolve o foco ao botão`, async ({
    page,
  }) => {
    await entrar(page, 'dat', 360);
    await page.goto('/dat/admin/usuarios');
    await expect(maisAcoes(page)).toBeVisible();

    // Tab do nome (que abre o detalhe) até o "Mais ações" da mesma linha.
    await linhaDaPessoa(page).getByRole('button', { name: `Ver detalhes de ${PESSOA}` }).focus();
    await page.keyboard.press('Tab');
    await expect(maisAcoes(page)).toBeFocused();

    await page.keyboard.press('Enter');
    const menu = page.getByRole('menu');
    await expect(menu).toBeVisible();
    await expect(maisAcoes(page)).toHaveAttribute('aria-expanded', 'true');
    for (let i = 0; i < setas; i++) await page.keyboard.press('ArrowDown');
    await expect(menu.getByRole('menuitem', { name: acao })).toBeFocused();
    await page.keyboard.press('Enter');

    await expect(page.getByRole('dialog').filter({ hasText: dialogo })).toBeVisible();
    await expect(menu).toBeHidden();
    await expect(maisAcoes(page)).toHaveAttribute('aria-expanded', 'false');

    // O rc-dialog só leva o foco para dentro do modal no fim da animação de abertura.
    await expect
      .poll(() => page.evaluate(() => document.activeElement?.closest('[role="dialog"]') != null))
      .toBe(true);
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(maisAcoes(page)).toBeFocused();
    await expect(maisAcoes(page)).toHaveAttribute('aria-expanded', 'false');
    await expect(menu).toBeHidden();
  });
}
