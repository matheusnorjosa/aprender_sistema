/**
 * Seam 3 (import v15): exibir o NOME do participante, não só o e-mail.
 * Convidados importados "que saíram" não têm FK — o nome fica em `guest_nome`.
 * Cadeia: usuario (nome) → guest_nome → guest_email → email.
 */
import { describe, it, expect } from 'vitest';
import { participantLabel, formadoresLabel, formadoresNomes } from '../participants';
import type { Participation } from '../../types/solicitacao';

const base: Participation = {
  usuario: null,
  guest_email: null,
  guest_nome: null,
  email: null,
  role: 'FORMADOR',
  ch_horas: null,
  observacao: null,
};

const usuario = (over: Partial<{ first_name: string; last_name: string; username: string; email: string }> = {}) => ({
  id: 1,
  username: 'jsilva',
  first_name: 'João',
  last_name: 'Silva',
  email: 'j@x.com',
  ...over,
});

describe('participantLabel', () => {
  it('usuário com FK → nome completo', () => {
    expect(participantLabel({ ...base, usuario: usuario() })).toBe('João Silva');
  });

  it('usuário sem first/last → username', () => {
    expect(participantLabel({ ...base, usuario: usuario({ first_name: '', last_name: '' }) })).toBe('jsilva');
  });

  it('convidado sem FK com guest_nome → nome preservado (importado que saiu)', () => {
    expect(
      participantLabel({ ...base, usuario: null, guest_nome: 'Maria Ex-Formadora', guest_email: 'maria@x.com', email: 'maria@x.com' }),
    ).toBe('Maria Ex-Formadora');
  });

  it('convidado sem guest_nome → cai no guest_email', () => {
    expect(participantLabel({ ...base, usuario: null, guest_nome: null, guest_email: 'anon@x.com', email: 'anon@x.com' })).toBe(
      'anon@x.com',
    );
  });
});

describe('formadoresLabel', () => {
  it('inclui formador-convidado por NOME (antes descartado por não ter FK)', () => {
    const parts: Participation[] = [
      { ...base, usuario: usuario() }, // João Silva (FK)
      { ...base, guest_nome: 'Ex Formador' }, // convidado por nome
      { ...base, role: 'COORDENADOR', usuario: usuario({ first_name: 'Ana', last_name: 'C' }) }, // não-formador → fora
    ];
    expect(formadoresLabel(parts)).toBe('João Silva, Ex Formador');
  });

  it('lista vazia/undefined → string vazia', () => {
    expect(formadoresLabel(undefined)).toBe('');
    expect(formadoresLabel([])).toBe('');
  });
});

// #1945: MeusEventos consome o shape pré-resolvido [{role, nome}] do MeEventSerializer.
describe('formadoresNomes (MeusEventos — shape pré-resolvido [{role, nome}])', () => {
  it('inclui só FORMADOR, incluindo quem saiu (nome já resolvido); descarta outros papéis', () => {
    const participantes = [
      { role: 'FORMADOR', nome: 'João Silva' }, // formador com usuário
      { role: 'FORMADOR', nome: 'Maria Ex' }, // formador que saiu (guest_nome, sem FK)
      { role: 'COORDENADOR', nome: 'Ana Coord' }, // não-formador → fora
      { role: 'COORD_ACOMPANHA', nome: 'Beto Acomp' }, // não-formador → fora
      { role: 'CONVIDADO', nome: 'Caio Convidado' }, // não-formador → fora
    ];
    expect(formadoresNomes(participantes)).toBe('João Silva, Maria Ex');
  });

  it('descarta nomes vazios e trata lista vazia/undefined', () => {
    expect(formadoresNomes([{ role: 'FORMADOR', nome: '' }])).toBe('');
    expect(formadoresNomes(undefined)).toBe('');
    expect(formadoresNomes([])).toBe('');
  });
});
