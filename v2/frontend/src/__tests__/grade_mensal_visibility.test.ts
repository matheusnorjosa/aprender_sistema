/**
 * Tests de visibilidade da Grade Mensal (D8 — 2026-04-28).
 *
 * Valida o predicate exato usado em `AppSidebar.tsx` e `AppRoutes.tsx`:
 *
 *     access.can('view_all_availability') || canDisponibilidade
 *
 * sem renderizar componentes (helper extraction pattern documentado em
 * `feedback_stabilization_pos_programa_pattern.md` — modal/router antd
 * gigante mockear é flaky; testar a regra pura do predicate é suficiente).
 *
 * Regra D8:
 *   ALLOW: Superuser, Controle, Gerente, Coordenador, Apoio
 *   DENY:  DAT, Diretoria, Formador, user sem nada
 *
 * Quem é ALLOW pelo `view_all_availability` (Controle/Gerente) basta a policy.
 * Quem é ALLOW pelo `canDisponibilidade` (Coord/Apoio) entra pelo segundo termo
 * do OR e o backend valida scope via `EquipeGerencia` em runtime.
 */

import { describe, test, expect } from 'vitest';
import { computePermissions } from '../hooks/usePermissions';
import { computeAccess } from '../hooks/useCanAccess';

function makeUser(overrides = {}) {
  return {
    id: 1,
    username: 'testuser',
    email: 'test@test.com',
    first_name: 'Test',
    last_name: 'User',
    name: 'Test User',
    groups: [],
    setores: [],
    funcoes: [],
    is_superuser: false,
    is_superintendencia: false,
    can_approve_super: false,
    permissions: [],
    ...overrides,
  };
}

/**
 * Replica o predicate usado em AppSidebar.tsx:363 e AppRoutes.tsx:121:
 *     access.can('view_all_availability') || canDisponibilidade
 */
function shouldShowGradeMensal(user: ReturnType<typeof makeUser>, policies: readonly string[]): boolean {
  const perms = computePermissions(user);
  const access = computeAccess(policies, {});
  return access.can('view_all_availability') || perms.canDisponibilidade;
}

describe('Grade Mensal visibility (D8 — 2026-04-28)', () => {
  describe('ALLOW', () => {
    test('Superuser', () => {
      // Superuser bypassa policies no backend; useCanAccess recebe lista vazia
      // mas computePermissions já dá canDisponibilidade=true via is_superuser.
      expect(shouldShowGradeMensal(makeUser({ is_superuser: true }), [])).toBe(true);
    });

    test('Controle (via view_all_availability)', () => {
      // Backend atribui `view_all_availability` ao grupo Controle no seed 0078.
      // Frontend recebe a policy via GET /api/me/policies/.
      expect(
        shouldShowGradeMensal(makeUser({ setores: ['Controle'] }), ['view_all_availability']),
      ).toBe(true);
    });

    test('Gerente (via view_all_availability)', () => {
      expect(
        shouldShowGradeMensal(makeUser({ funcoes: ['Gerente'] }), ['view_all_availability']),
      ).toBe(true);
    });

    test('Coordenador (canDisponibilidade — scoped via EquipeGerencia em runtime)', () => {
      // Coord não tem `view_all_availability` no seed; entra pelo predicate
      // canDisponibilidade. Backend valida EquipeGerencia ativo em runtime.
      expect(
        shouldShowGradeMensal(makeUser({ funcoes: ['Coordenador'], setores: ['Vidas'] }), []),
      ).toBe(true);
    });

    test('Apoio de Coordenação (canDisponibilidade — scoped via EquipeGerencia em runtime)', () => {
      expect(
        shouldShowGradeMensal(makeUser({ funcoes: ['Apoio de Coordenação'], setores: ['Vidas'] }), []),
      ).toBe(true);
    });
  });

  describe('DENY', () => {
    test('Formador (caso especial — só Meus Eventos + Bloqueios)', () => {
      expect(shouldShowGradeMensal(makeUser({ funcoes: ['Formador'] }), [])).toBe(false);
    });

    test('DAT (não consulta disponibilidade — D8)', () => {
      expect(shouldShowGradeMensal(makeUser({ setores: ['DAT'] }), [])).toBe(false);
    });

    test('Diretoria (decisão executiva, não consulta operacional — D8)', () => {
      expect(shouldShowGradeMensal(makeUser({ setores: ['Diretoria'] }), [])).toBe(false);
    });

    test('Usuário sem setor/função', () => {
      expect(shouldShowGradeMensal(makeUser(), [])).toBe(false);
    });

    test('Usuário só com setor "Vidas" sem função', () => {
      expect(shouldShowGradeMensal(makeUser({ setores: ['Vidas'] }), [])).toBe(false);
    });
  });
});
