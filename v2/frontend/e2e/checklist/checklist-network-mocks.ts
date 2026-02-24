import { Page } from '@playwright/test';

export async function mockChecklistAuthBootstrap(page: Page): Promise<void> {
  await page.route(/\/api\/csrf\/?(\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ csrfToken: 'checklist-test-csrf-token' }),
    });
  });

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
