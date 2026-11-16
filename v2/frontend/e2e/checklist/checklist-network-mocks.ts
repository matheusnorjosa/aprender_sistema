import { Page } from '@playwright/test';

// ⚠️ Com o service worker do app (/sw.js) ligado, as chamadas a /api/ feitas depois que ele assume a
// página (o /api/me inclusive) passam por ele e não pelo page.route: o mock é ignorado. Quem precisa
// que o mock vença usa `test.use({ serviceWorkers: 'block' })`; sem o bloqueio, a tela anônima vem do
// 403 real do backend (FER-57).

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
  username: '12345678900',
  email: 'pessoa.teste@example.invalid',
  first_name: 'Pessoa',
  last_name: 'Teste',
  name: 'Pessoa Teste',
  cpf: '12345678900',
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
