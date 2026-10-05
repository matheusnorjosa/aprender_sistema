/**
 * C2b (decisão do dono, 01/10) — excluir registro em uso: o motivo e a saída, não só um toast.
 *
 * O backend recusa excluir registro em uso (FK PROTECT) com 409 e o motivo ("... está em uso
 * (Compras)."). A tela mostra esse motivo e, se o registro está ativo, oferece Desativar: PATCH
 * `ativo=false` pelo mesmo cliente e permissão do Editar. Registro já inativo: só o motivo.
 *
 * O diálogo do 409 só abre quando a confirmação de excluir termina de fechar (o `afterClose` dela):
 * aberto de dentro do onOk, o rc-dialog tirava o foco do Cancelar e o largava no body ao fechar.
 * O foco em si é medido no Chromium (e2e/checklist/excluir-em-uso-foco.spec.ts).
 *
 * Modal estático do AntD não monta de forma confiável sob React 19 no jsdom: confere o que ele recebe.
 */
import { Modal, message } from 'antd';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import { aposConfirmacaoFechar, dialogoDeExclusaoEmUso, dialogoNaoPodeExcluir } from '../excluirEmUso';

const MOTIVO = 'Este registro não pode ser excluído porque está em uso (Compras).';

function erroHttp(status: number, detail: string): Error {
  return Object.assign(new Error(detail), { status, response: { status, data: { detail } } });
}

function opcoes(extra: Partial<Parameters<typeof dialogoDeExclusaoEmUso>[0]> = {}) {
  return {
    erro: erroHttp(409, MOTIVO),
    registro: 'o produto "Kit Fictício" (código KIT-1)',
    ativo: true,
    desativar: vi.fn().mockResolvedValue({}),
    desativado: 'Produto desativado',
    recarregar: vi.fn(),
    ...extra,
  };
}

describe('dialogoDeExclusaoEmUso (C2b)', () => {
  let confirmar: ReturnType<typeof vi.spyOn>;
  let informar: ReturnType<typeof vi.spyOn>;
  let sucesso: ReturnType<typeof vi.spyOn>;
  let erro: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    informar = vi.spyOn(Modal, 'info').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    sucesso = vi.spyOn(message, 'success').mockImplementation(() => (() => undefined) as never);
    erro = vi.spyOn(message, 'error').mockImplementation(() => (() => undefined) as never);
  });

  afterEach(() => vi.restoreAllMocks());

  test('registro ativo: o motivo do backend e "Desativar", começando no Cancelar', () => {
    const abrir = dialogoDeExclusaoEmUso(opcoes());

    // Nada abre antes de a confirmação fechar: quem abre é o afterClose dela.
    expect(abrir).toBeTypeOf('function');
    expect(confirmar).not.toHaveBeenCalled();
    abrir!();
    expect(confirmar).toHaveBeenCalledTimes(1);
    const dialogo = confirmar.mock.calls[0]![0] as Parameters<typeof Modal.confirm>[0];
    expect(dialogo.title).toBe('Não é possível excluir');
    expect(String(dialogo.content)).toBe(
      `${MOTIVO} Você pode desativar o produto "Kit Fictício" (código KIT-1): o registro e os vínculos` +
        ' continuam no sistema, a situação passa a Inativo e dá para reativar em Editar.',
    );
    expect(dialogo.okText).toBe('Desativar');
    expect(dialogo.cancelText).toBe('Cancelar');
    // Quem acabou de confirmar "Sim, excluir" com Enter não desativa sem ler.
    expect(dialogo.autoFocusButton).toBe('cancel');
    expect(informar).not.toHaveBeenCalled();
  });

  test('Desativar grava ativo=false, avisa e recarrega a lista', async () => {
    const o = opcoes();
    dialogoDeExclusaoEmUso(o)!();

    await (confirmar.mock.calls[0]![0] as Parameters<typeof Modal.confirm>[0]).onOk!();

    expect(o.desativar).toHaveBeenCalledTimes(1);
    expect(sucesso).toHaveBeenCalledWith('Produto desativado');
    expect(o.recarregar).toHaveBeenCalledTimes(1);
    expect(erro).not.toHaveBeenCalled();
  });

  test('Desativar que falha: o motivo no toast, e a lista não recarrega', async () => {
    const o = opcoes({ desativar: vi.fn().mockRejectedValue(erroHttp(403, 'Você não tem permissão para realizar esta ação.')) });
    dialogoDeExclusaoEmUso(o)!();

    // Resolve (não rejeita): o AntD deixaria a rejeição sem tratamento.
    await expect((confirmar.mock.calls[0]![0] as Parameters<typeof Modal.confirm>[0]).onOk!()).resolves.toBeUndefined();

    expect(erro).toHaveBeenCalledWith('Erro ao desativar: Você não tem permissão para realizar esta ação.');
    expect(sucesso).not.toHaveBeenCalled();
    expect(o.recarregar).not.toHaveBeenCalled();
  });

  test('registro já inativo: só o motivo, sem "Desativar"', () => {
    const abrir = dialogoDeExclusaoEmUso(opcoes({ ativo: false }));

    expect(informar).not.toHaveBeenCalled();
    abrir!();
    expect(confirmar).not.toHaveBeenCalled();
    expect(informar).toHaveBeenCalledTimes(1);
    const aviso = informar.mock.calls[0]![0] as Parameters<typeof Modal.info>[0];
    expect(aviso.title).toBe('Não é possível excluir');
    expect(String(aviso.content)).toBe(`${MOTIVO} O registro já está inativo.`);
    expect(aviso.okText).toBe('Entendi');
  });

  test.each([
    ['403', erroHttp(403, 'Você não tem permissão para realizar esta ação.')],
    ['500', erroHttp(500, 'Erro 500')],
    ['sem rede', new TypeError('Sem conexão com o servidor.')],
  ])('erro que não é "em uso" (%s): devolve null e não abre diálogo', (_nome, falha) => {
    expect(dialogoDeExclusaoEmUso(opcoes({ erro: falha }))).toBeNull();

    expect(confirmar).not.toHaveBeenCalled();
    expect(informar).not.toHaveBeenCalled();
  });

  test('tela que mostra "Ativo: Sim/Não": o texto fala a coluna da tela, não "situação Inativo"', () => {
    dialogoDeExclusaoEmUso(opcoes({ registro: 'o projeto "Projeto Fictício"', aoDesativar: 'a coluna Ativo passa a "Não"' }))!();

    const dialogo = confirmar.mock.calls[0]![0] as Parameters<typeof Modal.confirm>[0];
    expect(String(dialogo.content)).toBe(
      `${MOTIVO} Você pode desativar o projeto "Projeto Fictício": o registro e os vínculos` +
        ' continuam no sistema, a coluna Ativo passa a "Não" e dá para reativar em Editar.',
    );
  });
});

test('tela em que desativar tem consequência: o texto diz o que fica e o que muda, sem "os vínculos continuam"', () => {
  const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));

  dialogoDeExclusaoEmUso(
    opcoes({
      registro: 'a gerência "Vidas"',
      oQueFica: 'os projetos e a equipe continuam cadastrados',
      aoDesativar: 'mas a equipe perde o acesso por ela, a situação passa a Inativo',
    }),
  )!();

  expect(String(confirmar.mock.calls[0]![0].content)).toBe(
    `${MOTIVO} Você pode desativar a gerência "Vidas": os projetos e a equipe continuam cadastrados,` +
      ' mas a equipe perde o acesso por ela, a situação passa a Inativo e dá para reativar em Editar.',
  );
  vi.restoreAllMocks();
});

describe('dialogoNaoPodeExcluir: exclusão que a tela já sabe recusada, sem DELETE (C2b)', () => {
  const MOTIVO_DA_TELA = 'A gerência "Vidas" tem 2 projeto(s) ativo(s) vinculado(s).';
  const base = {
    motivo: MOTIVO_DA_TELA,
    registro: 'a gerência "Vidas"',
    desativado: 'Gerência desativada',
  };

  afterEach(() => vi.restoreAllMocks());

  test('registro ativo: o motivo da tela e "Desativar", começando no Cancelar', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const sucesso = vi.spyOn(message, 'success').mockImplementation(() => (() => undefined) as never);
    const desativar = vi.fn().mockResolvedValue({});
    const recarregar = vi.fn();

    dialogoNaoPodeExcluir({ ...base, ativo: true, desativar, recarregar })();

    const dialogo = confirmar.mock.calls[0]![0];
    expect(dialogo.title).toBe('Não é possível excluir');
    expect(String(dialogo.content)).toBe(
      `${MOTIVO_DA_TELA} Você pode desativar a gerência "Vidas": o registro e os vínculos continuam no sistema,` +
        ' a situação passa a Inativo e dá para reativar em Editar.',
    );
    expect(dialogo.okText).toBe('Desativar');
    expect(dialogo.autoFocusButton).toBe('cancel');
    await dialogo.onOk!();
    expect(desativar).toHaveBeenCalledTimes(1);
    expect(sucesso).toHaveBeenCalledWith('Gerência desativada');
    expect(recarregar).toHaveBeenCalledTimes(1);
  });

  test('registro já inativo: só o motivo e "Entendi"', () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const informar = vi.spyOn(Modal, 'info').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));

    dialogoNaoPodeExcluir({ ...base, ativo: false, desativar: vi.fn(), recarregar: vi.fn() })();

    expect(confirmar).not.toHaveBeenCalled();
    expect(String(informar.mock.calls[0]![0].content)).toBe(`${MOTIVO_DA_TELA} O registro já está inativo.`);
    expect(informar.mock.calls[0]![0].okText).toBe('Entendi');
  });
});

describe('aposConfirmacaoFechar: o diálogo do 409 abre uma vez, com a confirmação já fechada (C2b)', () => {
  test('409 com a confirmação aberta: espera o afterClose dela', () => {
    const fila = aposConfirmacaoFechar();
    const dialogo = vi.fn();

    fila.abrir(dialogo);
    expect(dialogo).not.toHaveBeenCalled();
    fila.afterClose();

    expect(dialogo).toHaveBeenCalledTimes(1);
  });

  test('confirmação fechada (Cancelar/Esc) com o DELETE em andamento: o 409 abre na hora, não some', () => {
    const fila = aposConfirmacaoFechar();
    const dialogo = vi.fn();

    fila.afterClose();
    expect(dialogo).not.toHaveBeenCalled();
    fila.abrir(dialogo);

    expect(dialogo).toHaveBeenCalledTimes(1);
  });

  test('afterClose repetido (o AntD fecha de novo quando o onOk termina) não reabre o diálogo', () => {
    const fila = aposConfirmacaoFechar();
    const dialogo = vi.fn();

    fila.abrir(dialogo);
    fila.afterClose();
    fila.afterClose();

    expect(dialogo).toHaveBeenCalledTimes(1);
  });
});
