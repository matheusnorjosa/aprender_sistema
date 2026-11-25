/**
 * Integra (DADOS SIMULADOS): sem rolagem horizontal e sem violação crítica de acessibilidade nas
 * telas filhas.
 *
 * O `ROTAS_MEDIDAS` só alcança os `path` do AppRoutes, e lá a Integra é um único `/integra/*`
 * (a página dos cartões). As telas abaixo são rotas filhas (`IntegraRoutes`, `ica/IcaRoutes`,
 * `semaforo/SemaforoRoutes`, `deslocamento/DeslocamentoRoutes`) e são medidas aqui, com o mesmo verificador do spec de rolagem (`medirAssentada`: página,
 * rolagem interna e corte sem reticências) e o axe com as tags WCAG 2.1 AA.
 *
 * Regra do dono: nenhuma rolagem horizontal em nenhuma largura; 400 px é a largura de teste da
 * Integra (celular comum), ao lado das 360 e 768 do spec de rolagem.
 *
 * Rodar local (backend do slot já semeado com `seed_frontend_contract_data`):
 *   SKIP_WEBSERVER=1 BASE_URL=http://127.0.0.1:<porta do vite> \
 *     npx playwright test --project=checklist e2e/checklist/integra-telas
 */
import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

import { entrar, medirAssentada, resumir, temProblema, verificarTela, vigiarRede } from './sem-rolagem-horizontal.medicao';

// O sw.js (modo offline) esconde as requisições dos eventos de rede que `verificarTela` lê.
test.use({ serviceWorkers: 'block' });

const LARGURAS_INTEGRA = [360, 400, 768] as const;

/** Ids do gerador com a semente fixa (pessoas fictícias): o 101 tem carteira cheia; o 117 está sem municípios. */
const COORDENADORA_MAIS_CARREGADA = '101';
const COORDENADORA_SEM_MUNICIPIOS = '117';
/** `HISTORIAS_SEMAFORO.vermelho_prazo_hoje`: a ficha com mais linhas. O id é conferido em `semaforo/__tests__/dados.test.ts`. */
const MUNICIPIO_VERMELHO = '5';

interface TelaIntegra {
  path: string;
  /** O h1 da tela. */
  marco: string;
  /** Monta o estado mais largo da tela antes de medir. */
  preparar?: (page: Page) => Promise<void>;
}

/**
 * Simulador com um movimento: aparece "Antes e depois", a parte mais larga da tela. Marca o primeiro município da
 * carteira, sem depender do nome: a lista de municípios segue o relatório de deslocamento e pode mudar.
 */
async function montarSimulacao(page: Page): Promise<void> {
  const main = page.locator('main#main');
  await main.getByLabel('Coordenador de origem').selectOption(COORDENADORA_MAIS_CARREGADA);
  await main.getByRole('group', { name: 'Municípios para mover' }).getByRole('checkbox').first().check();
  await main.getByLabel('Coordenador de destino').selectOption(COORDENADORA_SEM_MUNICIPIOS);
  await main.getByRole('button', { name: 'Adicionar à simulação' }).click();
  await expect(main.getByRole('heading', { level: 2, name: 'Antes e depois' })).toBeVisible();
}

const TELAS: readonly TelaIntegra[] = [
  { path: '/integra/ica', marco: 'Painel do ICA' },
  { path: `/integra/ica/coordenador/${COORDENADORA_MAIS_CARREGADA}`, marco: 'Ficha do coordenador' },
  { path: '/integra/ica/simulador', marco: 'Simulador de remanejamento', preparar: montarSimulacao },
  { path: '/integra/ica/pesos', marco: 'Pesos e faixas' },
  { path: '/integra/ica/gerencias', marco: 'Visão por gerência' },
  { path: '/integra/ica/comparativo', marco: 'Comparativo de pesos' },
  { path: '/integra/ica/historico', marco: 'Histórico semestral' },
  { path: '/integra/ica/alertas', marco: 'Alertas' },
  { path: '/integra/para-validar', marco: 'Para validar no dia 7' },
  { path: '/integra/semaforo', marco: 'Semáforo de Risco Municipal' },
  { path: '/integra/semaforo/comite', marco: 'Comitê de Satisfação' },
  { path: `/integra/semaforo/municipio/${MUNICIPIO_VERMELHO}`, marco: 'Ficha do município' },
  { path: '/integra/semaforo/gestora', marco: 'Painel da gestora de referência' },
  { path: '/integra/semaforo/pesquisa', marco: 'Pesquisa do articulador' },
  { path: '/integra/semaforo/lider', marco: 'Indicadores da Líder do NFP' },
  { path: '/integra/semaforo/relatorio-mensal', marco: 'Relatório mensal e formulários' },
  { path: '/integra/deslocamento', marco: 'Tempos de deslocamento' },
  { path: '/integra/deslocamento/regras', marco: 'Como o tempo é calculado' },
  { path: '/integra/deslocamento/coordenadores', marco: 'Soma por coordenador' },
];

test.describe('Integra: foco visível nos links e aviso em toda folha impressa', () => {
  test('link de texto (nome no Painel) mostra o contorno de foco ao chegar por Tab', async ({ page, baseURL }) => {
    const rede = vigiarRede(page, baseURL);
    await entrar(page, 'superusuario', 1280);
    await page.goto('/integra/ica');
    expect(await verificarTela(page, { marco: 'Painel do ICA' }, rede)).toEqual([]);
    // O reset do antd zera o outline de `a:focus` dentro do Layout (`:where(.css-…) a:focus`).
    const alvo = page.locator('main#main ol[aria-label="ICA por coordenador"] a').first();
    await alvo.scrollIntoViewIfNeeded();
    let focado = false;
    for (let i = 0; i < 80 && !focado; i += 1) {
      await page.keyboard.press('Tab');
      focado = await alvo.evaluate((el) => el === document.activeElement);
    }
    expect(focado, 'o Tab não chegou ao primeiro nome do Painel').toBe(true);
    const contorno = await alvo.evaluate((el) => {
      const s = getComputedStyle(el);
      return { estilo: s.outlineStyle, largura: s.outlineWidth };
    });
    expect(contorno.estilo).not.toBe('none');
    expect(contorno.largura).not.toBe('0px');
  });

  test('link no meio do texto é sublinhado; os botões do menu não (WCAG 1.4.1)', async ({ page, baseURL }) => {
    const rede = vigiarRede(page, baseURL);
    await entrar(page, 'superusuario', 1280);
    await page.goto('/integra/semaforo/gestora');
    expect(await verificarTela(page, { marco: 'Painel da gestora de referência' }, rede)).toEqual([]);
    const main = page.locator('main#main');
    // O preflight do Tailwind (`a { color: inherit; text-decoration: inherit }`) vence o reset do antd: sem regra
    // própria, o link na frase tem a cor e a decoração do texto em volta e some no meio dele.
    const naFrase = main.getByRole('region', { name: 'Vence hoje' }).getByRole('listitem').first().getByRole('link');
    await expect(naFrase).toBeVisible();
    expect(await naFrase.evaluate((el) => getComputedStyle(el).textDecorationLine)).toBe('underline');
    const doMenu = main.getByRole('navigation', { name: 'Telas do Semáforo' }).getByRole('link').first();
    expect(await doMenu.evaluate((el) => getComputedStyle(el).textDecorationLine)).toBe('none');
  });

  test('impressão: o aviso DADOS SIMULADOS vai na margem de cima de toda folha', async ({ page, baseURL }) => {
    const rede = vigiarRede(page, baseURL);
    await entrar(page, 'superusuario', 1280);
    await page.goto('/integra/ica');
    expect(await verificarTela(page, { marco: 'Painel do ICA' }, rede)).toEqual([]);
    await page.emulateMedia({ media: 'print' });
    // A moldura usa a página com nome `integra`, e essa página tem o aviso na margem de cima: o
    // navegador repete a margem em cada folha (a faixa da tela sai só na primeira).
    const nomeDaPagina = await page.evaluate(() => getComputedStyle(document.body).getPropertyValue('page'));
    expect(nomeDaPagina).toBe('integra');
    const avisoNaMargem = await page.evaluate(() => {
      const regras = [...document.styleSheets].flatMap((folha) => {
        try {
          return [...folha.cssRules];
        } catch {
          return [];
        }
      });
      const todas = (lista: CSSRule[]): CSSRule[] =>
        lista.flatMap((r) => ('cssRules' in r ? [r, ...todas([...(r as CSSGroupingRule).cssRules])] : [r]));
      return todas(regras).some(
        (r) => r instanceof CSSPageRule && r.selectorText === 'integra' && /@top-\w+\s*\{[^}]*DADOS SIMULADOS/.test(r.cssText),
      );
    });
    expect(avisoNaMargem, 'falta a regra @page integra com o aviso na margem de cima').toBe(true);
  });

  test('impressão do Painel num notebook (1366 px): Gerência e Atuação no papel, sem "Expandir linha"', async ({ page, baseURL }) => {
    const rede = vigiarRede(page, baseURL);
    await entrar(page, 'superusuario', 1366);
    await page.goto('/integra/ica');
    expect(await verificarTela(page, { marco: 'Painel do ICA' }, rede)).toEqual([]);
    const main = page.locator('main#main');
    // Na tela, a 1366 px, a tabela manda Gerência e Atuação para a linha expandida.
    await expect(main.getByRole('button', { name: /^Expandir linha/ }).first()).toBeVisible();

    await page.emulateMedia({ media: 'print' });
    await expect(main.getByRole('table')).toBeHidden();
    const papel = main.getByRole('list', { name: 'Todos os componentes, por coordenador' });
    await expect(papel).toBeVisible();
    const primeiro = papel.getByRole('listitem').first();
    await expect(primeiro.getByRole('term').filter({ hasText: /^Gerência$/ })).toBeVisible();
    await expect(primeiro.getByRole('term').filter({ hasText: /^Atuação$/ })).toBeVisible();
    await expect(main.getByRole('button', { name: /^Expandir linha/ })).toHaveCount(0);
  });

  test('impressão de outra tabela (Ficha a 400 px): o botão "Expandir linha" e a coluna dele saem do papel', async ({ page, baseURL }) => {
    const rede = vigiarRede(page, baseURL);
    await entrar(page, 'superusuario', 400);
    await page.goto(`/integra/ica/coordenador/${COORDENADORA_MAIS_CARREGADA}`);
    expect(await verificarTela(page, { marco: 'Ficha do coordenador' }, rede)).toEqual([]);
    const main = page.locator('main#main');
    await expect(main.getByRole('button', { name: /^Expandir linha/ }).first()).toBeVisible();

    await page.emulateMedia({ media: 'print' });
    await expect(main.getByRole('button', { name: /^Expandir linha/ })).toHaveCount(0);
    const colunasDoBotao = await main.locator('.ant-table-row-expand-icon-cell, .ant-table-expand-icon-col').evaluateAll((els) =>
      els.filter((el) => getComputedStyle(el).display !== 'none').length,
    );
    expect(colunasDoBotao).toBe(0);
  });
});

test.describe('Integra: trocar de tela abre a nova no topo, com o foco no título', () => {
  test('nome no fim do Painel abre a Ficha no topo; "Voltar ao painel" também (400 px)', async ({ page, baseURL }) => {
    const rede = vigiarRede(page, baseURL);
    await entrar(page, 'superusuario', 400);
    await page.goto('/integra/ica');
    expect(await verificarTela(page, { marco: 'Painel do ICA' }, rede)).toEqual([]);
    const main = page.locator('main#main');
    const nomeNaTabela = main.getByRole('table').getByRole('link').last();
    await nomeNaTabela.scrollIntoViewIfNeeded();
    expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(1000);

    await nomeNaTabela.click();
    const ficha = main.getByRole('heading', { level: 1, name: 'Ficha do coordenador' });
    await expect(ficha).toBeFocused();
    expect(await page.evaluate(() => window.scrollY)).toBe(0);

    const voltar = main.getByRole('link', { name: 'Voltar ao painel' });
    await voltar.scrollIntoViewIfNeeded();
    expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
    await voltar.click();
    await expect(main.getByRole('heading', { level: 1, name: 'Painel do ICA' })).toBeFocused();
    expect(await page.evaluate(() => window.scrollY)).toBe(0);
  });
});

test.describe('Integra: a faixa presa no topo não cobre o destino de um link "#seção"', () => {
  for (const largura of [360, 1280]) {
    test(`índice do "Para validar" a ${largura}px: o título de destino fica abaixo da faixa`, async ({ page, baseURL }) => {
      const rede = vigiarRede(page, baseURL);
      await entrar(page, 'superusuario', largura);
      await page.goto('/integra/para-validar');
      expect(await verificarTela(page, { marco: 'Para validar no dia 7' }, rede)).toEqual([]);
      const main = page.locator('main#main');
      await main.getByRole('navigation', { name: 'Nesta página' }).getByRole('link', { name: 'De onde virá cada dado' }).click();
      const titulo = main.getByRole('heading', { level: 2, name: 'De onde virá cada dado' });
      await expect.poll(async () => page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
      const faixa = await main.getByRole('note').filter({ hasText: 'DADOS SIMULADOS' }).boundingBox();
      const destino = await titulo.boundingBox();
      expect(faixa).not.toBeNull();
      expect(destino).not.toBeNull();
      expect(destino!.y).toBeGreaterThanOrEqual(faixa!.y + faixa!.height);
    });
  }
});

test.describe('Integra: telas filhas sem rolagem horizontal e sem violação crítica (axe)', () => {
  for (const tela of TELAS) {
    for (const largura of LARGURAS_INTEGRA) {
      test(`${tela.path} a ${largura}px`, async ({ page, baseURL }) => {
        const rede = vigiarRede(page, baseURL);
        // A Integra só abre para superusuário, Diretoria e gerente da Superintendência; o seed só tem
        // o superusuário entre eles.
        await entrar(page, 'superusuario', largura);
        await page.goto(tela.path);
        expect(await verificarTela(page, { marco: tela.marco }, rede), `a tela ${tela.path} não ficou pronta`).toEqual([]);
        if (tela.preparar) await tela.preparar(page);

        const medicao = await medirAssentada(page);
        expect(temProblema(medicao), `[rolagem] ${tela.path} @ ${largura}px — ${resumir(medicao)}`).toBe(false);

        const axe = await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
          .exclude('.ant-spin-fullscreen')
          .exclude('.ant-spin-text')
          .analyze();
        const criticas = axe.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
        const relatorio = criticas
          .map((v) => `[${v.impact}] ${v.id}: ${v.help}\n  ${v.nodes.map((n) => n.target.join(' ')).join('\n  ')}`)
          .join('\n');
        expect(criticas, `violações críticas em ${tela.path} a ${largura}px:\n${relatorio}`).toHaveLength(0);
      });
    }
  }
});
