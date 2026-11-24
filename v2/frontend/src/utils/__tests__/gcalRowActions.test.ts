/**
 * gcalRowActions — ações de Google Agenda por linha (página Publicar na agenda, #1656).
 *
 * Tabela exaustiva gcal_status × external_event_id × ready. Cada ação oferecida
 * precisa ter um endpoint que o backend aceita para aquele estado:
 * publicar/tentar → /publish/, atualizar → /resync-gcal/, remover → /cancel-gcal/
 * (cancel exige external_event_id).
 */
import { describe, expect, test } from 'vitest';
import {
  MOTIVO_NAO_PUBLICAVEL,
  confirmacaoDeExcluirNoGoogle,
  excluirMarcaCancelado,
  gcalRowActions,
  motivoNaoPublicavel,
  type GcalRowAction,
} from '../gcalRowActions';
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

// Virada (16/10/2026): o mesmo `motivo_nao_publicavel` do backend, para a tela não oferecer o que ele recusa.
describe('gcalRowActions — publicado fora do sistema', () => {
  test('evento no Google pela planilha não oferece ação nenhuma', () => {
    const result = gcalRowActions(
      { gcal_status: 'NONE', external_event_id: null, publicado_fora_do_sistema: true },
      { ready: true },
    );
    expect(result.actions).toEqual([]);
    expect(result.tag.label).toBe('Na agenda pela planilha');
  });
});

describe('motivoNaoPublicavel', () => {
  const agora = Date.parse('2026-10-16T12:00:00-03:00');
  const futuro = '2026-11-05T12:00:00-03:00';
  const passado = '2026-10-10T12:00:00-03:00';
  const linha = (o: Record<string, unknown>) => ({
    gcal_status: 'NONE' as GCalStatus,
    fim: futuro,
    publicado_fora_do_sistema: false,
    ...o,
  });

  test('publicar', () => {
    expect(motivoNaoPublicavel(linha({}), { agora })).toBeNull();
    expect(motivoNaoPublicavel(linha({ fim: passado }), { agora })).toBe('evento_passado');
    expect(motivoNaoPublicavel(linha({ gcal_status: 'PUBLISHED' }), { agora })).toBe('ja_publicado');
    expect(motivoNaoPublicavel(linha({ gcal_status: 'PENDING' }), { agora })).toBe('ja_publicado');
    expect(motivoNaoPublicavel(linha({ gcal_status: 'ERROR' }), { agora })).toBeNull();
    expect(motivoNaoPublicavel(linha({ publicado_fora_do_sistema: true }), { agora })).toBe(
      'publicado_fora_do_sistema',
    );
  });

  test('reenvio (Reaplicar / Reenviar)', () => {
    expect(motivoNaoPublicavel(linha({}), { agora, reenvio: true })).toBe('nao_publicado');
    expect(motivoNaoPublicavel(linha({ gcal_status: 'PUBLISHED' }), { agora, reenvio: true })).toBeNull();
    expect(motivoNaoPublicavel(linha({ gcal_status: 'PUBLISHED', fim: passado }), { agora, reenvio: true })).toBe(
      'evento_passado',
    );
  });

  // CON-09: a marca vem do servidor (`falta_numero_da_formacao`); a tela não confere o formato.
  test('evento de formação sem o Nº da formação, depois dos outros motivos', () => {
    const sem = { falta_numero_da_formacao: true };
    expect(motivoNaoPublicavel(linha(sem), { agora })).toBe('sem_numero_da_formacao');
    expect(motivoNaoPublicavel(linha({ ...sem, gcal_status: 'ERROR' }), { agora })).toBe('sem_numero_da_formacao');
    expect(motivoNaoPublicavel(linha({ ...sem, gcal_status: 'PUBLISHED' }), { agora, reenvio: true })).toBe(
      'sem_numero_da_formacao',
    );
    expect(motivoNaoPublicavel(linha({ ...sem, fim: passado }), { agora })).toBe('evento_passado');
    expect(motivoNaoPublicavel(linha({ ...sem, gcal_status: 'PUBLISHED' }), { agora })).toBe('ja_publicado');
    expect(motivoNaoPublicavel(linha(sem), { agora, reenvio: true })).toBe('nao_publicado');
    expect(motivoNaoPublicavel(linha({ falta_numero_da_formacao: false }), { agora })).toBeNull();
  });
});

// CON-08 B: "Cancelar evento" de formação (o título no Google ganha "(CANCELADO) "). O servidor diz por linha se
// o Excluir marca o título com a chave CON08_CANCELAR_NA_AGENDA ligada (`exclui_marcando_cancelado`).
describe('gcalRowActions — cancelar evento de formação', () => {
  test.each<[GCalStatus, string | null, GcalRowAction[]]>([
    ['PUBLISHED', 'asv27', ['atualizar', 'remover', 'cancelar']],
    // Sem id, nem Remover nem Cancelar (como a Pré-agenda): um Cancelar que falhasse deixaria ERROR sem id, sem refazer.
    ['PUBLISHED', null, ['atualizar']],
    ['ERROR', 'asv27', ['atualizar', 'remover', 'cancelar']],
    ['ERROR', null, ['tentar']],
    ['NONE', null, ['publicar']],
    ['PENDING', 'asv27', []],
  ])('formação %s com id=%s → %j', (gcal_status, external_event_id, actions) => {
    const result = gcalRowActions(
      { gcal_status, external_event_id, exclui_marcando_cancelado: true },
      { ready: true },
    );
    expect(result.actions).toEqual(actions);
  });

  test('sem exclui_marcando_cancelado (outro tipo, ou a chave desligada) não ganha Cancelar', () => {
    for (const exclui_marcando_cancelado of [false, undefined]) {
      const result = gcalRowActions(
        { gcal_status: 'PUBLISHED', external_event_id: 'asv27', exclui_marcando_cancelado },
        { ready: true },
      );
      expect(result.actions).toEqual(['atualizar', 'remover']);
    }
  });

  // Revisão da rodada 1 da chave: o Cancelar falhou antes do Google e a chave desligou. O servidor aceita o Tirar
  // nela (a marca sai com o evento); o Cancelar de novo, não. A linha marcada já confirmada (PUBLISHED) fica sem ação.
  test.each<[GCalStatus, string | null, string, GcalRowAction[]]>([
    ['ERROR', 'asv27', 'Erro ao cancelar', ['remover']],
    ['ERROR', null, 'Erro ao cancelar', []],
    ['PUBLISHED', 'asv27', 'Cancelado na agenda', []],
    ['PENDING', 'asv27', 'Cancelando…', []],
  ])('chave desligada: linha marcada %s com id=%s → "%s" %j', (gcal_status, external_event_id, label, actions) => {
    const result = gcalRowActions(
      { gcal_status, external_event_id, cancelado_na_agenda: true, exclui_marcando_cancelado: false },
      { ready: true },
    );
    expect(result.tag.label).toBe(label);
    expect(result.actions).toEqual(actions);
  });

  test.each<[GCalStatus, string | null, string, string, GcalRowAction[]]>([
    ['PUBLISHED', 'asv27', 'Cancelado na agenda', 'default', []],
    ['NONE', null, 'Cancelado na agenda', 'default', []],
    ['PENDING', 'asv27', 'Cancelando…', 'processing', []],
    ['ERROR', 'asv27', 'Erro ao cancelar', 'error', ['cancelar']],
    ['ERROR', null, 'Erro ao cancelar', 'error', []],
  ])('linha cancelada na agenda %s com id=%s → "%s"', (gcal_status, external_event_id, label, color, actions) => {
    const result = gcalRowActions(
      { gcal_status, external_event_id, exclui_marcando_cancelado: true, cancelado_na_agenda: true },
      { ready: true },
    );
    expect(result.tag).toEqual({ label, color });
    expect(result.actions).toEqual(actions);
  });

  test('motivoNaoPublicavel diz primeiro que foi cancelado na agenda', () => {
    expect(
      motivoNaoPublicavel(
        { gcal_status: 'ERROR', cancelado_na_agenda: true, fim: '2000-01-01T00:00:00Z', publicado_fora_do_sistema: true },
        { reenvio: true },
      ),
    ).toBe('cancelado_na_agenda');
    expect(MOTIVO_NAO_PUBLICAVEL.cancelado_na_agenda).toBe('foi cancelado na agenda');
  });

  test('confirmação de excluir evento de formação diz que ele fica no Google com (CANCELADO)', () => {
    const evento = {
      inicio: '2099-10-10T12:00:00Z',
      municipio_nome: 'Sobral',
      projeto_nome: 'Vidas Em Rede',
      gcal_status: 'PUBLISHED' as const,
      meet_link: null,
    };
    expect(confirmacaoDeExcluirNoGoogle({ ...evento, exclui_marcando_cancelado: true }).content).toBe(
      '10/10/2099 09:00 · Sobral · Vidas Em Rede. Ele sai do sistema e fica no Google Agenda com (CANCELADO) no título. Não dá para desfazer.',
    );
    expect(confirmacaoDeExcluirNoGoogle({ ...evento, exclui_marcando_cancelado: false }).content).toBe(
      '10/10/2099 09:00 · Sobral · Vidas Em Rede. Ele sai do sistema e do Google Agenda. Não dá para desfazer.',
    );
  });

  test('chave desligada: o Excluir da formação tira do Google, e o da linha já marcada segue marcando', () => {
    const evento = {
      inicio: '2099-10-10T12:00:00Z',
      municipio_nome: 'Sobral',
      projeto_nome: 'Vidas Em Rede',
      gcal_status: 'PUBLISHED' as const,
      meet_link: null,
      exclui_marcando_cancelado: false,
    };
    expect(excluirMarcaCancelado(evento)).toBe(false);
    expect(confirmacaoDeExcluirNoGoogle(evento).content).toBe(
      '10/10/2099 09:00 · Sobral · Vidas Em Rede. Ele sai do sistema e do Google Agenda. Não dá para desfazer.',
    );
    const marcada = { ...evento, cancelado_na_agenda: true };
    expect(excluirMarcaCancelado(marcada)).toBe(true);
    expect(confirmacaoDeExcluirNoGoogle(marcada).content).toBe(
      '10/10/2099 09:00 · Sobral · Vidas Em Rede. Ele sai do sistema e fica no Google Agenda com (CANCELADO) no título. Não dá para desfazer.',
    );
  });

  test('chave desligada: o Excluir da linha marcada em erro (o Cancelar não terminou) tira do Google', () => {
    const marcadaEmErro = {
      inicio: '2099-10-10T12:00:00Z',
      municipio_nome: 'Sobral',
      projeto_nome: 'Vidas Em Rede',
      gcal_status: 'ERROR' as const,
      external_event_id: 'asv27',
      meet_link: null,
      cancelado_na_agenda: true,
      exclui_marcando_cancelado: false,
    };
    expect(excluirMarcaCancelado(marcadaEmErro)).toBe(false);
    expect(confirmacaoDeExcluirNoGoogle(marcadaEmErro).content).toBe(
      '10/10/2099 09:00 · Sobral · Vidas Em Rede. Ele sai do sistema e do Google Agenda, se estiver lá. Não dá para desfazer.',
    );
    // Com a chave ligada, a mesma linha segue marcando (o Excluir põe a marca que faltou).
    expect(excluirMarcaCancelado({ ...marcadaEmErro, exclui_marcando_cancelado: true })).toBe(true);
  });

  test('formação em ERROR sem id: a confirmação não promete que o evento está no Google', () => {
    const evento = {
      inicio: '2099-10-10T12:00:00Z',
      municipio_nome: 'Sobral',
      projeto_nome: 'Vidas Em Rede',
      gcal_status: 'ERROR' as const,
      meet_link: null,
      exclui_marcando_cancelado: true,
    };
    expect(confirmacaoDeExcluirNoGoogle({ ...evento, external_event_id: null }).content).toBe(
      '10/10/2099 09:00 · Sobral · Vidas Em Rede. Ele sai do sistema e, se chegou ao Google Agenda, fica lá com (CANCELADO) no título. Não dá para desfazer.',
    );
    expect(confirmacaoDeExcluirNoGoogle({ ...evento, external_event_id: 'asv29' }).content).toBe(
      '10/10/2099 09:00 · Sobral · Vidas Em Rede. Ele sai do sistema e fica no Google Agenda com (CANCELADO) no título. Não dá para desfazer.',
    );
  });
});
