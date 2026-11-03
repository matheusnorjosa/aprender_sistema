/**
 * Seam 3 (import v15): exibir o NOME do participante, não só o e-mail.
 * Convidados importados "que saíram" não têm FK — o nome fica em `guest_nome`.
 * Cadeia: usuario (nome) → guest_nome → guest_email → email.
 */
import { describe, it, expect } from 'vitest';
import {
  participantLabel,
  formadoresLabel,
  formadoresNomes,
  extrasLabels,
  extrasNomes,
  coordenadoresTexto,
} from '../participants';
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

  // S5: o login é o CPF e o e-mail pode ser o de reserva `<cpf>@placeholder.local`.
  it('usuário sem first/last → "Usuario #id", nunca o login nem o e-mail', () => {
    const semNome = usuario({ first_name: '', last_name: '', username: '52998224725', email: '52998224725@placeholder.local' });
    expect(participantLabel({ ...base, usuario: semNome, email: semNome.email })).toBe('Usuario #1');
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

// Vários coordenadores (03/11/2026): os extras são as participações COORD_ACOMPANHA. A de papel
// COORDENADOR é quem criou, não um extra.
describe('extrasLabels (Participation[])', () => {
  it('só COORD_ACOMPANHA, por nome; descarta vazio e outros papéis (inclusive COORDENADOR)', () => {
    const parts: Participation[] = [
      { ...base, role: 'COORD_ACOMPANHA', usuario: usuario({ first_name: 'Beto', last_name: 'Extra' }) },
      { ...base, role: 'COORD_ACOMPANHA', guest_nome: 'Caio Saiu' },
      { ...base, role: 'COORD_ACOMPANHA' }, // sem nome nenhum → fora
      { ...base, role: 'COORDENADOR', usuario: usuario({ first_name: 'Quem', last_name: 'Criou' }) },
      { ...base, role: 'FORMADOR', usuario: usuario() },
    ];
    expect(extrasLabels(parts)).toEqual(['Beto Extra', 'Caio Saiu']);
  });

  it('lista vazia/undefined → []', () => {
    expect(extrasLabels(undefined)).toEqual([]);
    expect(extrasLabels([])).toEqual([]);
  });
});

describe('extrasNomes (shape pré-resolvido [{role, nome}])', () => {
  it('só COORD_ACOMPANHA; descarta vazio e outros papéis', () => {
    expect(
      extrasNomes([
        { role: 'COORD_ACOMPANHA', nome: 'Beto Extra' },
        { role: 'COORD_ACOMPANHA', nome: '' },
        { role: 'COORDENADOR', nome: 'Quem Criou' },
        { role: 'FORMADOR', nome: 'Ana Formadora' },
      ]),
    ).toEqual(['Beto Extra']);
    expect(extrasNomes(undefined)).toEqual([]);
  });
});

describe('coordenadoresTexto', () => {
  it('responsável primeiro, depois os extras, separados por vírgula', () => {
    expect(coordenadoresTexto('Rita Resp', ['Beto Extra', 'Caio Extra'])).toBe('Rita Resp, Beto Extra, Caio Extra');
  });

  it('sem extras → só o responsável', () => {
    expect(coordenadoresTexto('Rita Resp', [])).toBe('Rita Resp');
  });

  it('não repete nome (extra igual ao responsável ou repetido) e descarta vazios', () => {
    expect(coordenadoresTexto('Rita Resp', ['Rita Resp', ' ', 'Beto Extra', 'Beto Extra'])).toBe('Rita Resp, Beto Extra');
  });

  it('sem responsável → só os extras; nada → string vazia', () => {
    expect(coordenadoresTexto(null, ['Beto Extra'])).toBe('Beto Extra');
    expect(coordenadoresTexto(undefined, [])).toBe('');
  });
});
