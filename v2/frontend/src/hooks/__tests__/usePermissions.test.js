/**
 * Tests: usePermissions Hook (Issue #927 — Frente A)
 *
 * Coverage:
 * - Null user returns all false
 * - Superuser gets all capabilities
 * - Coordenador role flags
 * - Apoio de Coordenação maps to isCoordenador
 * - DAT sector permissions
 * - Controle sector permissions
 * - Gerente role
 * - canAcoesInternas combinations
 * - Dashboard visibility by sector
 * - canDisponibilidade inverse logic
 * - can_approve_super passthrough
 */

import { describe, test, expect } from 'vitest'
import { computePermissions } from '../usePermissions'

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
  }
}

describe('computePermissions', () => {
  test('null user returns all false', () => {
    const perms = computePermissions(null)
    expect(perms.isCoordenador).toBe(false)
    expect(perms.canControle).toBe(false)
    expect(perms.canDAT).toBe(false)
    expect(perms.canAcoesInternas).toBe(false)
    expect(perms.canDashboardsMenu).toBe(false)
    expect(perms.canDisponibilidade).toBe(false)
    expect(perms.canSeeAllSectors).toBe(false)
  })

  // Epic 3.3: SSOT para "vê todos os setores/gerências".
  // Substitui hardcodes is_superuser || is_superintendencia || groups.includes(Super) em 4+ páginas.
  describe('canSeeAllSectors', () => {
    test('superuser → true', () => {
      const perms = computePermissions(makeUser({ is_superuser: true }))
      expect(perms.canSeeAllSectors).toBe(true)
    })

    test('is_superintendencia flag (backend) → true', () => {
      const perms = computePermissions(makeUser({ is_superintendencia: true }))
      expect(perms.canSeeAllSectors).toBe(true)
    })

    test('setor Superintendência → true', () => {
      const perms = computePermissions(makeUser({ setores: ['Superintendência'] }))
      expect(perms.canSeeAllSectors).toBe(true)
    })

    test('user sem nenhum desses → false', () => {
      const perms = computePermissions(makeUser({ setores: ['Controle'], funcoes: ['Coordenador'] }))
      expect(perms.canSeeAllSectors).toBe(false)
    })
  })

  test('superuser gets all capabilities', () => {
    const perms = computePermissions(makeUser({ is_superuser: true }))
    expect(perms.canCoordenador).toBe(true)
    expect(perms.canControle).toBe(true)
    expect(perms.canDAT).toBe(true)
    expect(perms.canAcoesInternas).toBe(true)
    expect(perms.canDashboardOverview).toBe(true)
    expect(perms.canDashboardEquipe).toBe(true)
    expect(perms.canDashboardGcal).toBe(true)
    expect(perms.canDashboardCompras).toBe(true)
    expect(perms.canMapaBrasil).toBe(true)
    expect(perms.canDashboardsMenu).toBe(true)
    expect(perms.canDisponibilidade).toBe(true)
  })

  test('Coordenador role sets isCoordenador and canCoordenador', () => {
    const perms = computePermissions(makeUser({ funcoes: ['Coordenador'] }))
    expect(perms.isCoordenador).toBe(true)
    expect(perms.canCoordenador).toBe(true)
    expect(perms.canAcoesInternas).toBe(true)
  })

  test('Apoio de Coordenação maps to isCoordenador', () => {
    const perms = computePermissions(makeUser({ funcoes: ['Apoio de Coordenação'] }))
    expect(perms.isCoordenador).toBe(true)
    expect(perms.canCoordenador).toBe(true)
  })

  test('DAT sector grants canDAT, canCoordenador, canAcoesInternas', () => {
    const perms = computePermissions(makeUser({ setores: ['DAT'] }))
    expect(perms.inDAT).toBe(true)
    expect(perms.canDAT).toBe(true)
    expect(perms.canCoordenador).toBe(true)
    expect(perms.canAcoesInternas).toBe(true)
    expect(perms.canDashboardCompras).toBe(true)
  })

  test('Controle sector grants canControle (dashboards específicos cobertos abaixo)', () => {
    const perms = computePermissions(makeUser({ setores: ['Controle'] }))
    expect(perms.inControle).toBe(true)
    expect(perms.canControle).toBe(true)
    // Controle cannot access Disponibilidade
    expect(perms.canDisponibilidade).toBe(false)
  })

  test('Gerente role grants canAcoesInternas', () => {
    const perms = computePermissions(makeUser({ funcoes: ['Gerente'] }))
    expect(perms.isGerente).toBe(true)
    expect(perms.canAcoesInternas).toBe(true)
    // Gerente alone has no sector-based permissions
    expect(perms.canControle).toBe(false)
    expect(perms.canDAT).toBe(false)
  })

  test('canAcoesInternas: Coordenador without DAT/superuser', () => {
    const perms = computePermissions(makeUser({
      setores: ['Vidas'],
      funcoes: ['Coordenador'],
    }))
    expect(perms.canAcoesInternas).toBe(true)
  })

  // ============================================================================
  // Dashboards — alinhado com doc v2/docs/rbac_authorization_matrix.md §3 + D7
  //
  // Tabela canônica:
  //   - Geral:     Diretoria + super
  //   - Compras:   Diretoria + DAT + super
  //   - Equipe:    Diretoria + DAT + super
  //   - GCal:      Diretoria + DAT + Controle (operar) + super
  //   - Mapa:      Diretoria + DAT + super
  //
  // Bug 2 fix (Onda 1, C1, 2026-04-27): regras antigas tinham Controle/Gerência/
  // Superintendência indevidamente em vários dashboards. Cada caso abaixo
  // valida a tabela canônica.
  // ============================================================================

  test('Diretoria vê todos os 5 dashboards', () => {
    const perms = computePermissions(makeUser({ setores: ['Diretoria'] }))
    expect(perms.inDiretoria).toBe(true)
    expect(perms.canDashboardOverview).toBe(true)
    expect(perms.canDashboardCompras).toBe(true)
    expect(perms.canDashboardEquipe).toBe(true)
    expect(perms.canDashboardGcal).toBe(true)
    expect(perms.canMapaBrasil).toBe(true)
  })

  test('DAT vê Compras + Equipe + GCal + Mapa (NÃO vê Geral)', () => {
    const perms = computePermissions(makeUser({ setores: ['DAT'] }))
    expect(perms.inDAT).toBe(true)
    expect(perms.canDashboardOverview).toBe(false)
    expect(perms.canDashboardCompras).toBe(true)
    expect(perms.canDashboardEquipe).toBe(true)
    expect(perms.canDashboardGcal).toBe(true)
    expect(perms.canMapaBrasil).toBe(true)
  })

  test('Controle vê APENAS Dashboard GCal (operacional do calendário)', () => {
    const perms = computePermissions(makeUser({ setores: ['Controle'] }))
    expect(perms.inControle).toBe(true)
    expect(perms.canDashboardOverview).toBe(false)
    expect(perms.canDashboardCompras).toBe(false)
    expect(perms.canDashboardEquipe).toBe(false)
    expect(perms.canDashboardGcal).toBe(true)
    expect(perms.canMapaBrasil).toBe(false)
  })

  test('Superintendência NÃO vê dashboards (decisão executiva = Diretoria)', () => {
    const perms = computePermissions(makeUser({ setores: ['Superintendência'] }))
    expect(perms.inSuperintendencia).toBe(true)
    expect(perms.canDashboardOverview).toBe(false)
    expect(perms.canDashboardCompras).toBe(false)
    expect(perms.canDashboardEquipe).toBe(false)
    expect(perms.canDashboardGcal).toBe(false)
    expect(perms.canMapaBrasil).toBe(false)
    expect(perms.canDashboardsMenu).toBe(false)
  })

  test('Gerência NÃO vê dashboards', () => {
    const perms = computePermissions(makeUser({ setores: ['Gerência'] }))
    expect(perms.inGerencia).toBe(true)
    expect(perms.canDashboardOverview).toBe(false)
    expect(perms.canDashboardEquipe).toBe(false)
    expect(perms.canMapaBrasil).toBe(false)
    expect(perms.canDashboardsMenu).toBe(false)
  })

  test('Coordenador/Apoio/Formador NÃO veem nenhum dashboard', () => {
    for (const funcao of ['Coordenador', 'Apoio de Coordenação', 'Formador']) {
      const perms = computePermissions(makeUser({ setores: ['Vidas'], funcoes: [funcao] }))
      expect(perms.canDashboardOverview).toBe(false)
      expect(perms.canDashboardCompras).toBe(false)
      expect(perms.canDashboardEquipe).toBe(false)
      expect(perms.canDashboardGcal).toBe(false)
      expect(perms.canMapaBrasil).toBe(false)
      expect(perms.canDashboardsMenu).toBe(false)
    }
  })

  test('can_approve_super passthrough from user', () => {
    const perms = computePermissions(makeUser({ can_approve_super: true }))
    expect(perms.canApproveSuper).toBe(true)
  })

  test('Formador role grants canBloqueios via role flag', () => {
    const perms = computePermissions(makeUser({ funcoes: ['Formador'] }))
    expect(perms.isFormador).toBe(true)
  })

  test('canDisponibilidade is true for non-Controle users', () => {
    const perms = computePermissions(makeUser({ setores: ['Vidas'] }))
    expect(perms.canDisponibilidade).toBe(true)
  })

  test('regular user with no roles/sectors has minimal permissions', () => {
    const perms = computePermissions(makeUser())
    expect(perms.isCoordenador).toBe(false)
    expect(perms.isGerente).toBe(false)
    expect(perms.canCoordenador).toBe(false)
    expect(perms.canControle).toBe(false)
    expect(perms.canDAT).toBe(false)
    expect(perms.canAcoesInternas).toBe(false)
    expect(perms.canDashboardsMenu).toBe(false)
    // Non-Controle user can access Disponibilidade
    expect(perms.canDisponibilidade).toBe(true)
  })

  test('multiple sectors combine permissions', () => {
    const perms = computePermissions(makeUser({
      setores: ['DAT', 'Controle'],
      funcoes: ['Coordenador', 'Gerente'],
    }))
    expect(perms.canDAT).toBe(true)
    expect(perms.canControle).toBe(true)
    expect(perms.canAcoesInternas).toBe(true)
    expect(perms.isCoordenador).toBe(true)
    expect(perms.isGerente).toBe(true)
    expect(perms.canDashboardsMenu).toBe(true)
  })
})
