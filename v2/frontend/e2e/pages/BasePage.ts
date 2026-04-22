/**
 * Base de todos os Page Objects.
 *
 * Filosofia: POM mínimo — encapsula apenas o que se REPETE em múltiplos
 * specs. Ações one-off ficam no spec. Evita abstração prematura.
 *
 * Regras:
 * - Locators expostos como getters readonly, não funções.
 * - Ações de alto nível (ex: `criarSolicitacao(payload)`) retornam `void`
 *   ou o objeto criado via API; nunca retornar locator cru.
 * - Asserções NÃO ficam no POM (quem decide o que asserir é o spec).
 */
import type { Page, Locator } from '@playwright/test';
import { waitForRouteReady } from '../helpers/wait';

export abstract class BasePage {
  constructor(protected readonly page: Page) {}

  /** URL relativa da rota. Cada subclasse define. */
  abstract readonly path: string;

  /** Navega até a rota e aguarda shell + overlay. */
  async goto(): Promise<void> {
    await this.page.goto(this.path);
    await waitForRouteReady(this.page);
  }

  /** Heading principal — usa role semântico. */
  get heading(): Locator {
    return this.page.getByRole('heading').first();
  }

  /** `<main>` da página (AppShell expõe role="main"). */
  get main(): Locator {
    return this.page.getByRole('main');
  }
}
