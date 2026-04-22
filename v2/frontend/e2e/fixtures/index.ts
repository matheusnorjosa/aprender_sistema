/**
 * Composição pública das fixtures E2E.
 *
 * Import único para specs da matriz de jornadas:
 *
 *   import { test, expect } from '@fixtures';
 *   import { freezeTime } from '@fixtures/time';
 *   import { seedSolicitacao, createApiContext } from '@fixtures/seed';
 *   import { waitForRouteReady } from '@helpers/wait';
 *
 * A composição final ativa fixtures de role (authedPage). Conforme novas
 * fixtures forem criadas (ex: `seedContext`, `freezeTimeAt`), agregar aqui.
 */
export { test, expect, E2E_ROLES, ROLE_CREDENTIALS, storageStatePath } from './roles';
export type { E2eRole, RoleFixtures } from './roles';
export { freezeTime, unfreezeTime } from './time';
export {
  createApiContext,
  seedSolicitacao,
} from './seed';
export type {
  ApiContextOptions,
  SeedSolicitacaoInput,
  SeededSolicitacao,
} from './seed';
