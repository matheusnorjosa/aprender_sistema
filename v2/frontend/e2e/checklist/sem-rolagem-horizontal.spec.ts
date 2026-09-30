/**
 * Sem rolagem horizontal (Programa C, C0): mede e trava. Celular e tablet: 360 e 768 px.
 *
 * Regra do dono (29/09/2026): nenhuma tela com rolagem horizontal, nem da página nem
 * DENTRO de tabela, grade ou card, e nenhum conteúdo cortado sem reticências, em 360,
 * 768, 1024 e 1280 px. Padrão: `v2/docs/specs/frontend/pages.spec.md`, "Padrão responsivo".
 *
 * - Este arquivo mede 360 e 768 com a barra de rolagem sobreposta (padrão do Chromium
 *   headless, como no celular). 1024 e 1280 ficam em `sem-rolagem-horizontal.desktop.spec.ts`,
 *   com a barra clássica ocupando largura, como no Windows.
 * - Cada rota de `AppRoutes.tsx` (e cada vista alternativa declarada) é aberta com um
 *   perfil que tem acesso (lista em `sem-rolagem-horizontal.rotas.ts`), mais a tela de login.
 * - O que rola hoje está em `PENDENTES` e roda com `test.fail`: é o ratchet. Consertou a
 *   tela? O teste passa a falhar ("Expected to fail, but passed") e a combinação sai de
 *   PENDENTES (e o teto do Vitest desce junto).
 * - `test.fail` só é ligado DEPOIS das pré-condições: título próprio da tela, casca
 *   autenticada, nenhum erro na tela, a linha com o texto do seed, rede sem falha e
 *   medição estável. Os controles abaixo provam que cada uma reprova o seu caso.
 *
 * Rodar local (backend do slot já semeado):
 *   SKIP_WEBSERVER=1 BASE_URL=http://127.0.0.1:<porta do vite> \
 *     npx playwright test --project=checklist e2e/checklist/sem-rolagem-horizontal
 */
import { test, expect } from '@playwright/test';
import {
  entrar,
  medirRolagemHorizontal,
  registrarMatriz,
  verificarTela,
  vigiarRede,
  type Medicao,
} from './sem-rolagem-horizontal.medicao';
import { ROTAS_MEDIDAS, TEXTOS_DO_SEED, type RotaMedida } from './sem-rolagem-horizontal.rotas';

// O sw.js (modo offline) intermedeia as requisições e as esconde do page.route e dos
// eventos de rede. Sem ele a rede fica observável (guarda de falhas) e o layout é o mesmo.
test.use({ serviceWorkers: 'block' });

function rota(path: string): RotaMedida {
  const encontrada = ROTAS_MEDIDAS.find((r) => r.path === path);
  if (!encontrada) throw new Error(`rota ${path} não está em ROTAS_MEDIDAS`);
  return encontrada;
}

const CONTROLE = 3_000; // espera curta: nos controles a tela nunca fica pronta

test.describe('Sem rolagem horizontal: controles do verificador', () => {
  test('controle positivo sintético: cada critério detecta sozinho', async ({ page }) => {
    await entrar(page, 'coordenador', 1280);
    await page.goto('/politica-privacidade');
    expect(await verificarTela(page, rota('/politica-privacidade'), [])).toEqual([]);
    const injetar = (html: string, onde: 'main' | 'body' = 'main') =>
      page.evaluate(
        ([conteudo, alvo]) => {
          document.getElementById('controle')?.remove();
          const caixa = document.createElement('div');
          caixa.id = 'controle';
          caixa.innerHTML = conteudo;
          const destino = document.querySelector(alvo);
          if (!destino) throw new Error(`controle: ${alvo} não existe`);
          destino.appendChild(caixa);
        },
        [html, onde] as const
      );
    const alvos = (lista: Medicao['internos']) => lista.map((m) => m.alvo);

    await injetar('<div id="rola" style="overflow-x:auto;width:200px"><div style="width:2000px;height:10px"></div></div>');
    const interno = await medirRolagemHorizontal(page);
    expect(interno.pagina).toBe(0);
    expect(alvos(interno.internos)).toContain('div#rola');

    await injetar('<div id="corta" style="overflow:hidden;width:200px"><div style="width:2000px;height:10px"></div></div>');
    expect(alvos((await medirRolagemHorizontal(page)).cortados)).toContain('div#corta');

    await injetar(
      '<div id="reticencias" style="overflow:hidden;width:200px;white-space:nowrap;text-overflow:ellipsis">' +
        'texto longo '.repeat(50) +
        '</div>'
    );
    expect(alvos((await medirRolagemHorizontal(page)).cortados)).not.toContain('div#reticencias');

    await injetar('<div style="width:3000px;height:10px"></div>', 'body');
    expect((await medirRolagemHorizontal(page)).pagina).toBeGreaterThan(0);
  });

  test('controle negativo: /politica-privacidade a 360 não rola nem corta', async ({ page }) => {
    await entrar(page, 'coordenador', 360);
    await page.goto('/politica-privacidade');
    expect(await verificarTela(page, rota('/politica-privacidade'), [])).toEqual([]);
    expect(await medirRolagemHorizontal(page)).toEqual({ pagina: 0, internos: [], cortados: [] });
  });
});

test.describe('Sem rolagem horizontal: controles das pré-condições (tela quebrada reprova)', () => {
  test('página que não carrega (chunk abortado): ErrorBoundary, sem marco, requisição falha', async ({ page, baseURL }) => {
    const rede = vigiarRede(page, baseURL);
    await entrar(page, 'coordenador', 1280);
    await page.route(
      (url) => url.pathname.includes('PerfilPage'),
      (r) => r.abort()
    );
    await page.goto('/perfil');
    const problemas = (await verificarTela(page, rota('/perfil'), rede, CONTROLE)).join('\n');
    expect(problemas).toContain('marco "Meu perfil" não apareceu');
    expect(problemas).toContain('erro na tela');
    expect(problemas).toMatch(/requisição com falha: FALHOU .*PerfilPage/);
  });

  test('sessão perdida (volta ao login, que também tem main): casca autenticada ausente', async ({ page, baseURL }) => {
    const rede = vigiarRede(page, baseURL);
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/perfil');
    const problemas = (await verificarTela(page, rota('/perfil'), rede, CONTROLE)).join('\n');
    expect(problemas).toContain('casca autenticada ausente');
    expect(problemas).toContain('marco "Meu perfil" não apareceu');
  });

  test('API com 4xx deixa a tabela vazia: falta a linha do seed e a requisição falha', async ({ page, baseURL }) => {
    const rede = vigiarRede(page, baseURL);
    await entrar(page, 'coordenador', 1280);
    await page.route(
      (url) => url.pathname === '/api/solicitacoes/',
      (r) => r.fulfill({ status: 403, contentType: 'application/json', body: '{"detail":"controle"}' })
    );
    await page.goto('/solicitacoes/minhas');
    const problemas = (await verificarTela(page, rota('/solicitacoes/minhas'), rede, CONTROLE)).join('\n');
    expect(problemas).toContain(`dados: nenhum ".ant-table-row" com "${TEXTOS_DO_SEED.municipio}" visível`);
    expect(problemas).toContain('requisição com falha: 403 /api/solicitacoes/');
  });

  test('erro da própria página (Result "Erro ao carregar"): erro na tela', async ({ page, baseURL }) => {
    const rede = vigiarRede(page, baseURL);
    await entrar(page, 'coordenador', 1280);
    await page.route(
      (url) => /^\/api\/solicitacoes\/\d+\/$/.test(url.pathname),
      (r) => r.fulfill({ status: 500, contentType: 'application/json', body: '{}' })
    );
    await page.goto('/solicitacoes/1/editar');
    const problemas = (await verificarTela(page, rota('/solicitacoes/:id/editar'), rede, CONTROLE)).join('\n');
    expect(problemas).toContain('erro na tela');
    expect(problemas).toMatch(/requisição com falha: 500 \/api\/solicitacoes\/\d+\//);
  });
});

registrarMatriz([360, 768]);
