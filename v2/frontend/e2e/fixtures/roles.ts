/**
 * Fixtures de autenticação multi-role.
 *
 * O projeto tem 4 funções × 13 setores via Django Groups, então um
 * storageState único (legado) é insuficiente. Esta fixture permite o spec
 * declarar o papel que precisa:
 *
 *   test('coord Vidas vê apenas as próprias', async ({ authedPage }) => {
 *     const page = await authedPage('coord_vidas');
 *     await page.goto('/solicitacoes/minhas');
 *     // ...
 *   });
 *
 * Cada role tem storageState serializado em `e2e/.auth/{role}.json` pelo
 * `auth.setup.ts` (multi-role setup). Dentro do mesmo worker, contextos
 * são reutilizados para múltiplas páginas do mesmo role.
 */
import { BrowserContext, Page, test as base } from '@playwright/test';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Roles suportadas. Cada uma mapeia para um usuário em `seed_e2e_users.py`
 * e tem um `storageState` dedicado após `auth.setup.ts`.
 */
export const E2E_ROLES = [
  'coord_e2e', // legacy, mantido para back-compat
  'super_e2e', // legacy
  'controle_e2e', // legacy
  'formador_e2e', // legacy
  'coord_vidas',
  'coord_fluir',
  'coord_acerta',
  'gerente_vidas',
  'super_geral',
  'formador_vidas',
  'formador_fluir',
  'dat_e2e', // DAT puro — jornada J18
] as const;

export type E2eRole = (typeof E2E_ROLES)[number];

export const ROLE_CREDENTIALS: Record<E2eRole, { username: string; password: string }> = {
  coord_e2e: { username: 'coord_e2e@test.com', password: 'testpass123' },
  super_e2e: { username: 'super_e2e@test.com', password: 'testpass123' },
  controle_e2e: { username: 'controle_e2e@test.com', password: 'testpass123' },
  formador_e2e: { username: 'formador_e2e@test.com', password: 'testpass123' },
  coord_vidas: { username: 'coord_vidas@test.com', password: 'testpass123' },
  coord_fluir: { username: 'coord_fluir@test.com', password: 'testpass123' },
  coord_acerta: { username: 'coord_acerta@test.com', password: 'testpass123' },
  gerente_vidas: { username: 'gerente_vidas@test.com', password: 'testpass123' },
  super_geral: { username: 'super_geral@test.com', password: 'testpass123' },
  formador_vidas: { username: 'formador_vidas@test.com', password: 'testpass123' },
  formador_fluir: { username: 'formador_fluir@test.com', password: 'testpass123' },
  dat_e2e: { username: 'dat_e2e@test.com', password: 'testpass123' },
};

/**
 * Caminho do storageState para uma role. Usado pelo `auth.setup.ts` ao
 * salvar e por `authedPage()` ao carregar.
 */
export function storageStatePath(role: E2eRole): string {
  return join(__dirname, '..', '.auth', `${role}.json`);
}

export interface RoleFixtures {
  /** Retorna uma `Page` autenticada como a role especificada. */
  authedPage: (role: E2eRole) => Promise<Page>;
}

/**
 * Extensão do `test` do Playwright adicionando `authedPage`.
 *
 * Reutiliza contextos entre páginas do mesmo role dentro do worker para
 * não pagar o custo de abrir browser context N vezes.
 */
export const test = base.extend<RoleFixtures>({
  authedPage: async ({ browser }, use) => {
    const contexts = new Map<E2eRole, BrowserContext>();

    const getPage = async (role: E2eRole): Promise<Page> => {
      let ctx = contexts.get(role);
      if (!ctx) {
        ctx = await browser.newContext({ storageState: storageStatePath(role) });
        contexts.set(role, ctx);
      }
      return ctx.newPage();
    };

    await use(getPage);

    // Teardown — fecha todos os contextos criados neste teste
    for (const ctx of contexts.values()) {
      await ctx.close();
    }
  },
});

export { expect } from '@playwright/test';
