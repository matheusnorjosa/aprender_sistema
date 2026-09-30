/**
 * Sem rolagem horizontal (Programa C, C0): desktop, 1024 e 1280 px.
 *
 * Mesma medição de `sem-rolagem-horizontal.spec.ts` (leia o cabeçalho de lá), com uma
 * diferença: aqui a barra de rolagem vertical OCUPA largura, como no Chrome do Windows.
 * O Playwright abre o Chromium headless com `--hide-scrollbars`, e a barra some; a
 * 1024 e 1280 o usuário tem ~15 px a menos do que o teste via. Tirar o flag devolve a
 * barra clássica (15 px no Chromium; medido em 29/09/2026). É opção de lançamento do
 * navegador, por isso fica neste arquivo e não vale para 360 e 768, em que a barra do
 * celular é sobreposta.
 */
import { test, expect } from '@playwright/test';
import {
  entrar,
  medirAssentada,
  registrarMatriz,
  resumir,
  verificarTela,
  vigiarRede,
} from './sem-rolagem-horizontal.medicao';
import { ROTAS_MEDIDAS, type RotaMedida } from './sem-rolagem-horizontal.rotas';

test.use({
  serviceWorkers: 'block',
  launchOptions: { ignoreDefaultArgs: ['--hide-scrollbars'] },
});

function rota(path: string): RotaMedida {
  const encontrada = ROTAS_MEDIDAS.find((r) => r.path === path);
  if (!encontrada) throw new Error(`rota ${path} não está em ROTAS_MEDIDAS`);
  return encontrada;
}

test.describe('Sem rolagem horizontal (desktop): controles', () => {
  test('a barra de rolagem vertical ocupa largura, como no Windows', async ({ page, baseURL }) => {
    const rede = vigiarRede(page, baseURL);
    await entrar(page, 'coordenador', 1280);
    await page.goto('/politica-privacidade'); // página mais alta que a janela
    expect(await verificarTela(page, rota('/politica-privacidade'), rede)).toEqual([]);
    const barra = await page.evaluate(() => window.innerWidth - document.documentElement.clientWidth);
    expect(barra, 'sem a barra, 1024 e 1280 medem ~15 px a mais do que o usuário tem').toBeGreaterThanOrEqual(12);
  });

  test('controle positivo: /dashboards/equipe a 1024 rola DENTRO da tabela, não na página', async ({ page, baseURL }) => {
    // Prova o caso real do AntD numa tela que ainda está em PENDENTES. Até o C1 o alvo era
    // /dat/admin/usuarios, que o C1 consertou; o Dashboard da Equipe é do C7, o último PR do
    // Programa C. Quando ele sair de PENDENTES, este controle sai junto; o controle sintético
    // de sem-rolagem-horizontal.spec.ts continua valendo.
    const rede = vigiarRede(page, baseURL);
    await entrar(page, 'dat', 1024);
    await page.goto('/dashboards/equipe');
    expect(await verificarTela(page, rota('/dashboards/equipe'), rede)).toEqual([]);
    const medicao = await medirAssentada(page);
    expect(medicao.pagina, 'o critério da página sozinho não enxerga esta rolagem').toBe(0);
    expect(
      medicao.internos.some((m) => m.alvo.includes('ant-table')),
      `o verificador não viu a rolagem interna da tabela (${resumir(medicao)})`
    ).toBe(true);
  });
});

registrarMatriz([1024, 1280]);
