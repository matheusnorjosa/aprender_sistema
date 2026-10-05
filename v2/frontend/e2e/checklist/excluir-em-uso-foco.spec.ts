/**
 * Excluir registro em uso (C2b): para onde vai o foco no diálogo do 409 (WCAG 2.4.3).
 *
 * O "Sim, excluir" recebe 409; o diálogo "Não é possível excluir" abre com o foco no Cancelar e,
 * ao fechar (Cancelar, Desativar ou Entendi), o foco volta ao Excluir da linha. Ele só abre depois
 * que a confirmação termina de fechar: aberto de dentro do onOk dela, cada diálogo do rc-dialog
 * devolvia o foco ao que tinha guardado (o Excluir atrás da máscara, o "Sim, excluir" que já saiu
 * do DOM), e o foco acabava no contêiner do diálogo e, ao fechar, no body. O jsdom não roda essa
 * animação: por isso o teste é no Chromium.
 *
 * Roda no projeto `checklist`, com o backend semeado por `seed_frontend_contract_data`. O DELETE
 * e o PATCH são interceptados: nada é excluído nem desativado.
 */
import { test, expect, type Page, type Route } from '@playwright/test';
import { entrar } from './sem-rolagem-horizontal.medicao';
import { TEXTOS_DO_SEED } from './sem-rolagem-horizontal.rotas';

// O sw.js intermedeia as requisições e as esconde do page.route.
test.use({ serviceWorkers: 'block' });

const MUNICIPIO = TEXTOS_DO_SEED.municipio;
const MOTIVO = 'Este registro não pode ser excluído porque está em uso (Compras).';
const DO_MUNICIPIO = /\/api\/municipios\/\d+\/$/;
const DA_LISTA = /\/api\/municipios\/(\?|$)/;

const linha = (page: Page) => page.locator('.ant-table-row').filter({ hasText: MUNICIPIO });
const dialogo = (page: Page, titulo: string) => page.getByRole('dialog').filter({ hasText: titulo });

/** DELETE do município: 409 com o motivo. PATCH: 200. O resto vai ao backend. */
async function emUsoNoBackend(page: Page): Promise<void> {
  await page.route(DO_MUNICIPIO, async (rota: Route) => {
    const metodo = rota.request().method();
    if (metodo === 'DELETE') {
      await rota.fulfill({ status: 409, json: { detail: MOTIVO, code: 'CONFLICT' } });
    } else if (metodo === 'PATCH') {
      await rota.fulfill({ status: 200, json: { ...rota.request().postDataJSON(), id: 1 } });
    } else {
      await rota.continue();
    }
  });
}

/** O diálogo terminou de abrir: sem a classe da animação de zoom do AntD. */
async function assentado(page: Page, titulo: string): Promise<void> {
  await expect(dialogo(page, titulo)).toBeVisible();
  await expect(dialogo(page, titulo)).not.toHaveClass(/ant-zoom/);
}

/** Do Excluir da linha (`gatilho`, já focado) até o diálogo do 409, só pelo teclado. */
async function excluirPeloTeclado(page: Page): Promise<void> {
  await page.keyboard.press('Enter');
  await assentado(page, 'Confirmar exclusão');
  await expect(dialogo(page, 'Confirmar exclusão').getByRole('button', { name: 'Cancelar' })).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(dialogo(page, 'Confirmar exclusão').getByRole('button', { name: 'Sim, excluir' })).toBeFocused();
  await page.keyboard.press('Enter');

  // A confirmação some antes de o diálogo do 409 abrir (um diálogo por vez).
  await expect(dialogo(page, 'Confirmar exclusão')).toHaveCount(0);
  await assentado(page, 'Não é possível excluir');
  await expect(dialogo(page, 'Não é possível excluir')).toContainText(MOTIVO);
}

test.describe('Excluir em uso (409): o foco', () => {
  test('a 1280 px, o diálogo do 409 abre no Cancelar, e Cancelar e Desativar devolvem o foco ao Excluir da linha', async ({
    page,
  }) => {
    await entrar(page, 'dat', 1280);
    await emUsoNoBackend(page);
    await page.goto('/dat/admin/municipios');
    const excluir = linha(page).getByRole('button', { name: `Excluir: ${MUNICIPIO}` });
    await expect(excluir).toBeVisible();

    // Cancelar.
    await excluir.focus();
    await excluirPeloTeclado(page);
    const cancelar = dialogo(page, 'Não é possível excluir').getByRole('button', { name: 'Cancelar' });
    // Quem confirmou "Sim, excluir" com Enter não desativa sem ler.
    await expect(cancelar).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(dialogo(page, 'Não é possível excluir')).toHaveCount(0);
    await expect(excluir).toBeFocused();

    // Desativar: o PATCH, o aviso, a lista recarregada e o foco de volta ao Excluir.
    await excluirPeloTeclado(page);
    await expect(cancelar).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(dialogo(page, 'Não é possível excluir').getByRole('button', { name: 'Desativar' })).toBeFocused();
    const patch = page.waitForRequest((r) => r.method() === 'PATCH' && DO_MUNICIPIO.test(new URL(r.url()).pathname));
    const recarga = page.waitForResponse((r) => r.request().method() === 'GET' && DA_LISTA.test(r.url()));
    await page.keyboard.press('Enter');
    expect((await patch).postDataJSON()).toEqual({ ativo: false });
    await recarga;
    await expect(page.getByText('Município desativado')).toBeVisible();
    await expect(dialogo(page, 'Não é possível excluir')).toHaveCount(0);
    await expect(page.locator('.ant-table .ant-spin-blur')).toHaveCount(0);
    await expect(excluir).toBeFocused();
  });

  test('a 1280 px, registro já inativo: "Entendi" tem o foco e o devolve ao Excluir da linha', async ({ page }) => {
    await entrar(page, 'dat', 1280);
    await emUsoNoBackend(page);
    // A lista mostra o município do seed como inativo: o 409 só tem o motivo, sem Desativar.
    await page.route(DA_LISTA, async (rota) => {
      const resposta = await rota.fetch();
      const lista = (await resposta.json()) as { results: { nome: string; ativo: boolean }[] };
      for (const m of lista.results) if (m.nome.startsWith(MUNICIPIO)) m.ativo = false;
      await rota.fulfill({ response: resposta, json: lista });
    });
    await page.goto('/dat/admin/municipios');
    const excluir = linha(page).getByRole('button', { name: `Excluir: ${MUNICIPIO}` });
    await expect(linha(page)).toContainText('Inativo');

    await excluir.focus();
    await excluirPeloTeclado(page);
    await expect(dialogo(page, 'Não é possível excluir').getByRole('button', { name: 'Desativar' })).toHaveCount(0);
    await expect(dialogo(page, 'Não é possível excluir').getByRole('button', { name: 'Entendi' })).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(dialogo(page, 'Não é possível excluir')).toHaveCount(0);
    await expect(excluir).toBeFocused();
  });

  test('a 360 px, pelo "Mais ações": o Cancelar do 409 devolve o foco ao "Mais ações" da linha', async ({ page }) => {
    await entrar(page, 'dat', 360);
    await emUsoNoBackend(page);
    await page.goto('/dat/admin/municipios');
    const maisAcoes = linha(page).getByRole('button', { name: /^Mais ações: / });
    await expect(maisAcoes).toBeVisible();

    await maisAcoes.focus();
    await page.keyboard.press('Enter');
    const menu = page.getByRole('menu');
    await expect(menu.getByRole('menuitem').first()).toBeFocused();
    await page.keyboard.press('ArrowDown');
    await expect(menu.getByRole('menuitem', { name: 'Excluir', exact: true })).toBeFocused();
    await excluirPeloTeclado(page);
    await expect(dialogo(page, 'Não é possível excluir').getByRole('button', { name: 'Cancelar' })).toBeFocused();
    await page.keyboard.press('Escape');
    await expect(dialogo(page, 'Não é possível excluir')).toHaveCount(0);
    await expect(maisAcoes).toBeFocused();
  });
});
