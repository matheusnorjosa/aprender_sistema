/**
 * Tests do comportamento CPF na edição de usuário (Bug 3 fix, 2026-04-27).
 *
 * Cenário:
 * - CPF é write-only no serializer backend (LGPD compliance) — API nunca
 *   retorna CPF raw, apenas `cpf_masked`.
 * - No edit, o input deve mostrar `cpf_masked` (visual), NÃO ser obrigatório,
 *   e exigir clique em "Alterar CPF" para liberar nova entrada.
 * - Submit sem alterar CPF deve omitir `cpf` do payload (backend mantém atual).
 * - Submit após "Alterar CPF" + novo valor deve enviar `cpf` no payload.
 *
 * Foco: helper puro `buildUsuarioPayload` (testável sem render do form).
 */

import { describe, expect, test } from 'vitest';

import { buildUsuarioPayload, type UsuarioFormValues } from '../usuario_form_helpers';


function makeValues(overrides: Partial<UsuarioFormValues> = {}): UsuarioFormValues {
  return {
    username: 'fabiana.veras',
    email: 'fabiana@example.com',
    first_name: 'Fabiana',
    last_name: 'Veras',
    telefone: '85999991111',
    cargo: 'Apoio de Coordenação',
    is_active: true,
    is_superuser: false,
    setor_ids: [1],
    funcao_ids: [2],
    ...overrides,
  };
}


describe('buildUsuarioPayload — CPF write-only LGPD (Bug 3 fix)', () => {
  describe('Modo CREATE (isEditing=false, cpfEditUnlocked=true)', () => {
    test('cpf preenchido → enviado no payload', () => {
      const values = makeValues({ cpf: '12345678901' });
      const payload = buildUsuarioPayload(values, {
        isEditing: false,
        cpfEditUnlocked: true,
        currentIsSuperuser: true,
      });
      expect(payload.cpf).toBe('12345678901');
      expect(payload.username).toBe('fabiana.veras');
      expect(payload.group_ids).toEqual([1, 2]);
    });

    test('cpf vazio → não enviado (defesa em profundidade — schema já marca required)', () => {
      const values = makeValues({ cpf: '' });
      const payload = buildUsuarioPayload(values, {
        isEditing: false,
        cpfEditUnlocked: true,
        currentIsSuperuser: true,
      });
      expect(payload).not.toHaveProperty('cpf');
    });
  });

  describe('Modo EDIT + LOCKED (isEditing=true, cpfEditUnlocked=false)', () => {
    test('cpf locked: payload NUNCA inclui cpf (backend mantém atual)', () => {
      const values = makeValues({ cpf: undefined });  // form não captura porque input disabled
      const payload = buildUsuarioPayload(values, {
        isEditing: true,
        cpfEditUnlocked: false,
        currentIsSuperuser: true,
      });
      expect(payload).not.toHaveProperty('cpf');
      // outros campos preservados
      expect(payload.username).toBe('fabiana.veras');
      expect(payload.telefone).toBe('85999991111');
    });

    test('cpf locked + valor "vazado" no values → ainda assim NÃO inclui (defesa)', () => {
      // Mesmo se algum bug fizer o form capturar valor com CPF locked,
      // o helper protege omitindo. Defesa em profundidade.
      const values = makeValues({ cpf: '12345678901' });
      const payload = buildUsuarioPayload(values, {
        isEditing: true,
        cpfEditUnlocked: false,  // ← locked
        currentIsSuperuser: true,
      });
      expect(payload).not.toHaveProperty('cpf');
    });
  });

  describe('Modo EDIT + UNLOCKED (isEditing=true, cpfEditUnlocked=true)', () => {
    test('user clicou "Alterar CPF" + digitou novo → cpf novo enviado', () => {
      const values = makeValues({ cpf: '98765432100' });
      const payload = buildUsuarioPayload(values, {
        isEditing: true,
        cpfEditUnlocked: true,
        currentIsSuperuser: true,
      });
      expect(payload.cpf).toBe('98765432100');
    });

    test('user clicou "Alterar CPF" mas não digitou → omitido (não substitui por vazio)', () => {
      const values = makeValues({ cpf: '' });
      const payload = buildUsuarioPayload(values, {
        isEditing: true,
        cpfEditUnlocked: true,
        currentIsSuperuser: true,
      });
      expect(payload).not.toHaveProperty('cpf');
    });
  });

  describe('is_superuser visibility (regra ortogonal)', () => {
    test('currentIsSuperuser=true → is_superuser presente no payload', () => {
      const values = makeValues({ is_superuser: true });
      const payload = buildUsuarioPayload(values, {
        isEditing: true,
        cpfEditUnlocked: false,
        currentIsSuperuser: true,
      });
      expect(payload.is_superuser).toBe(true);
    });

    test('currentIsSuperuser=false → is_superuser OMITIDO (não-super não pode mudar)', () => {
      const values = makeValues({ is_superuser: true });  // tentativa de escalation
      const payload = buildUsuarioPayload(values, {
        isEditing: true,
        cpfEditUnlocked: false,
        currentIsSuperuser: false,  // ← user comum
      });
      expect(payload).not.toHaveProperty('is_superuser');
    });
  });

  describe('group_ids consolida setor_ids + funcao_ids', () => {
    test('setor_ids + funcao_ids agregados em group_ids', () => {
      const values = makeValues({ setor_ids: [10, 20], funcao_ids: [30] });
      const payload = buildUsuarioPayload(values, {
        isEditing: false,
        cpfEditUnlocked: true,
        currentIsSuperuser: true,
      });
      expect(payload.group_ids).toEqual([10, 20, 30]);
      expect(payload).not.toHaveProperty('setor_ids');
      expect(payload).not.toHaveProperty('funcao_ids');
    });
  });
});
