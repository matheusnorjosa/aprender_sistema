/**
 * #2071: o Salvar do formulário de Usuários mexe só no que o formulário mudou.
 *
 * - Ao CRIAR, gerência e função são obrigatórias. Na edição, a função é opcional (o DAT não
 *   tem) e a gerência só é obrigatória para quem já tem lotação (o Controle não tem; e limpar
 *   a gerência de uma aprovadora não pode ser um jeito de salvar sem revogar).
 * - A prévia "Permissões efetivas" saiu da tela no lote C (06/11/2026): grupo não dá poder desde o PR 12.
 */

import { describe, expect, test } from 'vitest';

import {
  buildUsuarioPayload,
  errosDosCampos,
  funcoesProntasParaSalvar,
  lotacaoObrigatoria,
  mensagemDoErro,
  nomeDe,
} from '../usuario_form_helpers';

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

describe('mensagemDoErro (#2071)', () => {
  test('mostra o texto de validação do backend, não só "Erro de validação."', () => {
    const err = Object.assign(new Error('Erro de validação.'), {
      response: { status: 400, data: { detail: 'Erro de validação.', errors: { group_ids: 'Tire o grupo X.' } } },
    });
    expect(mensagemDoErro(err)).toBe('Tire o grupo X.');
  });

  test('lista de mensagens por campo vira um texto só', () => {
    const err = Object.assign(new Error('Erro de validação.'), {
      response: { status: 400, data: { errors: { email: ['Inválido.'], cpf: ['Já existe.'] } } },
    });
    expect(mensagemDoErro(err)).toBe('Inválido. Já existe.');
  });

  test('sem detalhes por campo, usa a mensagem do erro', () => {
    expect(mensagemDoErro(new Error('HTTP 500'))).toBe('HTTP 500');
  });
});

describe('errosDosCampos (C2): o erro de validação vai para o campo do formulário', () => {
  test('cada campo com as mensagens dele, no formato do form.setFields', () => {
    const err = Object.assign(new Error('Erro de validação.'), {
      response: {
        status: 400,
        data: { detail: 'Erro de validação.', errors: { codigo: ['produto com este código já existe.'], nome: 'Curto.' } },
      },
    });
    expect(errosDosCampos(err)).toEqual([
      { name: 'codigo', errors: ['produto com este código já existe.'] },
      { name: 'nome', errors: ['Curto.'] },
    ]);
  });

  test('sem erros por campo (ex.: 500), nada para marcar', () => {
    expect(errosDosCampos(new Error('HTTP 500'))).toEqual([]);
  });
});

describe('nomeDe: a pessoa pelo nome, nunca pelo username (CPF)', () => {
  test('nome completo; sem nome, o e-mail', () => {
    expect(nomeDe({ first_name: 'Maria', last_name: 'Aparecida', email: 'maria@example.invalid' })).toBe('Maria Aparecida');
    expect(nomeDe({ first_name: '', last_name: '', email: 'maria@example.invalid' })).toBe('maria@example.invalid');
  });
});

describe('buildUsuarioPayload sem as funções carregadas (#2071)', () => {
  test('não manda funções nem gerência: salvar não pode tirar tudo por falha de carga', () => {
    const payload = buildUsuarioPayload(
      { username: 'x', email: 'x@example.com', is_active: true, is_superuser: false, gerencia_id: 1, funcao_ids: [] },
      { isEditing: true, cpfEditUnlocked: false, currentIsSuperuser: true, funcoesCarregadas: false },
    );
    expect(payload).not.toHaveProperty('group_ids');
    expect(payload).not.toHaveProperty('gerencia_id');
  });

  test('com as funções carregadas, manda as duas coisas (como antes)', () => {
    const payload = buildUsuarioPayload(
      { username: 'x', email: 'x@example.com', is_active: true, is_superuser: false, gerencia_id: 1, funcao_ids: [2] },
      { isEditing: true, cpfEditUnlocked: false, currentIsSuperuser: true, funcoesCarregadas: true },
    );
    expect(payload.group_ids).toEqual([2]);
    expect(payload.gerencia_id).toBe(1);
  });
});

describe('funcoesProntasParaSalvar (#2071)', () => {
  test('editar aberto antes de as funções carregarem: não manda, mesmo que tenham carregado depois', () => {
    expect(
      funcoesProntasParaSalvar({ isEditing: true, hidratouComFuncoes: false, funcoesTocadas: false, carregadasAgora: true }),
    ).toBe(false);
  });

  test('editar aberto antes da carga, mas a pessoa escolheu funções depois: manda', () => {
    expect(
      funcoesProntasParaSalvar({ isEditing: true, hidratouComFuncoes: false, funcoesTocadas: true, carregadasAgora: true }),
    ).toBe(true);
  });

  test('editar aberto com as funções carregadas: manda', () => {
    expect(
      funcoesProntasParaSalvar({ isEditing: true, hidratouComFuncoes: true, funcoesTocadas: false, carregadasAgora: true }),
    ).toBe(true);
  });

  test('criar: depende só de as funções estarem carregadas agora', () => {
    expect(
      funcoesProntasParaSalvar({ isEditing: false, hidratouComFuncoes: false, funcoesTocadas: false, carregadasAgora: true }),
    ).toBe(true);
    expect(
      funcoesProntasParaSalvar({ isEditing: false, hidratouComFuncoes: false, funcoesTocadas: false, carregadasAgora: false }),
    ).toBe(false);
  });
});
