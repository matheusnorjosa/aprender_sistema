/**
 * gcalRowActions — ações de Google Agenda por linha (página Publicar na agenda, #1656).
 *
 * Tabela exaustiva gcal_status × external_event_id × ready. Cada ação oferecida
 * precisa ter um endpoint que o backend aceita para aquele estado:
 * publicar/tentar → /publish/, atualizar → /resync-gcal/, remover → /cancel-gcal/
 * (cancel exige external_event_id).
 */
import { describe, expect, test } from 'vitest';
import { gcalRowActions, type GcalRowAction } from '../gcalRowActions';
import type { GCalStatus } from '../../types';

type Case = [GCalStatus, string | null, GcalRowAction[], string];

const CASES: Case[] = [
  ['NONE', null, ['publicar'], 'Não publicado'],
  ['NONE', 'asv27', ['publicar'], 'Não publicado'],
  // Publicação em voo: nada a fazer até o worker terminar (evita reenfileirar por cima).
  ['PENDING', null, [], 'Publicando…'],
  ['PENDING', 'asv27', [], 'Publicando…'],
  ['PUBLISHED', null, ['atualizar'], 'Publicado'],
  ['PUBLISHED', 'asv27', ['atualizar', 'remover'], 'Publicado'],
  // ERROR sem id: nunca chegou ao Google → tentar de novo = publicar.
  ['ERROR', null, ['tentar'], 'Erro'],
  // ERROR com id: o evento existe no Google → atualizar ou remover.
  ['ERROR', 'asv27', ['atualizar', 'remover'], 'Erro'],
];

describe.each([true, false])('gcalRowActions — ready=%s', (ready) => {
  test.each(CASES)(
    '%s com external_event_id=%s → ações %j, tag "%s"',
    (gcal_status, external_event_id, actions, tagLabel) => {
      const result = gcalRowActions({ gcal_status, external_event_id }, { ready });
      expect(result.actions).toEqual(actions);
      expect(result.tag.label).toBe(tagLabel);
      // Sem publish_ready, as ações continuam visíveis mas todas desabilitadas.
      expect(result.disabled).toBe(!ready);
    },
  );
});

describe('gcalRowActions — cores da tag', () => {
  test('cada estado tem a cor do padrão GCal do sistema', () => {
    const color = (gcal_status: GCalStatus) =>
      gcalRowActions({ gcal_status, external_event_id: null }, { ready: true }).tag.color;
    expect(color('NONE')).toBe('default');
    expect(color('PENDING')).toBe('processing');
    expect(color('PUBLISHED')).toBe('success');
    expect(color('ERROR')).toBe('error');
  });
});
