/**
 * Sessão: expiração, várias abas e "Sair agora" (auditoria UX 30/09).
 *
 * Rodada 1 (ALTA): o monitor mandava para '/login' e o aviso para '/logout', rotas que não
 * existem: a área de conteúdo ficava em branco e a sessão continuava aberta.
 * Rodada 2 (ALTA): o relógio local é de cada aba, mas a sessão é do navegador. Uma aba
 * ociosa fazia POST de logout ao zerar e derrubava a aba em uso. Agora ela pergunta ao
 * servidor (`GET /api/me/`): sessão viva → recomeça o relógio; sem sessão → login com o
 * motivo, sem POST de logout. O logout real fica só para o "Sair" e o "Sair agora".
 *
 * Rodada 3: a atividade renova a sessão no servidor (GET /api/me/, no máximo a cada 10 min);
 * a contagem do aviso anda; e, sem rede, "Continuar logado" e "Sair" dizem "sem conexão" (e o
 * "Sair" não recarrega para a tela quebrada do service worker).
 *
 * O relógio do navegador é adiantado com `clock` (o monitor confere a cada 60 s; a sessão
 * local dura 2 h). Roda no projeto `checklist`, com o backend semeado por
 * `seed_frontend_contract_data`.
 */
import { test, expect, type BrowserContext, type Page } from '@playwright/test';
import { entrar } from './sem-rolagem-horizontal.medicao';

const telaDeLogin = (page: Page) => page.getByRole('heading', { level: 1, name: 'Login' });
const casca = (page: Page) => page.getByRole('button', { name: /Sair$/ });

async function abrirLogado(page: Page): Promise<void> {
  await page.clock.install();
  await entrar(page, 'coordenador', 1280);
  await page.goto('/home');
  await expect(casca(page)).toBeVisible();
  // Sem request em voo: no trace, um request que terminou depois do POST de logout devolveu
  // o cookie da sessão antiga e ela seguiu viva (defeito do backend, registrado à parte).
  await page.waitForLoadState('networkidle');
}

async function sessaoNoServidor(page: Page): Promise<number> {
  return (await page.request.get('/api/me/')).status();
}

/** Conta os POST de logout que a PÁGINA faz (os de `page.request`, do teste, não entram). */
function logoutsDaPagina(page: Page): () => number {
  let total = 0;
  page.on('request', (req) => {
    if (req.method() === 'POST' && req.url().includes('/api/auth/logout/')) total += 1;
  });
  return () => total;
}

/** Encerra a sessão no servidor por fora da aba, como a expiração no Redis: a aba não sabe. */
async function encerrarSessaoPorFora(page: Page): Promise<void> {
  const { csrfToken } = (await (await page.request.get('/api/csrf/')).json()) as { csrfToken?: string };
  const resp = await page.request.post('/api/auth/logout/', { headers: { 'X-CSRFToken': csrfToken ?? '' } });
  expect(resp.ok(), `logout por fora falhou (${resp.status()})`).toBeTruthy();
}

test('sessão encerrada no servidor: o relógio zerado leva ao login com o motivo, sem POST de logout', async ({ page }) => {
  await abrirLogado(page);
  const logouts = logoutsDaPagina(page);
  await encerrarSessaoPorFora(page);

  await page.clock.fastForward('02:02:00');

  await expect(telaDeLogin(page)).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('Sua sessão expirou por inatividade. Entre de novo.');
  expect(logouts()).toBe(0);
});

/** Os requests da página ao /api/ (os de `page.request`, do teste, não entram). */
function requestsAApi(page: Page): string[] {
  const vistos: string[] = [];
  page.on('request', (req) => {
    const caminho = new URL(req.url()).pathname;
    if (caminho.startsWith('/api/')) vistos.push(`${req.method()} ${caminho}`);
  });
  return vistos;
}

// Rodada 5 (MÉDIA): cada aba contava só dos próprios requests e perguntava ao servidor 121 min
// depois; a pergunta de uma renovava a sessão para a outra, e duas abas largadas a mantinham viva
// sem limite. Agora o horário da última resposta do servidor é comum às abas (localStorage).
test('duas abas: a ociosa não derruba a sessão da que está em uso nem a mantém viva depois', async ({ context }) => {
  await context.clock.install();
  const ociosa = await context.newPage();
  const emUso = await context.newPage();
  await entrar(emUso, 'coordenador', 1280); // o cookie de sessão é do contexto: vale para as duas
  for (const aba of [ociosa, emUso]) {
    await aba.goto('/home');
    await expect(casca(aba)).toBeVisible();
    await aba.waitForLoadState('networkidle');
  }
  const logouts = [logoutsDaPagina(ociosa), logoutsDaPagina(emUso)];
  const daOciosa = requestsAApi(ociosa);

  // 2 h 30 sem tocar na aba ociosa; a outra em uso a cada 30 min (cada tecla renova a sessão).
  for (let i = 0; i < 5; i++) {
    await context.clock.fastForward('00:30:00');
    await emUso.bringToFront();
    const renovou = emUso.waitForResponse((resp) => new URL(resp.url()).pathname === '/api/me/');
    await emUso.keyboard.press('Shift');
    expect((await renovou).status()).toBe(200);
  }
  // A ociosa vê as respostas à outra: não pergunta ao servidor nem mostra o aviso.
  expect(daOciosa).toEqual([]);
  await expect(ociosa.getByRole('button', { name: 'Sair agora' })).toBeHidden();
  await expect(casca(ociosa)).toBeVisible();

  // As duas largadas: nenhuma renova a sessão antes de ela vencer, 2 h depois do último request.
  const depoisDoUso = [requestsAApi(ociosa), requestsAApi(emUso)];
  await context.clock.fastForward('01:59:00');
  expect(depoisDoUso).toEqual([[], []]);
  // A sessão vence no servidor (o Redis a apaga): encerrada por fora, a aba não sabe.
  await encerrarSessaoPorFora(emUso);
  await context.clock.fastForward('00:03:00');

  for (const aba of [ociosa, emUso]) {
    await expect(telaDeLogin(aba)).toBeVisible();
    await expect(aba.getByRole('alert')).toContainText('Sua sessão expirou por inatividade. Entre de novo.');
  }
  expect(logouts.map((n) => n())).toEqual([0, 0]);
});

/** Duas abas logadas no mesmo contexto (o cookie de sessão é dele: vale para as duas). */
async function duasAbasLogadas(context: BrowserContext): Promise<[Page, Page]> {
  const outra = await context.newPage();
  const daqui = await context.newPage();
  await entrar(daqui, 'coordenador', 1280);
  for (const aba of [outra, daqui]) {
    await aba.goto('/home');
    await expect(casca(aba)).toBeVisible();
    await aba.waitForLoadState('networkidle');
  }
  return [outra, daqui];
}

const SAIU_EM_OUTRA_ABA = 'Você saiu do sistema em outra aba. Entre de novo.';

// Rodada 6 (MÉDIA): as respostas do próprio logout gravavam o horário comum às abas, e as outras
// contavam dele: seguiam com cara de logadas por mais 121 min (e fechavam sozinhas o aviso aberto),
// depois iam ao login com "expirou por inatividade". Agora o "Sair" apaga esse horário, e o evento
// 'storage' faz as outras perguntarem ao servidor na hora, sem adiantar relógio nenhum.
test('"Sair" numa aba leva a outra ao login na hora, com o motivo', async ({ context }) => {
  const [outra, daqui] = await duasAbasLogadas(context);
  const logoutsDaOutra = logoutsDaPagina(outra);

  await daqui.bringToFront();
  await casca(daqui).click();

  await expect(telaDeLogin(daqui)).toBeVisible();
  await expect(telaDeLogin(outra)).toBeVisible();
  await expect(outra.getByRole('alert')).toContainText(SAIU_EM_OUTRA_ABA);
  await expect(daqui.getByText(SAIU_EM_OUTRA_ABA)).toHaveCount(0); // quem saiu foi esta
  expect(logoutsDaOutra()).toBe(0);
});

test('"Sair agora" com o aviso aberto nas duas abas: a outra vai ao login, o aviso não some sozinho', async ({ context }) => {
  await context.clock.install();
  const [outra, daqui] = await duasAbasLogadas(context);
  await context.clock.fastForward('01:56:00');
  await expect(outra.getByRole('button', { name: 'Sair agora' })).toBeVisible();
  const sairAgora = daqui.getByRole('button', { name: 'Sair agora' });
  await expect(sairAgora).toBeVisible();

  await daqui.bringToFront();
  await sairAgora.click();

  await expect(telaDeLogin(daqui)).toBeVisible();
  await expect(telaDeLogin(outra)).toBeVisible();
  await expect(outra.getByRole('alert')).toContainText(SAIU_EM_OUTRA_ABA);
});

test('"Sair agora" no aviso encerra a sessão e mostra o login', async ({ page }) => {
  await abrirLogado(page);

  await page.clock.fastForward('01:56:00');
  const sair = page.getByRole('button', { name: 'Sair agora' });
  await expect(sair).toBeVisible();
  await sair.click();

  await expect(telaDeLogin(page)).toBeVisible();
  expect(await sessaoNoServidor(page)).toBeGreaterThanOrEqual(401);
});

test('atividade renova a sessão no servidor (GET /api/me/), no máximo a cada 10 min e sem nada visível', async ({ page }) => {
  await abrirLogado(page);
  const perguntas: string[] = [];
  page.on('request', (req) => {
    if (new URL(req.url()).pathname === '/api/me/') perguntas.push(req.method());
  });

  await page.keyboard.press('Shift'); // logo depois do boot: nada
  await page.clock.fastForward('00:11:00');
  const renovou = page.waitForResponse((resp) => new URL(resp.url()).pathname === '/api/me/');
  await page.keyboard.press('Shift');
  expect((await renovou).status()).toBe(200);
  await page.keyboard.press('Shift'); // a seguinte só daqui a 10 min
  await page.mouse.wheel(0, 200);

  expect(perguntas).toEqual(['GET']);
  await expect(page.getByRole('button', { name: 'Continuar logado' })).toBeHidden();
  await expect(casca(page)).toBeVisible();
});

// Rodada 4 (MÉDIA): o relógio contava só das renovações do monitor. Um request da tela depois
// delas deixava a sessão viva além do zero local, e a pergunta da aba parada a esticava por mais
// 2 h. Agora conta da última resposta do servidor a um request desta aba.
test('o relógio conta do último request da aba: 119 min depois dele ainda não pergunta', async ({ page }) => {
  await abrirLogado(page);
  await page.clock.fastForward('00:03:00');
  // Um request da tela pelo fetchAPI do app (o mesmo módulo que a tela usa), sem renovação do monitor.
  const status = await page.evaluate(async () => {
    const api = (await import('/src/api/config.ts')) as { fetchAPI: (url: string) => Promise<unknown> };
    await api.fetchAPI('/me/policies/');
    return 'ok';
  });
  expect(status).toBe('ok');
  const perguntas: string[] = [];
  page.on('request', (req) => {
    if (new URL(req.url()).pathname === '/api/me/') perguntas.push(req.method());
  });

  await page.clock.fastForward('01:59:00'); // 122 min depois do boot, 119 depois do último request

  await expect(page.getByRole('button', { name: 'Continuar logado' })).toBeVisible(); // aviso: falta ~1 min
  expect(perguntas).toEqual([]);

  const pergunta = page.waitForRequest((req) => new URL(req.url()).pathname === '/api/me/');
  await page.clock.fastForward('00:03:00'); // 122 min depois do último request: pergunta ao servidor
  expect((await pergunta).method()).toBe('GET');
});

test('a contagem do aviso anda a cada segundo', async ({ page }) => {
  await abrirLogado(page);
  await page.clock.fastForward('01:55:30');
  const contagem = page.getByRole('dialog').getByText(/^\d+:\d{2}$/);
  await expect(contagem).toBeVisible();
  const antes = await contagem.textContent();

  await page.clock.runFor(3000);

  await expect(contagem).not.toHaveText(antes ?? '');
});

test('"Continuar logado" sem rede diz "Sem conexão com o servidor." e renova quando a rede volta', async ({ page, context }) => {
  await abrirLogado(page);
  await page.clock.fastForward('01:56:00');
  const continuar = page.getByRole('button', { name: 'Continuar logado' });
  await expect(continuar).toBeVisible();

  await context.setOffline(true);
  await continuar.click();
  const erro = page.getByRole('alert').filter({ hasText: 'Não foi possível renovar a sessão' });
  await expect(erro).toContainText('Sem conexão com o servidor.');
  await expect(erro).not.toContainText('CSRF');

  await context.setOffline(false);
  await continuar.click();
  await expect(continuar).toBeHidden();
  await expect(casca(page)).toBeVisible();
});

test('"Sair" sem rede avisa e não recarrega; com a rede de volta, sai', async ({ page, context }) => {
  await abrirLogado(page);

  await context.setOffline(true);
  await casca(page).click();
  await expect(page.getByText('Não foi possível sair: sem conexão. Tente de novo.')).toBeVisible();
  await expect(casca(page)).toBeVisible(); // continua na tela (antes: reload para o JSON offline)

  await context.setOffline(false);
  await casca(page).click();
  await expect(telaDeLogin(page)).toBeVisible();
  expect(await sessaoNoServidor(page)).toBeGreaterThanOrEqual(401);
});
