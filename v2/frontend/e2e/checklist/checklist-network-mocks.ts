import { Page } from '@playwright/test';

export interface ChecklistAuthBootstrapOptions {
  mockCsrf?: boolean;
  mockMeUnauthorized?: boolean;
}

export async function mockChecklistAuthBootstrap(
  page: Page,
  options: ChecklistAuthBootstrapOptions = {}
): Promise<void> {
  const {
    mockCsrf = true,
    mockMeUnauthorized = true,
  } = options;

  if (mockCsrf) {
    await page.route(/\/api\/csrf\/?(\?.*)?$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ csrfToken: 'checklist-test-csrf-token' }),
      });
    });
  }

  if (mockMeUnauthorized) {
    await page.route(/\/api\/me\/?(\?.*)?$/, async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'As credenciais de autenticação não foram fornecidas.',
        }),
      });
    });
  }
}
