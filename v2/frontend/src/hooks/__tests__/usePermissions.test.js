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

  test('Controle sector grants canControle, dashboard permissions', () => {
    const perms = computePermissions(makeUser({ setores: ['Controle'] }))
    expect(perms.inControle).toBe(true)
    expect(perms.canControle).toBe(true)
    expect(perms.canDashboardEquipe).toBe(true)
    expect(perms.canDashboardGcal).toBe(true)
    expect(perms.canMapaBrasil).toBe(true)
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

  test('Superintendência sector grants dashboard overview', () => {
    const perms = computePermissions(makeUser({ setores: ['Superintendência'] }))
    expect(perms.inSuperintendencia).toBe(true)
    expect(perms.canDashboardOverview).toBe(true)
    expect(perms.canDashboardEquipe).toBe(true)
    expect(perms.canDashboardGcal).toBe(true)
    expect(perms.canDashboardsMenu).toBe(true)
  })

  test('Diretoria sector grants specific dashboards', () => {
    const perms = computePermissions(makeUser({ setores: ['Diretoria'] }))
    expect(perms.inDiretoria).toBe(true)
    expect(perms.canDashboardOverview).toBe(true)
    expect(perms.canDashboardCompras).toBe(true)
    expect(perms.canDashboardEquipe).toBe(true)
    expect(perms.canMapaBrasil).toBe(true)
  })

  test('Gerência sector grants dashboards', () => {
    const perms = computePermissions(makeUser({ setores: ['Gerência'] }))
    expect(perms.inGerencia).toBe(true)
    expect(perms.canDashboardOverview).toBe(true)
    expect(perms.canDashboardEquipe).toBe(true)
    expect(perms.canMapaBrasil).toBe(true)
  })

  test('can_approve_super passthrough from user', () => {
    const perms = computePermissions(makeUser({ can_approve_super: true }))
    expect(perms.canApproveSuper).toBe(true)
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
