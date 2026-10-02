/**
 * C2b (decisão do dono, 01/10) — Projetos: excluir projeto em uso (409) mostra o motivo e oferece
 * Desativar (PATCH ativo=false, a mesma permissão do Editar), como as telas do C2.
 *
 * Modal estático do AntD não monta de forma confiável sob React 19 no jsdom: confere o que ele recebe.
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Modal, message } from 'antd';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { PROJETO } = vi.hoisted(() => ({
  PROJETO: {
    id: 21, nome: 'Projeto Fictício em Uso', codigo: 'PFU', fluxo: 'NAO_SUPER', ativo: true, setor: '',
    setor_efetivo: '', gerencia: 4, gerencia_nome: 'Vidas',
  },
}));

vi.mock('../../../api/adminDAT', () => ({
  listProjetos: vi.fn(),
  createProjeto: vi.fn(),
  updateProjeto: vi.fn(),
  deleteProjeto: vi.fn(),
  getRBACMeta: vi.fn().mockResolvedValue({ setor_groups: [], funcao_groups: [], categories: [], setores_produto: [] }),
  listGerencias: vi.fn().mockResolvedValue({ results: [], count: 0, next: null, previous: null }),
}));

import { deleteProjeto, listProjetos, updateProjeto } from '../../../api/adminDAT';
import ProjetosPage from '../ProjetosPage';

describe('ProjetosPage: excluir projeto em uso (C2b)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listProjetos).mockResolvedValue({ results: [PROJETO], count: 1, next: null, previous: null } as never);
  });

  test('409: o motivo e "Desativar", que grava ativo=false e recarrega a lista', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const erro = vi.spyOn(message, 'error').mockImplementation(() => (() => undefined) as never);
    const sucesso = vi.spyOn(message, 'success').mockImplementation(() => (() => undefined) as never);
    const motivo = 'Este registro não pode ser excluído porque está em uso (Compras, Produtos).';
    vi.mocked(deleteProjeto).mockRejectedValue(
      Object.assign(new Error(motivo), { response: { status: 409, data: { detail: motivo, code: 'CONFLICT' } } }),
    );
    vi.mocked(updateProjeto).mockResolvedValue({ ...PROJETO, ativo: false } as never);
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ProjetosPage />
      </MemoryRouter>,
    );

    const linha = (await screen.findByText(PROJETO.nome, {}, { timeout: 15000 })).closest<HTMLElement>('tr')!;
    await user.click(within(linha).getByRole('button', { name: /Excluir/ }));
    await confirmar.mock.calls[0]![0].onOk!();
    // O diálogo do 409 só abre quando a confirmação termina de fechar: um por vez, sem perder o foco.
    expect(confirmar).toHaveBeenCalledTimes(1);
    confirmar.mock.calls[0]![0].afterClose!();

    expect(erro).not.toHaveBeenCalled();
    expect(confirmar).toHaveBeenCalledTimes(2);
    const emUso = confirmar.mock.calls[1]![0];
    expect(String(emUso.content)).toContain(motivo);
    expect(String(emUso.content)).toContain(`Você pode desativar o projeto "${PROJETO.nome}"`);
    // A tela de Projetos mostra a coluna "Ativo" com Sim/Não, não "Situação: Inativo".
    expect(String(emUso.content)).toContain('a coluna Ativo passa a "Não"');
    expect(String(emUso.content)).not.toContain('Inativo');
    expect(emUso.okText).toBe('Desativar');
    const cargas = vi.mocked(listProjetos).mock.calls.length;
    await emUso.onOk!();

    expect(updateProjeto).toHaveBeenCalledWith(PROJETO.id, { ativo: false });
    expect(sucesso).toHaveBeenCalledWith('Projeto desativado');
    await waitFor(() => expect(listProjetos).toHaveBeenCalledTimes(cargas + 1));
    confirmar.mockRestore();
    erro.mockRestore();
    sucesso.mockRestore();
  }, 30000);

  test('confirmação fechada (Cancelar/Esc) com o DELETE em andamento: o 409 ainda abre o diálogo', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const erro = vi.spyOn(message, 'error').mockImplementation(() => (() => undefined) as never);
    const motivo = 'Este registro não pode ser excluído porque está em uso (Compras).';
    let recusar!: (falha: Error) => void;
    vi.mocked(deleteProjeto).mockReturnValue(new Promise((_, reject) => { recusar = reject; }) as never);
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ProjetosPage />
      </MemoryRouter>,
    );

    const linha = (await screen.findByText(PROJETO.nome, {}, { timeout: 15000 })).closest<HTMLElement>('tr')!;
    await user.click(within(linha).getByRole('button', { name: /Excluir/ }));
    const excluindo = confirmar.mock.calls[0]![0].onOk!() as Promise<void>;
    // A pessoa fecha a confirmação antes de o servidor responder.
    confirmar.mock.calls[0]![0].afterClose!();
    expect(confirmar).toHaveBeenCalledTimes(1);
    recusar(Object.assign(new Error(motivo), { response: { status: 409, data: { detail: motivo, code: 'CONFLICT' } } }));
    await excluindo;

    expect(confirmar).toHaveBeenCalledTimes(2);
    expect(confirmar.mock.calls[1]![0].title).toBe('Não é possível excluir');
    expect(String(confirmar.mock.calls[1]![0].content)).toContain(motivo);
    expect(erro).not.toHaveBeenCalled();
    confirmar.mockRestore();
    erro.mockRestore();
  }, 30000);
});
