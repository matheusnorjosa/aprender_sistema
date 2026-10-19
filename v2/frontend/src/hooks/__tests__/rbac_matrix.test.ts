/**
 * RBAC Living Matrix — frontend (Onda 3, 2026-04-27; PR 7 das permissões, 15/10/2026).
 *
 * Espelha `apps/core/rbac/matrix.py`: para cada um dos 10 atores, as policies que o backend
 * entrega em `GET /api/me/policies/` (`src/test/atoresRbac.ts`, medidas no backend) e as
 * capabilities que o front deriva delas (`computeCapabilities`, a fonte do `useAcesso`).
 *
 * Antes do PR 7 esta matriz misturava policies e flags de organograma (`useCanAccess` +
 * `usePermissions`); agora é só policy. Falha indica drift entre seed/policies e UI.
 */
import { describe, expect, test } from 'vitest';

import { ATORES_RBAC, type NomeDoAtor } from '../../test/atoresRbac';
import { computeCapabilities, type Capabilities } from '../useCapabilities';

const FLAGS = [
  'canAccessApprovals',
  'canAccessAvailabilityBlocks',
  'canAccessMonthlyAvailability',
  'canAccessTravel',
  'canCreateSolicitation',
  'canViewComprasDashboard',
  'canViewComprasStats',
  'canExecuteRestrictedOperations',
  'canCreateSolicitationWithoutPurchase',
] as const satisfies readonly (keyof Capabilities)[];

type Flag = (typeof FLAGS)[number];

/** Flags verdadeiras por ator (as ausentes são false). */
const ESPERADO: Record<NomeDoAtor, readonly Flag[]> = {
  Superuser: FLAGS,
  // PR 10: o DAT é o administrador operacional (pacote final): aprova, cria, exclui, sem a compra.
  DAT: FLAGS,
  // PR 12a: vínculo EQUIPE na gerência CONTROLE; o pacote aprova (D1 de 06/10).
  Controle: [
    'canAccessApprovals',
    'canAccessAvailabilityBlocks',
    'canAccessMonthlyAvailability',
    'canAccessTravel',
    'canViewComprasStats',
  ],
  Diretoria: ['canViewComprasDashboard'],
  // PR 10: o grupo Superintendência perdeu `execute_restricted_operations` (migration 0126).
  'Gerente da Superintendência': [
    'canAccessApprovals',
    'canAccessAvailabilityBlocks',
    'canAccessMonthlyAvailability',
    'canAccessTravel',
    'canCreateSolicitation',
  ],
  'Gerente pedagógico (Vidas)': [
    'canAccessAvailabilityBlocks',
    'canAccessMonthlyAvailability',
    'canAccessTravel',
    'canCreateSolicitation',
  ],
  Coordenador: ['canAccessAvailabilityBlocks', 'canAccessMonthlyAvailability', 'canAccessTravel', 'canCreateSolicitation'],
  'Apoio de Coordenação': [
    'canAccessAvailabilityBlocks',
    'canAccessMonthlyAvailability',
    'canAccessTravel',
    'canCreateSolicitation',
  ],
  // RD-02/03: só o próprio bloqueio.
  Formador: ['canAccessAvailabilityBlocks'],
  'Assistente Administrativo Controle': [
    'canAccessApprovals',
    'canAccessAvailabilityBlocks',
    'canAccessMonthlyAvailability',
    'canAccessTravel',
    'canViewComprasStats',
  ],
};

describe('RBAC Living Matrix (frontend)', () => {
  test.each(ATORES_RBAC)('$ator: capabilities derivadas das policies batem com a matriz', ({ ator, policies }) => {
    const caps = computeCapabilities(policies);
    const verdadeiras = FLAGS.filter((f) => caps[f]);
    expect(verdadeiras, `Mismatch para ${ator}: atualize a matriz ou verifique o seed/policies`).toEqual(
      FLAGS.filter((f) => ESPERADO[ator].includes(f)),
    );
  });

  test('todos os atores estão cobertos (sanity)', () => {
    expect(ATORES_RBAC.map((a) => a.ator).sort()).toEqual(Object.keys(ESPERADO).sort());
  });
});
