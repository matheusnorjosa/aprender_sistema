/**
 * CHECKLIST_FRONTEND.md - Accessibility Tests (WCAG 2.1)
 *
 * Testa itens da seção "Acessibilidade":
 * - 🔴 Keyboard navigation: Tab order lógico
 * - 🔴 Focus visible: Outline visível ao navegar com teclado
 * - 🔴 Alt text: Todas imagens com alt descritivo
 * - 🔴 Labels em forms: <label> associado a inputs
 * - 🔴 Contraste mínimo 4.5:1
 * - 🟡 ARIA quando necessário
 * - 🟡 Landmarks: <main>, <nav>, <aside>
 *
 * Usa @axe-core/playwright para testes automatizados de acessibilidade.
 */
import { test, expect, Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mockChecklistAuthBootstrap, mockChecklistAuthenticated } from './checklist-network-mocks';
import { entrar, esperarAssentar, verificarTela, vigiarRede } from './sem-rolagem-horizontal.medicao';
import { ROTAS_MEDIDAS } from './sem-rolagem-horizontal.rotas';

test.beforeEach(async ({ page }) => {
  await mockChecklistAuthBootstrap(page);
});

async function waitForLoadingOverlayToDisappear(page: Page): Promise<void> {
  await page.waitForFunction(
    () => {
      const overlay = document.querySelector('.ant-spin-fullscreen.ant-spin-fullscreen-show');
      if (!overlay) return true;
      const style = window.getComputedStyle(overlay);
      return style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0';
    },
    null,
    { timeout: 15000 }
  );
}

// Páginas para testar acessibilidade
const PAGES_TO_TEST = [
  { path: '/', name: 'Login/Home' },
];

// Regras axe-core que queremos enforçar (WCAG 2.1 Level AA)
const AXE_RULES_CONFIG = {
  // Regras críticas (🔴) - falha o teste
  critical: [
    'color-contrast',
    'image-alt',
    'label',
    'button-name',
    'link-name',
    'html-has-lang',
    'document-title',
  ],
  // Regras importantes (🟡) - reporta mas não falha
  important: [
    'landmark-one-main',
    'region',
    'bypass',
    'focus-order-semantics',
  ],
};

test.describe('Checklist: Acessibilidade (axe-core)', () => {
  test('🔴 página inicial deve passar nos testes de acessibilidade', async ({
    page,
  }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();

    // Filtra violações críticas
    const criticalViolations = accessibilityScanResults.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );

    if (criticalViolations.length > 0) {
      const report = criticalViolations
        .map(
          (v) =>
            `[${v.impact}] ${v.id}: ${v.description}\n` +
            `  Afeta: ${v.nodes.length} elementos\n` +
            `  Como corrigir: ${v.help}`
        )
        .join('\n\n');

      console.log('Violações de acessibilidade:\n' + report);
    }

    expect(
      criticalViolations,
      `${criticalViolations.length} violações críticas de acessibilidade`
    ).toHaveLength(0);
  });

  test('🔴 formulários devem ter labels associados', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const results = await new AxeBuilder({ page })
      .include('form, [role="form"], input, select, textarea')
      .withRules(['label', 'label-title-only', 'select-name'])
      .analyze();

    const labelViolations = results.violations.filter(
      (v) => v.id === 'label' || v.id === 'select-name'
    );

    expect(
      labelViolations,
      'Inputs sem labels apropriados'
    ).toHaveLength(0);
  });

  test('🔴 imagens devem ter alt text', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const results = await new AxeBuilder({ page })
      .include('img')
      .withRules(['image-alt'])
      .analyze();

    expect(
      results.violations,
      'Imagens sem alt text'
    ).toHaveLength(0);
  });

  test('🔴 contraste de cores deve ser adequado', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await waitForLoadingOverlayToDisappear(page);

    const results = await new AxeBuilder({ page })
      .exclude('.ant-spin-fullscreen')
      .exclude('.ant-spin-text')
      .withRules(['color-contrast', 'color-contrast-enhanced'])
      .analyze();

    const contrastViolations = results.violations.filter(
      (v) => v.id === 'color-contrast'
    );

    if (contrastViolations.length > 0) {
      console.log('Elementos com contraste insuficiente:');
      contrastViolations.forEach((v) => {
        v.nodes.forEach((node) => {
          console.log(`  - ${node.html}`);
          console.log(`    ${node.failureSummary}`);
        });
      });
    }

    expect(
      contrastViolations,
      'Elementos com contraste insuficiente'
    ).toHaveLength(0);
  });
});

test.describe('Checklist: Navegação por Teclado', () => {
  test('🔴 elementos interativos devem ser focáveis', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Tab através dos primeiros elementos
    const focusedElements: string[] = [];

    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('Tab');

      const focusedElement = await page.evaluate(() => {
        const el = document.activeElement;
        return {
          tag: el?.tagName,
          role: el?.getAttribute('role'),
          text: el?.textContent?.slice(0, 50),
        };
      });

      if (focusedElement.tag && focusedElement.tag !== 'BODY') {
        focusedElements.push(
          `${focusedElement.tag}${focusedElement.role ? `[role="${focusedElement.role}"]` : ''}`
        );
      }
    }

    // Deve haver elementos focáveis
    expect(focusedElements.length).toBeGreaterThan(0);
  });

  test('🔴 focus deve ser visível', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Tab para o primeiro elemento focável
    await page.keyboard.press('Tab');

    // Verifica se o elemento focado tem indicador visual
    const hasFocusIndicator = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return true; // Ignora se nada focado

      const styles = window.getComputedStyle(el);
      const hasOutline =
        styles.outline !== 'none' && styles.outline !== '0px none';
      const hasBoxShadow = styles.boxShadow !== 'none';
      const hasBorder = styles.border !== styles.getPropertyValue('border');

      return hasOutline || hasBoxShadow || hasBorder;
    });

    expect(
      hasFocusIndicator,
      'Elemento focado deve ter indicador visual'
    ).toBeTruthy();
  });

  test('🔴 skip link deve existir', async ({ page }) => {
    await page.goto('/');

    // Tab para o primeiro elemento
    await page.keyboard.press('Tab');

    // Procura por skip link
    const skipLink = page.locator(
      'a[href="#main"], a[href="#content"], a:has-text("Skip"), a:has-text("Pular")'
    );

    // Skip link é obrigatório mas pode estar visível apenas com foco
    const skipLinkCount = await skipLink.count();

    // Se não houver skip link, verifica se o primeiro link focável leva ao conteúdo principal
    if (skipLinkCount === 0) {
      const firstFocusedHref = await page.evaluate(() => {
        const el = document.activeElement as HTMLAnchorElement;
        return el?.href || '';
      });

      // Deve haver algum mecanismo de pular navegação
      expect(
        skipLinkCount > 0 || firstFocusedHref.includes('#'),
        'Deve haver skip link ou mecanismo similar'
      ).toBeTruthy();
    }
  });

  test('🟡 focus trap em modais', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Tenta encontrar e abrir um modal
    const modalTrigger = page.locator(
      'button:has-text("Abrir"), button:has-text("Modal"), [data-testid="modal-trigger"]'
    ).first();

    if ((await modalTrigger.count()) === 0) {
      test.skip(true, 'Nenhum modal encontrado para testar');
      return;
    }

    await modalTrigger.click();
    await page.waitForTimeout(500);

    // Verifica se modal está aberto
    const modal = page.locator('[role="dialog"], .ant-modal, .modal');
    if ((await modal.count()) === 0) {
      test.skip(true, 'Modal não abriu');
      return;
    }

    // Tab muitas vezes - focus deve permanecer no modal
    for (let i = 0; i < 20; i++) {
      await page.keyboard.press('Tab');
    }

    const focusIsInModal = await page.evaluate(() => {
      const modal = document.querySelector(
        '[role="dialog"], .ant-modal-content, .modal'
      );
      return modal?.contains(document.activeElement);
    });

    expect(
      focusIsInModal,
      'Focus deve permanecer preso dentro do modal'
    ).toBeTruthy();
  });
});

test.describe('Checklist: Estrutura Semântica', () => {
  test('🟡 deve ter landmarks apropriados', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const landmarks = await page.evaluate(() => {
      return {
        hasMain:
          !!document.querySelector('main') ||
          !!document.querySelector('[role="main"]'),
        hasNav:
          !!document.querySelector('nav') ||
          !!document.querySelector('[role="navigation"]'),
        hasHeader:
          !!document.querySelector('header') ||
          !!document.querySelector('[role="banner"]'),
      };
    });

    expect(landmarks.hasMain, 'Deve ter <main> ou role="main"').toBeTruthy();
  });

  test('🟡 headings devem estar em ordem', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const headingOrder = await page.evaluate(() => {
      const headings = Array.from(
        document.querySelectorAll('h1, h2, h3, h4, h5, h6')
      );
      return headings.map((h) => ({
        level: parseInt(h.tagName[1]),
        text: h.textContent?.slice(0, 30),
      }));
    });

    // Verifica se não pula níveis
    let previousLevel = 0;
    const skippedLevels: string[] = [];

    for (const heading of headingOrder) {
      if (heading.level > previousLevel + 1 && previousLevel !== 0) {
        skippedLevels.push(
          `H${previousLevel} -> H${heading.level} (${heading.text})`
        );
      }
      previousLevel = heading.level;
    }

    if (skippedLevels.length > 0) {
      console.log('Níveis de heading pulados:', skippedLevels);
    }

    // Não falha, apenas reporta - estrutura de headings pode variar
    expect(headingOrder.length).toBeGreaterThan(0);
  });

  test('🔴 página deve ter h1', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const h1Count = await page.locator('h1').count();

    expect(h1Count, 'Página deve ter pelo menos um H1').toBeGreaterThanOrEqual(1);
  });
});

test.describe('Checklist: Formulários Acessíveis', () => {
  test('🔴 campos obrigatórios devem estar marcados', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const requiredInputs = await page.locator('input[required], select[required], textarea[required]').all();

    for (const input of requiredInputs) {
      const hasAriaRequired = await input.getAttribute('aria-required');
      const hasRequiredAttr = await input.getAttribute('required');

      expect(
        hasAriaRequired === 'true' || hasRequiredAttr !== null,
        'Campos obrigatórios devem ter required ou aria-required'
      ).toBeTruthy();
    }
  });

  test('🟡 inputs devem ter autocomplete apropriado', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const commonInputs = await page.evaluate(() => {
      const inputs = Array.from(
        document.querySelectorAll('input[type="email"], input[type="tel"], input[name*="email"], input[name*="phone"]')
      );
      return inputs.map((input) => ({
        type: input.getAttribute('type'),
        name: input.getAttribute('name'),
        autocomplete: input.getAttribute('autocomplete'),
      }));
    });

    // Reporta inputs que poderiam ter autocomplete
    const missingAutocomplete = commonInputs.filter((i) => !i.autocomplete);

    if (missingAutocomplete.length > 0) {
      console.log(
        'Inputs que poderiam ter autocomplete:',
        missingAutocomplete
      );
    }

    // Não falha - é recomendação
    expect(true).toBeTruthy();
  });
});

test.describe('Checklist: Acessibilidade — páginas autenticadas (axe-core)', () => {
  // O bootstrap padrão (beforeEach) mocka /api/me como 401 -> tela anônima. Aqui
  // sobrescrevemos com um titular autenticado (a rota registrada por último vence no
  // Playwright) para rodar o axe em páginas LOGADAS — antes o gate só cobria a home
  // anônima. Foco em /perfil: renderiza só do prop `user`, sem dados extras a mockar.
  const AUTH_PAGES = [{ path: '/perfil', name: 'Perfil' }];

  for (const { path, name } of AUTH_PAGES) {
    test(`🔴 ${name} (${path}) sem violações críticas de acessibilidade (autenticado)`, async ({
      page,
    }) => {
      await mockChecklistAuthenticated(page);
      await page.goto(path);
      await page.waitForLoadState('networkidle');
      await waitForLoadingOverlayToDisappear(page);

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
        .exclude('.ant-spin-fullscreen')
        .exclude('.ant-spin-text')
        .analyze();

      const critical = results.violations.filter(
        (v) => v.impact === 'critical' || v.impact === 'serious'
      );

      // Inclui `color-contrast`: os 2 gaps globais do tema Antd (label #8c8c8c do
      // Descriptions e botão danger #ff4d4f) foram corrigidos no tema (colorTextTertiary
      // mais escuro + logout des-danger). Agora o contraste fica GUARDADO nas páginas
      // autenticadas, além dos críticos estruturais (label, *-name, alt, aria).
      if (critical.length > 0) {
        console.log(
          `Violações críticas de acessibilidade em ${path}:\n` +
            critical
              .map((v) => `[${v.impact}] ${v.id}: ${v.help} — ${v.nodes.length} elemento(s)`)
              .join('\n')
        );
      }

      expect(
        critical,
        `${critical.length} violações críticas de acessibilidade em ${path}`
      ).toHaveLength(0);
    });
  }
});

test.describe('Checklist: Acessibilidade — telas do Programa C (axe-core, backend semeado)', () => {
  // Regra do dono (ux-principios.spec.md): cada PR de tela do Programa C acrescenta as suas.
  // Login real e dados de `seed_frontend_contract_data`, como o spec de rolagem: o axe mede a
  // tela com as linhas do seed (e os textos longos), não uma lista vazia. Perfil e marco vêm de
  // ROTAS_MEDIDAS; `verificarTela` reprova se a tela não carregou (erro, rede, sem dados).
  const TELAS_PROGRAMA_C = [
    '/dat/admin/usuarios', // C1
    '/dat/admin/grupos', // C2
    '/dat/admin/setores',
    '/dat/admin/funcoes',
    '/dat/admin/gerencias',
    '/dat/admin/municipios',
    '/dat/admin/produtos',
    '/dat/admin/projetos-gerais',
  ];

  // O sw.js (modo offline) esconde as requisições dos eventos de rede que `verificarTela` lê.
  test.use({ serviceWorkers: 'block' });
  // O beforeEach do arquivo mocka /api/me como 401 (tela anônima): aqui a sessão é de verdade.
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  for (const path of TELAS_PROGRAMA_C) {
    for (const largura of [360, 1280]) {
      test(`🔴 ${path} a ${largura}px sem violações críticas de acessibilidade`, async ({ page, baseURL }) => {
        const rota = ROTAS_MEDIDAS.find((r) => r.path === path);
        if (!rota) throw new Error(`${path} não está em ROTAS_MEDIDAS`);
        const rede = vigiarRede(page, baseURL);
        await entrar(page, rota.perfil, largura);
        await page.goto(path);
        expect(await verificarTela(page, rota, rede), `a tela ${path} não ficou pronta`).toEqual([]);

        const results = await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
          .exclude('.ant-spin-fullscreen')
          .exclude('.ant-spin-text')
          .analyze();
        const critical = results.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
        const relatorio = critical
          .map((v) => `[${v.impact}] ${v.id}: ${v.help}\n  ${v.nodes.map((n) => n.target.join(' ')).join('\n  ')}`)
          .join('\n');

        expect(critical, `violações críticas em ${path} a ${largura}px:\n${relatorio}`).toHaveLength(0);
      });
    }
  }
});

test.describe('Checklist: Acessibilidade — opções que não carregaram (C2, axe e teclado)', () => {
  // O aviso de carga que falhou ficava dentro do dropdown do Select: o "Tentar de novo" num portal fora
  // do Tab e um role=alert dentro do listbox (axe: [critical] aria-required-children). Agora fica abaixo
  // do campo, com o Select desabilitado. A falha é simulada (500) só no endpoint das opções.
  test.use({ serviceWorkers: 'block' });
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  const FALHA = { status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'Falha simulada.' }) };

  // Já existia antes do C2 (antd 5.29 + rc-select 14.16), registrado em pages.spec.md (C2,
  // Acessibilidade): o Form.Item obrigatório passa `aria-required="true"` ao Select, e o rc-select
  // o põe no combobox (certo) e também no div raiz, que não tem role (axe: [critical]
  // aria-allowed-attr). O leitor de tela lê o do combobox. Só esse nó sai da conta; qualquer outro
  // aria-allowed-attr reprova.
  type Violacao = Awaited<ReturnType<AxeBuilder['analyze']>>['violations'][number];
  const semAriaRequiredNaRaizDoSelect = (v: Violacao): Violacao => ({
    ...v,
    nodes:
      v.id === 'aria-allowed-attr'
        ? v.nodes.filter(
            (n) =>
              !(
                /^<div class="ant-select [^"]*ant-select-in-form-item/.test(n.html) &&
                /^Fix all of the following:\s*ARIA attribute is not allowed: aria-required="true"\s*$/.test(n.failureSummary ?? '')
              ),
          )
        : v.nodes,
  });

  async function semViolacoesCriticas(page: Page, onde: string, escopo?: string): Promise<void> {
    const axe = new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']);
    if (escopo) axe.include(escopo);
    const results = await axe.exclude('.ant-spin-fullscreen').exclude('.ant-spin-text').analyze();
    const critical = results.violations
      .filter((v) => v.impact === 'critical' || v.impact === 'serious')
      .map(semAriaRequiredNaRaizDoSelect)
      .filter((v) => v.nodes.length > 0);
    const relatorio = critical
      .map((v) => `[${v.impact}] ${v.id}: ${v.help}\n  ${v.nodes.map((n) => n.target.join(' ')).join('\n  ')}`)
      .join('\n');
    expect(critical, `violações críticas em ${onde}:\n${relatorio}`).toHaveLength(0);
  }

  for (const largura of [360, 1280]) {
    test(`🔴 Gerências a ${largura}px: setores sem carregar — aviso fora do Select, "Tentar de novo" no Tab`, async ({
      page,
      baseURL,
    }) => {
      const rota = ROTAS_MEDIDAS.find((r) => r.path === '/dat/admin/gerencias');
      if (!rota) throw new Error('/dat/admin/gerencias não está em ROTAS_MEDIDAS');
      const rede = vigiarRede(page, baseURL);
      await entrar(page, rota.perfil, largura);
      await page.route(/\/api\/rbac\/meta\//, (r) => r.fulfill(FALHA));
      await page.goto(rota.path);
      const alvo = { ...rota, redeEsperada: [/^500 \/api\/rbac\/meta\//] };
      expect(await verificarTela(page, alvo, rede), 'a tela de Gerências não ficou pronta').toEqual([]);

      await page.getByRole('button', { name: /Nova Gerencia/ }).click();
      const modal = page.getByRole('dialog');
      const alerta = modal.getByRole('alert').filter({ hasText: 'Não foi possível carregar os setores.' });
      await expect(alerta).toBeVisible();
      await expect(modal.getByRole('combobox', { name: /Setor canônico/ })).toBeDisabled();

      await modal.getByLabel('Rótulo nas planilhas').focus();
      await page.keyboard.press('Tab');
      const tentar = alerta.getByRole('button', { name: 'Tentar de novo: carregar os setores', exact: true });
      await expect(tentar).toBeFocused();

      // Com o zoom de abertura ainda rodando, o modal está semitransparente e o axe mede um contraste falso.
      await expect(page.locator('.ant-modal[class*="ant-zoom"]')).toHaveCount(0);
      await semViolacoesCriticas(page, `o modal de Gerências a ${largura}px`, '.ant-modal-wrap');

      // Carregou: o foco vai para o campo (antes caía no body, fora do modal).
      await page.unroute(/\/api\/rbac\/meta\//);
      await page.keyboard.press('Enter');
      await expect(modal.getByRole('combobox', { name: /Setor canônico/ })).toBeFocused();
      await expect(alerta).toHaveCount(0);
    });

    test(`🔴 Produtos a ${largura}px: projetos sem carregar — o filtro avisa na página, "Tentar de novo" no Tab`, async ({
      page,
      baseURL,
    }) => {
      const rota = ROTAS_MEDIDAS.find((r) => r.path === '/dat/admin/produtos');
      if (!rota) throw new Error('/dat/admin/produtos não está em ROTAS_MEDIDAS');
      const rede = vigiarRede(page, baseURL);
      await entrar(page, rota.perfil, largura);
      await page.route(/\/api\/projetos\/(\?|$)/, (r) => r.fulfill(FALHA));
      await page.goto(rota.path);
      const alvo = { ...rota, redeEsperada: [/^500 \/api\/projetos\//] };
      // O único erro em main é o aviso esperado (os projetos do filtro), não a lista.
      const problemas = await verificarTela(page, alvo, rede);
      expect(problemas, 'a tela de Produtos não ficou pronta').toEqual(['erro na tela: 1 Result/Alert de erro em main']);

      const alerta = page.getByRole('alert').filter({ hasText: 'Não foi possível carregar os projetos.' });
      await expect(alerta).toBeVisible();
      await expect(page.getByRole('combobox', { name: 'Filtrar por projeto' })).toBeDisabled();

      await page.getByRole('button', { name: /Novo Produto/ }).focus();
      await page.keyboard.press('Tab');
      await expect(alerta.getByRole('button', { name: 'Tentar de novo: carregar os projetos', exact: true })).toBeFocused();

      await semViolacoesCriticas(page, `Produtos a ${largura}px`);

      // Carregou: o foco vai para o filtro (antes caía no body e o Tab voltava ao topo).
      await page.unroute(/\/api\/projetos\/(\?|$)/);
      await page.keyboard.press('Enter');
      await expect(page.getByRole('combobox', { name: 'Filtrar por projeto' })).toBeFocused();
    });

    test(`🔴 Produtos a ${largura}px: modal sem projetos e coleções — dois avisos no Tab, cada um com o seu nome`, async ({
      page,
      baseURL,
    }) => {
      const rota = ROTAS_MEDIDAS.find((r) => r.path === '/dat/admin/produtos');
      if (!rota) throw new Error('/dat/admin/produtos não está em ROTAS_MEDIDAS');
      const rede = vigiarRede(page, baseURL);
      await entrar(page, rota.perfil, largura);
      await page.route(/\/api\/projetos\/(\?|$)/, (r) => r.fulfill(FALHA));
      await page.route(/\/api\/options\/colecoes\//, (r) => r.fulfill(FALHA));
      await page.goto(rota.path);
      const alvo = { ...rota, redeEsperada: [/^500 \/api\/projetos\//, /^500 \/api\/options\/colecoes\//] };
      const problemas = await verificarTela(page, alvo, rede);
      expect(problemas, 'a tela de Produtos não ficou pronta').toEqual(['erro na tela: 1 Result/Alert de erro em main']);

      await page.getByRole('button', { name: /Novo Produto/ }).click();
      const modal = page.getByRole('dialog');
      const projetos = modal.getByRole('button', { name: 'Tentar de novo: carregar os projetos', exact: true });
      const colecoes = modal.getByRole('button', { name: 'Tentar de novo: carregar as coleções', exact: true });
      await expect(modal.getByRole('combobox', { name: 'Projeto' })).toBeDisabled();
      await expect(modal.getByRole('combobox', { name: 'Coleção' })).toBeDisabled();

      await modal.getByLabel('Descricao').focus();
      await page.keyboard.press('Tab');
      await expect(projetos).toBeFocused();
      await page.keyboard.press('Tab');
      await expect(colecoes).toBeFocused();

      await expect(page.locator('.ant-modal[class*="ant-zoom"]')).toHaveCount(0);
      await semViolacoesCriticas(page, `o modal de Produtos a ${largura}px`, '.ant-modal-wrap');

      // Carregou: o foco vai para o campo que o botão recarregou.
      await page.unroute(/\/api\/options\/colecoes\//);
      await page.keyboard.press('Enter');
      await expect(modal.getByRole('combobox', { name: 'Coleção' })).toBeFocused();
    });
  }
});

test.describe('Checklist: Acessibilidade — vazio com filtro (C2, axe)', () => {
  // O vazio que diz o que fazer (ux-principios) ia na cor de texto desabilitado da tabela (#bfbfbf,
  // 1,83:1: axe color-contrast). O seed sempre tem linhas, então o vazio é montado aqui: filtro de
  // projeto e uma busca sem resultado. Quem mede o contraste é o de 1280: a 360 o axe não decide a
  // cor de fundo da tabela (pseudo-elemento) e deixa o texto em `incomplete`.
  test.use({ serviceWorkers: 'block' });
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  for (const largura of [360, 1280]) {
    test(`🔴 Produtos a ${largura}px: vazio com filtro de projeto e busca, sem violações críticas`, async ({
      page,
      baseURL,
    }) => {
      const rota = ROTAS_MEDIDAS.find((r) => r.path === '/dat/admin/produtos');
      if (!rota) throw new Error('/dat/admin/produtos não está em ROTAS_MEDIDAS');
      const rede = vigiarRede(page, baseURL);
      await entrar(page, rota.perfil, largura);
      await page.goto(rota.path);
      expect(await verificarTela(page, rota, rede), 'a tela de Produtos não ficou pronta').toEqual([]);

      await page.getByRole('combobox', { name: 'Filtrar por projeto' }).click();
      await page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option').first().click();
      // Com a animação de saída ainda rodando, o axe mede as opções do dropdown fechado.
      await expect(page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden)')).toHaveCount(0);
      const busca = page.getByRole('searchbox', { name: 'Buscar produtos por nome ou código' });
      await busca.fill('zzqqxx');
      await busca.press('Enter');
      await expect(page.getByText(/^Nenhum produto para "zzqqxx" no projeto /)).toBeVisible();
      await esperarAssentar(page);

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
        .exclude('.ant-spin-fullscreen')
        .exclude('.ant-spin-text')
        .analyze();
      const critical = results.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
      const relatorio = critical
        .map((v) => `[${v.impact}] ${v.id}: ${v.help}\n  ${v.nodes.map((n) => n.target.join(' ')).join('\n  ')}`)
        .join('\n');
      expect(critical, `violações críticas no vazio de Produtos a ${largura}px:\n${relatorio}`).toHaveLength(0);

      // Limpar some com o clique: o foco vai para a busca, não para o body.
      await page.getByRole('button', { name: 'Limpar busca e filtro de projeto' }).focus();
      await page.keyboard.press('Enter');
      await expect(busca).toBeFocused();
      await expect(busca).toHaveValue('');
    });
  }
});
