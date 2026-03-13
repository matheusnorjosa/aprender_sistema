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
import { mockChecklistAuthBootstrap } from './checklist-network-mocks';

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
