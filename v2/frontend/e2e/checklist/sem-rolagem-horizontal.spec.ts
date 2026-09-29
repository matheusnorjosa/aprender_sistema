/**
 * Sem rolagem horizontal (Programa C, C0): mede e trava.
 *
 * Regra do dono (29/09/2026): nenhuma tela com rolagem horizontal, nem da
 * página nem DENTRO de tabela, grade ou card, em 360, 768, 1024 e 1280 px.
 * Padrão: `v2/docs/specs/frontend/pages.spec.md`, seção "Padrão responsivo".
 *
 * - Cada rota de `AppRoutes.tsx` é aberta com um perfil que tem acesso, nas 4
 *   larguras (lista e perfis em `sem-rolagem-horizontal.rotas.ts`), mais a tela de login.
 * - O que rola hoje está em `PENDENTES` e roda com `test.fail`: é o ratchet.
 *   Consertou a tela? O teste passa a falhar ("Expected to fail, but passed")
 *   e a combinação tem de sair de `PENDENTES`.
 * - `test.fail` só é ligado DEPOIS das pré-condições (login, casca carregada,
 *   perfil com acesso, medição estável, API sem 5xx/429). Uma tela que quebra ou
 *   nega acesso falha de verdade, em vez de passar como "falha esperada".
 *
 * Dados: `seed_frontend_contract_data` traz textos longos (80+ caracteres) nos
 * campos que aparecem em tabela. Tabela vazia nunca estoura e daria falso verde.
 * Pelo mesmo motivo, 5xx/429 em `/api/` reprova a pré-condição: tela sem dados não
 * foi medida. O proxy do Vite devolve 500 de vez em quando, quando o gunicorn recicla
 * um worker (o Django registra 200); isso cai no retry do CI. Local, use `--retries=1`.
 *
 * Rodar local (backend do slot já semeado):
 *   SKIP_WEBSERVER=1 BASE_URL=http://127.0.0.1:<porta do vite> \
 *     npx playwright test --project=checklist e2e/checklist/sem-rolagem-horizontal.spec.ts
 */
import { test, expect, type Page } from '@playwright/test';
import {
  LARGURAS,
  PENDENTES,
  PERFIS,
  ROTAS_MEDIDAS,
  SENHA_PERFIS,
  TELA_LOGIN,
  type Perfil,
  type RotaMedida,
} from './sem-rolagem-horizontal.rotas';

// O sw.js (modo offline) intermedeia /api/ e esconde as requisições do page.route. Sem ele a
// rede fica observável (guarda de 5xx/429) e o layout é o mesmo.
test.use({ serviceWorkers: 'block' });

interface Medicao {
  /** documentElement.scrollWidth - clientWidth (> 0 = a página rola). */
  pagina: number;
  /** Elementos com overflow-x auto/scroll cujo conteúdo excede a caixa. */
  internos: { alvo: string; excesso: number }[];
}

/**
 * Dois critérios, porque o primeiro sozinho é cego à tabela do AntD: com
 * `scroll.x` a rolagem fica DENTRO de `.ant-table-content` e a página mede 0
 * (o controle positivo abaixo prova isso).
 * 1. a página: `documentElement.scrollWidth - clientWidth > 0`;
 * 2. qualquer elemento com `overflow-x` auto/scroll e `scrollWidth - clientWidth > 1`
 *    (1 px de folga para arredondamento de subpixel).
 */
async function medirRolagemHorizontal(page: Page): Promise<Medicao> {
  return page.evaluate(() => {
    const descrever = (el: Element): string => {
      const id = el.id ? `#${el.id}` : '';
      const classes = Array.from(el.classList).slice(0, 3).map((c) => `.${c}`).join('');
      return `${el.tagName.toLowerCase()}${id}${classes}`;
    };
    const internos: { alvo: string; excesso: number }[] = [];
    for (const el of Array.from(document.body.querySelectorAll('*'))) {
      const { overflowX } = getComputedStyle(el);
      if (overflowX !== 'auto' && overflowX !== 'scroll') continue;
      const excesso = el.scrollWidth - el.clientWidth;
      if (excesso > 1) internos.push({ alvo: descrever(el), excesso });
    }
    const de = document.documentElement;
    return { pagina: de.scrollWidth - de.clientWidth, internos };
  });
}

function rolaNaHorizontal(medicao: Medicao): boolean {
  return medicao.pagina > 0 || medicao.internos.length > 0;
}

function resumir(medicao: Medicao): string {
  const internos = medicao.internos.map((m) => `${m.alvo} +${m.excesso}px`).join('; ');
  return `página +${medicao.pagina}px; internos: ${internos || 'nenhum'}`;
}

/**
 * Chamadas da API que voltaram 5xx ou 429 nesta página. Tabela vazia por erro não
 * estoura largura: sem esta guarda, o erro passaria por "sem rolagem" (falso verde).
 */
const falhasDeApi = new WeakMap<Page, string[]>();

function vigiarApi(page: Page): void {
  const falhas: string[] = [];
  falhasDeApi.set(page, falhas);
  page.on('response', (resposta) => {
    const status = resposta.status();
    if (resposta.url().includes('/api/') && (status >= 500 || status === 429)) {
      falhas.push(`${status} ${new URL(resposta.url()).pathname}`);
    }
  });
}

async function entrar(page: Page, perfil: Perfil, largura: number): Promise<void> {
  await page.setViewportSize({ width: largura, height: 800 });
  vigiarApi(page);
  const csrf = await page.request.get('/api/csrf/');
  expect(csrf.ok(), `[rolagem][login] csrf falhou (${perfil})`).toBeTruthy();
  const { csrfToken } = (await csrf.json()) as { csrfToken?: string };
  const login = await page.request.post('/api/auth/login/', {
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken ?? '' },
    data: { username: PERFIS[perfil], password: SENHA_PERFIS },
  });
  expect(login.ok(), `[rolagem][login] login falhou (${perfil} = ${PERFIS[perfil]})`).toBeTruthy();
}

/** Espera a página assentar: rede parada e nenhum spinner do AntD girando. */
async function esperarAssentar(page: Page): Promise<void> {
  await page.waitForLoadState('networkidle');
  await expect(page.locator('.ant-spin-spinning')).toHaveCount(0, { timeout: 15_000 });
}

async function navegar(page: Page, perfil: Perfil, url: string): Promise<void> {
  await page.goto(url);
  await esperarAssentar(page);
  await expect(page.locator('main#main'), `[rolagem] ${url} não abriu a casca autenticada`).toBeVisible();
  await expect(page.getByText('Recurso indisponível'), `[rolagem] ${perfil} não abre ${url}`).toHaveCount(0);
}

async function abrir(page: Page, perfil: Perfil, url: string, largura: number): Promise<void> {
  await entrar(page, perfil, largura);
  await navegar(page, perfil, url);
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
 * Mede até duas leituras seguidas darem o mesmo resultado, com a rede parada entre
 * elas. Sob carga, o `networkidle` pode cair entre duas levas de requisições de uma
 * tela e a primeira leitura pegaria um estado de transição.
 */
async function medirAssentada(page: Page): Promise<Medicao> {
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

function ehPendente(chave: string, largura: number): boolean {
  return (PENDENTES[chave] ?? []).some((l) => l === largura);
}

/** Pré-condições (medição estável, API sem 5xx/429) primeiro; daí em diante só a medição decide. */
async function afirmarSemRolagem(page: Page, chave: string, largura: number): Promise<void> {
  const medicao = await medirAssentada(page);
  expect(falhasDeApi.get(page) ?? [], `[rolagem] ${chave} @ ${largura}px: a API falhou, a tela não foi medida com dados`).toEqual([]);
  test.fail(
    ehPendente(chave, largura),
    `PENDENTE: ${chave} @ ${largura}px rola hoje. Se este teste "passou", tire a combinação de PENDENTES.`
  );
  expect(rolaNaHorizontal(medicao), `[rolagem] ${chave} @ ${largura}px — ${resumir(medicao)}`).toBe(false);
}

test.describe('Sem rolagem horizontal: controles do verificador', () => {
  test('controle positivo: /dat/admin/usuarios a 1024 rola DENTRO da tabela, não na página', async ({ page }) => {
    // Enquanto a tela estiver em PENDENTES, prova o caso real do AntD. Quando o
    // C1 consertar Usuários, este controle muda de alvo (outra tela ainda
    // pendente) ou sai; o controle sintético abaixo continua valendo.
    await abrir(page, 'dat', '/dat/admin/usuarios', 1024);
    const medicao = await medirAssentada(page);
    expect(medicao.pagina, 'o critério da página sozinho não enxerga esta rolagem').toBe(0);
    expect(
      medicao.internos.some((m) => m.alvo.includes('ant-table')),
      `o verificador não viu a rolagem interna da tabela (${resumir(medicao)})`
    ).toBe(true);
  });

  test('controle positivo sintético: os dois critérios detectam, cada um por si', async ({ page }) => {
    await abrir(page, 'coordenador', '/politica-privacidade', 1280);
    await page.evaluate(() => {
      const caixa = document.createElement('div');
      caixa.id = 'controle-interno';
      caixa.style.cssText = 'overflow-x:auto;width:200px';
      caixa.innerHTML = '<div style="width:2000px;height:10px"></div>';
      document.querySelector('main')?.appendChild(caixa);
    });
    const interno = await medirRolagemHorizontal(page);
    expect(interno.pagina).toBe(0);
    expect(interno.internos.map((m) => m.alvo)).toContain('div#controle-interno');

    await page.evaluate(() => {
      document.getElementById('controle-interno')?.remove();
      const largo = document.createElement('div');
      largo.style.cssText = 'width:3000px;height:10px';
      document.body.appendChild(largo);
    });
    const pagina = await medirRolagemHorizontal(page);
    expect(pagina.pagina).toBeGreaterThan(0);
  });

  test('controle da guarda de API: 500 na lista de usuários é registrado antes da medição', async ({ page }) => {
    await entrar(page, 'dat', 1280);
    await page.route(
      (url) => url.pathname.startsWith('/api/usuarios-admin/'),
      (rota) => rota.fulfill({ status: 500, body: '{}' })
    );
    await navegar(page, 'dat', '/dat/admin/usuarios');
    expect(falhasDeApi.get(page)).toContain('500 /api/usuarios-admin/');
  });

  test('controle negativo: /politica-privacidade a 1280 não rola', async ({ page }) => {
    await abrir(page, 'coordenador', '/politica-privacidade', 1280);
    const medicao = await medirRolagemHorizontal(page);
    expect(medicao).toEqual({ pagina: 0, internos: [] });
  });
});

test.describe('Sem rolagem horizontal: rota × largura', () => {
  for (const rota of ROTAS_MEDIDAS) {
    for (const largura of LARGURAS) {
      test(`${rota.path} @ ${largura}px (${rota.perfil})`, async ({ page }) => {
        await entrar(page, rota.perfil, largura);
        await navegar(page, rota.perfil, await resolverUrl(page, rota));
        await afirmarSemRolagem(page, rota.path, largura);
      });
    }
  }

  for (const largura of LARGURAS) {
    test(`tela de login @ ${largura}px (sem sessão)`, async ({ page }) => {
      await page.setViewportSize({ width: largura, height: 800 });
      vigiarApi(page);
      await page.goto('/');
      await esperarAssentar(page);
      await expect(page.locator('#login-title')).toBeVisible();
      await afirmarSemRolagem(page, TELA_LOGIN, largura);
    });
  }
});
