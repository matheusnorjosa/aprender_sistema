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

/** Payload de `/api/me/` para um titular autenticado (shape de `isCurrentUserPayload`). */
export const CHECKLIST_AUTH_USER = {
  id: 42,
  username: '04944374305',
  email: 'coord@aprendereditora.com.br',
  first_name: 'Amanda',
  last_name: 'Rodrigues',
  name: 'Amanda Rodrigues',
  cpf: '04944374305',
  telefone: '(85) 90000-0000',
  cargo: 'Coordenadora',
  groups: ['Coordenador', 'Vidas'],
  setores: ['Vidas'],
  funcoes: ['Coordenador'],
  is_superuser: false,
  is_superintendencia: false,
  can_approve_super: false,
  permissions: [],
};

/**
 * Bootstrap de um usuário AUTENTICADO para os checklists (a11y de páginas logadas).
 *
 * Mocka csrf + `/api/me/` (200, titular) + `/api/me/policies/` ([]) — o suficiente para
 * o App carregar `user`/policies e renderizar rotas protegidas (ex.: /perfil). Páginas com
 * dados próprios exigem mockar seus endpoints à parte.
 */
export async function mockChecklistAuthenticated(
  page: Page,
  user: Record<string, unknown> = CHECKLIST_AUTH_USER
): Promise<void> {
  await page.route(/\/api\/csrf\/?(\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ csrfToken: 'checklist-test-csrf-token' }),
    });
  });
  await page.route(/\/api\/me\/policies\/?(\?.*)?$/, async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
  });
  await page.route(/\/api\/me\/?(\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(user),
    });
  });
}
