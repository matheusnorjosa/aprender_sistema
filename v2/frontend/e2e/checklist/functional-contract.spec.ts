/**
 * Functional Contract Matrix - Critical pages/fields (Issue #705)
 *
 * Executa com backend real via Docker (sem mocks de dados críticos),
 * garantindo rastreabilidade de falhas por rota/campo/endpoint.
 */

import { test, expect, Page } from '@playwright/test';
import { FUNCTIONAL_CRITICAL_MATRIX, type FunctionalMatrixCase } from './functional-contract.matrix';

async function loginByApi(page: Page, username: string, password: string): Promise<void> {
  const csrfResponse = await page.request.get('/api/csrf/');
  expect(csrfResponse.ok(), `[matrix][auth] csrf failed for user=${username}`).toBeTruthy();
  const csrfData = (await csrfResponse.json()) as { csrfToken?: string };
  const csrfToken = csrfData.csrfToken;
  expect(csrfToken, `[matrix][auth] csrf token missing for user=${username}`).toBeTruthy();

  const loginResponse = await page.request.post('/api/auth/login/', {
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken || '',
    },
    data: { username, password },
  });

  expect(loginResponse.ok(), `[matrix][auth] login failed for user=${username}`).toBeTruthy();

  const meResponse = await page.request.get('/api/me/');
  expect(meResponse.ok(), `[matrix][auth] /api/me failed after login for user=${username}`).toBeTruthy();
}

async function runCase(page: Page, matrixCase: FunctionalMatrixCase): Promise<void> {
  const successfulEndpoints = new Set<string>();

  page.on('response', (response) => {
    const url = response.url();
    for (const endpoint of matrixCase.endpoints) {
      if (url.includes(endpoint) && response.status() < 500) {
        successfulEndpoints.add(endpoint);
      }
    }
  });

  await loginByApi(page, matrixCase.user.username, matrixCase.user.password);
  await page.goto(matrixCase.route);
  await page.waitForLoadState('networkidle');

  for (const endpoint of matrixCase.endpoints) {
    await expect
      .poll(
        () => successfulEndpoints.has(endpoint),
        {
          timeout: 15000,
          message: `[matrix][route=${matrixCase.route}][endpoint=${endpoint}] endpoint nao foi chamado com status < 500`,
        }
      )
      .toBeTruthy();
  }

  for (const assertion of matrixCase.assertions) {
    const locator = page.locator(assertion.selector).first();
    await expect(
      locator,
      `[matrix][route=${matrixCase.route}][field=${assertion.field}][endpoint=${assertion.endpoint}]`
    ).toContainText(assertion.expectedText, { timeout: 15000 });
  }
}

test.describe('Checklist: Functional Contract Matrix', () => {
  for (const matrixCase of FUNCTIONAL_CRITICAL_MATRIX) {
    test(`🔴 ${matrixCase.id}`, async ({ page }) => {
      await runCase(page, matrixCase);
    });
  }
});
