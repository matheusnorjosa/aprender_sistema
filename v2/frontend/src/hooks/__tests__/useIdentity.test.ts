/**
 * Tests: useIdentity + computeIdentity (Issue #1269, RBAC 3.1).
 *
 * `useIdentity` responde "quem é o usuário" (organograma: setor/função) e dados
 * de display (displayName, badge). É DISPLAY-ONLY — não decide autorização (isso
 * é `useCapabilities`, derivado de policies). Co-existe com `usePermissions`
 * (legacy) até a migração de callers (ondas 3.2/3.3).
 */
import { describe, test, expect } from 'vitest';
import { computeIdentity } from '../useIdentity';
import type { CurrentUser } from '../../types';

function makeUser(over: Partial<CurrentUser> = {}): CurrentUser {
  return {
    id: 1,
    username: 'user',
    email: 'user@test.com',
    first_name: 'First',
    last_name: 'Last',
    name: 'Fulano de Tal',
    groups: [],
    setores: [],
    funcoes: [],
    is_superuser: false,
    is_superintendencia: false,
    can_approve_super: false,
    permissions: [],
    ...over,
  };
}

describe('computeIdentity (Issue #1269)', () => {
  test('null user → identidade anônima', () => {
    const id = computeIdentity(null);
    expect(id.isAdmin).toBe(false);
    expect(id.isCoordenador).toBe(false);
    expect(id.isFormador).toBe(false);
    expect(id.isGerente).toBe(false);
    expect(id.inSuperintendencia).toBe(false);
    expect(id.inDAT).toBe(false);
    expect(id.inControle).toBe(false);
    expect(id.inDiretoria).toBe(false);
    expect(id.displayName).toBe('');
    expect(id.badge).toBe('Usuário');
  });

  test('superuser → isAdmin + badge Admin', () => {
    const id = computeIdentity(makeUser({ is_superuser: true, name: 'Super' }));
    expect(id.isAdmin).toBe(true);
    expect(id.displayName).toBe('Super');
    expect(id.badge).toBe('Admin');
  });

  test('Coordenador (Vidas) → isCoordenador + badge Coordenador', () => {
    const id = computeIdentity(makeUser({ funcoes: ['Coordenador'], setores: ['Vidas'], name: 'Coord' }));
    expect(id.isCoordenador).toBe(true);
    expect(id.isFormador).toBe(false);
    expect(id.badge).toBe('Coordenador');
    expect(id.displayName).toBe('Coord');
  });

  test('Apoio de Coordenação → isCoordenador + badge Apoio de Coordenação', () => {
    const id = computeIdentity(makeUser({ funcoes: ['Apoio de Coordenação'] }));
    expect(id.isCoordenador).toBe(true);
    expect(id.badge).toBe('Apoio de Coordenação');
  });

  test('Formador → isFormador + badge Formador', () => {
    const id = computeIdentity(makeUser({ funcoes: ['Formador'] }));
    expect(id.isFormador).toBe(true);
    expect(id.badge).toBe('Formador');
  });

  test('Gerente da Superintendência → isGerente + inSuperintendencia + badge Gerente', () => {
    const id = computeIdentity(makeUser({ funcoes: ['Gerente'], setores: ['Superintendência'] }));
    expect(id.isGerente).toBe(true);
    expect(id.inSuperintendencia).toBe(true);
    expect(id.badge).toBe('Gerente');
  });

  test('DAT sem função → inDAT + badge do setor (fallback)', () => {
    const id = computeIdentity(makeUser({ setores: ['DAT'] }));
    expect(id.inDAT).toBe(true);
    expect(id.badge).toBe('DAT');
  });

  test('displayName cai para username quando name vazio', () => {
    const id = computeIdentity(makeUser({ name: '', username: 'jdoe' }));
    expect(id.displayName).toBe('jdoe');
  });
});
