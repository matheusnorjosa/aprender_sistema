/**
 * #2071: o Salvar do formulário de Usuários mexe só no que o formulário mudou.
 *
 * - Gerência e função são obrigatórias só ao CRIAR: na edição, a pessoa pode não ter
 *   gerência (Controle) nem função (DAT).
 * - A prévia "Permissões efetivas" espelha o backend (`_apply_lotacao`): os grupos atuais
 *   que não são FUNÇÃO ficam; as funções vêm do form; o grupo de setor da gerência só
 *   entra/sai quando a gerência muda; a gerência aprovadora não dá grupo de setor.
 */

import { describe, expect, test } from 'vitest';

import { GERENCIA_APROVADORA_NOME, gruposAposSalvar, lotacaoObrigatoria } from '../usuario_form_helpers';

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
const g1 = { id: 1, nome: GERENCIA_APROVADORA_NOME, setor_canonico: 'Superintendência' };

function nomes(args: Parameters<typeof gruposAposSalvar>[0]): string[] {
  return gruposAposSalvar(args).map((g) => g.name).sort();
}

describe('lotacaoObrigatoria (#2071)', () => {
  test('superuser criando: obrigatória', () => {
    expect(lotacaoObrigatoria({ currentIsSuperuser: true, isEditing: false })).toBe(true);
  });

  test('superuser editando: opcional (Controle não tem gerência; DAT não tem função)', () => {
    expect(lotacaoObrigatoria({ currentIsSuperuser: true, isEditing: true })).toBe(false);
  });

  test('quem não é superuser: nunca (o campo fica desabilitado)', () => {
    expect(lotacaoObrigatoria({ currentIsSuperuser: false, isEditing: false })).toBe(false);
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
});
