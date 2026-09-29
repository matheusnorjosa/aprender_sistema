/**
 * #2071: o Salvar do formulário de Usuários mexe só no que o formulário mudou.
 *
 * - Ao CRIAR, gerência e função são obrigatórias. Na edição, a função é opcional (o DAT não
 *   tem) e a gerência só é obrigatória para quem já tem lotação (o Controle não tem; e limpar
 *   a gerência de uma aprovadora não pode ser um jeito de salvar sem revogar).
 * - A prévia "Permissões efetivas" espelha o backend (`_apply_lotacao`): os grupos atuais
 *   que não são FUNÇÃO ficam; as funções vêm do form; o grupo de setor da gerência só
 *   entra/sai quando a gerência muda; setor de par aprovador (Superintendência, Controle)
 *   não vira grupo.
 */

import { describe, expect, test } from 'vitest';

import { gruposAposSalvar, lotacaoObrigatoria } from '../usuario_form_helpers';

const G = {
  formador: { id: 1, name: 'Formador' },
  gerente: { id: 2, name: 'Gerente' },
  controle: { id: 3, name: 'Controle' },
  asst: { id: 4, name: 'Assistente Administrativo' },
  vidas: { id: 5, name: 'Vidas' },
  fluir: { id: 6, name: 'Fluir' },
  sup: { id: 7, name: 'Superintendência' },
  prog: { id: 8, name: 'Programador' },
};
const grupos = Object.values(G);
const funcoes = new Set(['Formador', 'Coordenador', 'Gerente', 'Apoio de Coordenação', 'Assistente Administrativo']);
const vidas = { id: 2, nome: 'GERENCIA 2', setor_canonico: 'Vidas' };
const fluir = { id: 3, nome: 'GERENCIA 3', setor_canonico: 'Fluir' };
const g1 = { id: 1, nome: 'SUPERINTENDENCIA', setor_canonico: 'Superintendência' };
const gControle = { id: 9, nome: 'G CONTROLE', setor_canonico: 'Controle' };

function nomes(args: Parameters<typeof gruposAposSalvar>[0]): string[] {
  return gruposAposSalvar(args).map((g) => g.name).sort();
}

describe('lotacaoObrigatoria (#2071)', () => {
  test('superuser criando: gerência e função obrigatórias', () => {
    expect(lotacaoObrigatoria({ currentIsSuperuser: true, isEditing: false, temLotacao: false })).toEqual({
      gerencia: true,
      funcao: true,
    });
  });

  test('superuser editando quem não tem lotação (Controle, DAT): nada obrigatório', () => {
    expect(lotacaoObrigatoria({ currentIsSuperuser: true, isEditing: true, temLotacao: false })).toEqual({
      gerencia: false,
      funcao: false,
    });
  });

  test('superuser editando quem tem lotação: a gerência não pode ser limpa', () => {
    expect(lotacaoObrigatoria({ currentIsSuperuser: true, isEditing: true, temLotacao: true })).toEqual({
      gerencia: true,
      funcao: false,
    });
  });

  test('quem não é superuser: nunca (os campos ficam desabilitados)', () => {
    expect(lotacaoObrigatoria({ currentIsSuperuser: false, isEditing: false, temLotacao: true })).toEqual({
      gerencia: false,
      funcao: false,
    });
  });
});

describe('gruposAposSalvar (#2071)', () => {
  test('pessoa do Controle sem gerência: o grupo Controle continua', () => {
    expect(
      nomes({ grupos, idsAtuais: [3, 4], funcoes, funcaoIds: [4], gerencia: undefined, gerenciaAnterior: undefined }),
    ).toEqual(['Assistente Administrativo', 'Controle']);
  });

  test('funções são substituídas e o grupo de permissão fica', () => {
    expect(
      nomes({ grupos, idsAtuais: [1, 8], funcoes, funcaoIds: [2], gerencia: undefined, gerenciaAnterior: undefined }),
    ).toEqual(['Gerente', 'Programador']);
  });

  test('mesma gerência: não acrescenta o grupo de setor', () => {
    expect(nomes({ grupos, idsAtuais: [1], funcoes, funcaoIds: [1], gerencia: vidas, gerenciaAnterior: vidas })).toEqual([
      'Formador',
    ]);
  });

  test('troca de gerência troca o grupo de setor', () => {
    expect(
      nomes({ grupos, idsAtuais: [1, 6], funcoes, funcaoIds: [1], gerencia: vidas, gerenciaAnterior: fluir }),
    ).toEqual(['Formador', 'Vidas']);
  });

  test('primeira lotação acrescenta o grupo de setor', () => {
    expect(nomes({ grupos, idsAtuais: [], funcoes, funcaoIds: [1], gerencia: vidas, gerenciaAnterior: undefined })).toEqual(
      ['Formador', 'Vidas'],
    );
  });

  test('a gerência aprovadora não dá o grupo Superintendência', () => {
    expect(nomes({ grupos, idsAtuais: [], funcoes, funcaoIds: [2], gerencia: g1, gerenciaAnterior: undefined })).toEqual([
      'Gerente',
    ]);
  });

  test('gerência com setor Controle não dá o grupo Controle', () => {
    expect(
      nomes({ grupos, idsAtuais: [], funcoes, funcaoIds: [4], gerencia: gControle, gerenciaAnterior: undefined }),
    ).toEqual(['Assistente Administrativo']);
  });
});
