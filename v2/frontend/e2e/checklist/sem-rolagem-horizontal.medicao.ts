/**
 * Medição e pré-condições do spec "sem rolagem horizontal" (Programa C, C0).
 *
 * Compartilhado pelos dois specs: `sem-rolagem-horizontal.spec.ts` (360 e 768 px,
 * barra de rolagem sobreposta, como no celular) e `sem-rolagem-horizontal.desktop.spec.ts`
 * (1024 e 1280 px, com a barra de rolagem clássica ocupando largura, como no Windows).
 * Não é spec (o nome não termina em .spec.ts): só exporta funções.
 */
import { test, expect, type Page } from '@playwright/test';
import {
  PENDENTES,
  PENDENTES_SO_LINUX,
  PERFIS,
  ROTAS_MEDIDAS,
  SENHA_PERFIS,
  TELA_LOGIN,
  chaveDe,
  type DadosDaTela,
  type Largura,
  type Perfil,
  type RotaMedida,
} from './sem-rolagem-horizontal.rotas';

export interface Medicao {
  /** documentElement.scrollWidth - clientWidth (> 0 = a página rola). */
  pagina: number;
  /** Elementos com overflow-x auto/scroll cujo conteúdo excede a caixa (rolagem interna). */
  internos: { alvo: string; excesso: number }[];
  /** Elementos com overflow-x hidden/clip que cortam conteúdo sem reticências. */
  cortados: { alvo: string; excesso: number }[];
}

/**
 * Internos do AntD e do Leaflet que escondem conteúdo de propósito (medidos em 29/09/2026):
 * setas do InputNumber, rótulos do Switch, preenchimento do Progress, linha conectora do
 * Steps, abas com menu "mais" e os tiles do mapa. Desde o C1 (30/09/2026): os itens da
 * sidebar recolhida (992 a 1279 px, só ícones; o rótulo aparece no Tooltip e no flyout) e o
 * texto só para leitor de tela (`sr-only`, cortado por definição). Lista curta: entrada nova
 * precisa de motivo.
 */
export const CORTE_PERMITIDO = [
  '.ant-input-number-handler',
  '.ant-switch-inner',
  '.ant-progress-bg',
  '.ant-steps-item',
  '.ant-tabs-nav-wrap',
  '.leaflet-container',
  '.ant-menu-inline-collapsed .ant-menu-item',
  '.ant-menu-inline-collapsed .ant-menu-submenu-title',
  '.sr-only',
] as const;

/**
 * Três critérios. O primeiro sozinho é cego à tabela do AntD: com `scroll.x` a rolagem
 * fica DENTRO de `.ant-table-content` e a página mede 0 (os controles provam isso).
 * 1. a página: `documentElement.scrollWidth - clientWidth > 0`;
 * 2. rolagem interna: `overflow-x` auto/scroll e `scrollWidth - clientWidth > 1`;
 * 3. corte: `overflow-x` hidden/clip, `scrollWidth - clientWidth > 1` e sem
 *    `text-overflow: ellipsis`. Ficam de fora campos de formulário (o valor rola dentro
 *    do campo), caixas sem largura ou invisíveis, `aria-hidden` e CORTE_PERMITIDO.
 * A folga de 1 px cobre arredondamento de subpixel. `permitido` só muda nos controles.
 */
export async function medirRolagemHorizontal(
  page: Page,
  permitido: readonly string[] = CORTE_PERMITIDO
): Promise<Medicao> {
  return page.evaluate((permitido) => {
    const descrever = (el: Element): string => {
      const id = el.id ? `#${el.id}` : '';
      const classes = Array.from(el.classList).slice(0, 3).map((c) => `.${c}`).join('');
      return `${el.tagName.toLowerCase()}${id}${classes}`;
    };
    const seletorPermitido = permitido.join(', ');
    const internos: Medicao['internos'] = [];
    const cortados: Medicao['cortados'] = [];
    for (const el of Array.from(document.body.querySelectorAll('*'))) {
      const estilo = getComputedStyle(el);
      const excesso = el.scrollWidth - el.clientWidth;
      if (excesso <= 1) continue;
      if (estilo.overflowX === 'auto' || estilo.overflowX === 'scroll') {
        internos.push({ alvo: descrever(el), excesso });
        continue;
      }
      if (estilo.overflowX !== 'hidden' && estilo.overflowX !== 'clip') continue;
      if (estilo.textOverflow === 'ellipsis' || estilo.visibility === 'hidden' || el.clientWidth < 1) continue;
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName)) continue;
      if (el.closest('[aria-hidden="true"]') || (seletorPermitido && el.matches(seletorPermitido))) continue;
      cortados.push({ alvo: descrever(el), excesso });
    }
    const de = document.documentElement;
    return { pagina: de.scrollWidth - de.clientWidth, internos, cortados };
  }, permitido);
}

export function temProblema(medicao: Medicao): boolean {
  return medicao.pagina > 0 || medicao.internos.length > 0 || medicao.cortados.length > 0;
}

export function resumir(medicao: Medicao): string {
  const lista = (itens: { alvo: string; excesso: number }[]) =>
    itens.map((m) => `${m.alvo} +${m.excesso}px`).join('; ') || 'nenhum';
  return `página +${medicao.pagina}px; rolagem interna: ${lista(medicao.internos)}; corte: ${lista(medicao.cortados)}`;
}

/**
 * Requisições da MESMA ORIGEM do app (API e chunks da página) que falharam: status >= 400
 * ou `requestfailed`. Tabela vazia por erro não estoura largura: sem esta guarda, o erro
 * passaria por "sem rolagem". Hoje nenhuma rota tem falha esperada (medido em 29/09/2026).
 * Não conta: cancelamento deliberado (`net::ERR_ABORTED`, latest-wins/AbortController) e
 * terceiros (tiles do mapa).
 */
export function vigiarRede(page: Page, baseURL: string | undefined): string[] {
  const origem = new URL(baseURL ?? 'http://localhost').origin;
  const falhas: string[] = [];
  const mesmaOrigem = (url: string) => new URL(url).origin === origem;
  page.on('response', (resposta) => {
    if (mesmaOrigem(resposta.url()) && resposta.status() >= 400) {
      falhas.push(`${resposta.status()} ${new URL(resposta.url()).pathname}`);
    }
  });
  page.on('requestfailed', (requisicao) => {
    const erro = requisicao.failure()?.errorText ?? '?';
    if (mesmaOrigem(requisicao.url()) && erro !== 'net::ERR_ABORTED') {
      falhas.push(`FALHOU ${new URL(requisicao.url()).pathname} (${erro})`);
    }
  });
  return falhas;
}

export async function entrar(page: Page, perfil: Perfil, largura: number): Promise<void> {
  await page.setViewportSize({ width: largura, height: 800 });
  const csrf = await page.request.get('/api/csrf/');
  expect(csrf.ok(), `[rolagem][login] csrf falhou (${perfil})`).toBeTruthy();
  const { csrfToken } = (await csrf.json()) as { csrfToken?: string };
  const login = await page.request.post('/api/auth/login/', {
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken ?? '' },
    data: { username: PERFIS[perfil], password: SENHA_PERFIS },
  });
  expect(login.ok(), `[rolagem][login] login falhou (${perfil} = ${PERFIS[perfil]})`).toBeTruthy();
}

/** O que a tela tem de mostrar para a medição valer. */
export interface AlvoDaTela {
  /** Título próprio da tela, ou TELA_LOGIN. */
  marco: string;
  dados?: DadosDaTela;
  /** Requisições com falha que são esperadas nesta tela (regex sobre "status caminho"). */
  redeEsperada?: readonly RegExp[];
}

const TITULOS = 'h1, h2, h3, h4, h5, [role="heading"], .ant-card-head-title';
const ERRO_NA_TELA = '.ant-result-error, .ant-result-warning, .ant-alert-error';

/**
 * Pré-condições da medição. Devolve a lista de problemas (vazia = a tela está pronta),
 * para os controles provarem que cada camada, sozinha, reprova o seu caso:
 * - marco: o título próprio da tela aparece em `main` (a casca sozinha não basta);
 * - casca autenticada: o header com o botão "Sair" (a tela de login também tem `main`);
 * - nenhum erro em `main`: Result de erro ou aviso, Alert de erro, "Algo deu errado"
 *   (ErrorBoundary) e "Recurso indisponível" (RequirePolicy);
 * - dados: o texto do seed dentro da linha de tabela ou do contêiner declarado (em `main`, ou
 *   na página com `foraDeMain`);
 * - rede: nenhuma requisição da mesma origem com falha, fora as esperadas.
 */
export async function verificarTela(
  page: Page,
  alvo: AlvoDaTela,
  rede: readonly string[],
  espera = 15_000
): Promise<string[]> {
  const problemas: string[] = [];
  const main = page.locator('main#main');
  const login = alvo.marco === TELA_LOGIN;
  const marco = login ? page.locator('#login-title') : main.locator(TITULOS).filter({ hasText: alvo.marco }).first();
  try {
    await marco.waitFor({ state: 'visible', timeout: espera });
  } catch {
    problemas.push(`marco "${alvo.marco}" não apareceu em main`);
  }
  try {
    await esperarAssentar(page, espera);
  } catch {
    problemas.push('a página não assentou (rede ou spinner)');
  }
  const sair = page.locator('header[aria-label="Perfil do usuario e acoes"]').getByRole('button', { name: 'Sair' });
  if (!login && !(await sair.isVisible())) problemas.push('casca autenticada ausente (header com "Sair")');
  const erros = await main.locator(ERRO_NA_TELA).count();
  if (erros > 0) problemas.push(`erro na tela: ${erros} Result/Alert de erro em main`);
  for (const texto of ['Algo deu errado', 'Recurso indisponível']) {
    if ((await main.getByText(texto).count()) > 0) problemas.push(`erro na tela: "${texto}"`);
  }
  if (alvo.dados) {
    const onde = alvo.dados.foraDeMain ? page.locator('body') : main;
    const linha = onde.locator(alvo.dados.em).filter({ hasText: alvo.dados.texto }).first();
    try {
      await linha.waitFor({ state: 'visible', timeout: Math.min(espera, 5_000) });
    } catch {
      problemas.push(`dados: nenhum "${alvo.dados.em}" com "${alvo.dados.texto}" visível`);
    }
  }
  const esperadas = alvo.redeEsperada ?? [];
  for (const falha of rede) {
    if (!esperadas.some((e) => e.test(falha))) problemas.push(`requisição com falha: ${falha}`);
  }
  return problemas;
}

export async function garantirTela(page: Page, alvo: AlvoDaTela, rede: readonly string[]): Promise<void> {
  expect(await verificarTela(page, alvo, rede), `[rolagem] a tela não ficou pronta para medir (${alvo.marco})`).toEqual([]);
}

/** Espera a página assentar: rede parada e nenhum spinner do AntD girando. */
export async function esperarAssentar(page: Page, espera = 15_000): Promise<void> {
  await page.waitForLoadState('networkidle', { timeout: espera });
  await expect(page.locator('.ant-spin-spinning')).toHaveCount(0, { timeout: espera });
}

/**
 * Mede até duas leituras seguidas darem o mesmo resultado, com a rede parada entre
 * elas. Sob carga, o `networkidle` pode cair entre duas levas de requisições de uma
 * tela e a primeira leitura pegaria um estado de transição.
 */
export async function medirAssentada(page: Page): Promise<Medicao> {
  let anterior = await medirRolagemHorizontal(page);
  for (let tentativa = 0; tentativa < 5; tentativa += 1) {
    await page.waitForTimeout(500); // intervalo de amostragem, não espera por evento
    await esperarAssentar(page);
    const atual = await medirRolagemHorizontal(page);
    if (JSON.stringify(atual) === JSON.stringify(anterior)) return atual;
    anterior = atual;
  }
  throw new Error(`[rolagem] o layout não estabilizou em 5 leituras (${resumir(anterior)})`);
}

/**
 * Troca `:id` pelo id real, buscado pela API com a sessão do perfil: a pendente
 * do próprio coordenador (pendente e sem GCal é editável), semeada com texto longo.
 */
async function resolverUrl(page: Page, rota: RotaMedida): Promise<string> {
  if (rota.parametro !== 'solicitacaoEditavel') return rota.path;
  const resposta = await page.request.get('/api/solicitacoes/?mine=true&status=pendente&page_size=1');
  expect(resposta.ok(), '[rolagem] não listou solicitações para abrir a edição').toBeTruthy();
  const corpo = (await resposta.json()) as { results?: { id: number }[] };
  const id = corpo.results?.[0]?.id;
  expect(id, '[rolagem] o seed não deixou solicitação editável para o perfil').toBeDefined();
  return rota.path.replace(':id', String(id));
}

/**
 * A referência da trava é o Chromium Linux da CI. PENDENTES_SO_LINUX (diferença de fonte)
 * só vale lá; no Windows essas telas não rolam e não viram "falha esperada".
 */
const NA_REFERENCIA = process.platform === 'linux';

function ehPendente(chave: string, largura: number): boolean {
  const listas = NA_REFERENCIA ? [PENDENTES, PENDENTES_SO_LINUX] : [PENDENTES];
  return listas.some((lista) => (lista[chave] ?? []).some((l) => l === largura));
}

/**
 * Mede e decide. As pré-condições (tela pronta, medição estável, rede sem falha, inclusive
 * durante a medição) vêm ANTES do `test.fail`: uma tela quebrada falha de verdade, em vez
 * de passar como "falha esperada" ou de mandar tirar a combinação de PENDENTES.
 */
export async function afirmarSemRolagem(
  page: Page,
  chave: string,
  largura: number,
  rede: readonly string[],
  redeEsperada: readonly RegExp[] = []
): Promise<void> {
  const medicao = await medirAssentada(page);
  const falhas = rede.filter((f) => !redeEsperada.some((e) => e.test(f)));
  expect(falhas, `[rolagem] ${chave} @ ${largura}px: requisição falhou durante a medição`).toEqual([]);
  test.fail(
    ehPendente(chave, largura),
    `PENDENTE: ${chave} @ ${largura}px rola hoje. Se este teste "passou", tire a combinação de PENDENTES.`
  );
  expect(temProblema(medicao), `[rolagem] ${chave} @ ${largura}px — ${resumir(medicao)}`).toBe(false);
}

/** 401/403 do /api/me/ é como o app descobre que não há sessão: esperado só na tela de login. */
const REDE_DA_TELA_DE_LOGIN = [/^40[13] \/api\/me\/$/];

/** Registra rota × largura (e estados alternativos) mais a tela de login, para `larguras`. */
export function registrarMatriz(larguras: readonly Largura[]): void {
  test.describe(`Sem rolagem horizontal: rota × largura (${larguras.join(' e ')} px)`, () => {
    for (const rota of ROTAS_MEDIDAS) {
      for (const largura of larguras) {
        test(`${rota.path} @ ${largura}px (${rota.perfil})`, async ({ page, baseURL }) => {
          const rede = vigiarRede(page, baseURL);
          await entrar(page, rota.perfil, largura);
          await page.goto(await resolverUrl(page, rota));
          await garantirTela(page, rota, rede);
          await afirmarSemRolagem(page, chaveDe(rota), largura, rede);
        });
        for (const estado of (rota.estados ?? []).filter((e) => !e.larguras || e.larguras.includes(largura))) {
          test(`${chaveDe(rota, estado)} @ ${largura}px (${rota.perfil})`, async ({ page, baseURL }) => {
            const rede = vigiarRede(page, baseURL);
            await entrar(page, rota.perfil, largura);
            await page.goto(await resolverUrl(page, rota));
            await garantirTela(page, rota, rede);
            await page.locator(estado.clicar).first().click();
            await garantirTela(page, { marco: rota.marco, dados: estado.dados }, rede);
            await afirmarSemRolagem(page, chaveDe(rota, estado), largura, rede);
          });
        }
      }
    }

    for (const largura of larguras) {
      test(`tela de login @ ${largura}px (sem sessão)`, async ({ page, baseURL }) => {
        const rede = vigiarRede(page, baseURL);
        await page.setViewportSize({ width: largura, height: 800 });
        await page.goto('/');
        const alvo = { marco: TELA_LOGIN, redeEsperada: REDE_DA_TELA_DE_LOGIN };
        await garantirTela(page, alvo, rede);
        await afirmarSemRolagem(page, TELA_LOGIN, largura, rede, REDE_DA_TELA_DE_LOGIN);
      });
    }
  });
}
