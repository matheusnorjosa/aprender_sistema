/**
 * C2 (Programa C) — Projetos Gerais: salvar, excluir e o formulário só com o que importa.
 *
 * - O erro de validação do backend (nome repetido) aparece com o motivo, no campo.
 * - Salvar com loading; a exclusão diz que os projetos da família ficam sem projeto geral.
 * - Só o parâmetro do cálculo escolhido aparece (divisor por aluno, multiplicador por professor),
 *   e as opções falam português, não nome de campo ("qtde_alunos / divisor").
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider, Modal, message } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { ITEM } = vi.hoisted(() => ({
  ITEM: {
    id: 1, nome: 'PROJETO AMMA', usa_avaliar: true, tipo_calculo_codigos: 'por_aluno', divisor_aluno: 20,
    multiplicador_professor: '1.10', ativo: true, descricao: '', projetos_count: 3, created_at: '', updated_at: '',
  },
}));

vi.mock('../../../api/adminDAT', () => ({
  listProjetosGerais: vi.fn(),
  createProjetoGeral: vi.fn(),
  updateProjetoGeral: vi.fn(),
  deleteProjetoGeral: vi.fn(),
}));

import { deleteProjetoGeral, listProjetosGerais, updateProjetoGeral } from '../../../api/adminDAT';
import ProjetosGeraisPage from '../ProjetosGeraisPage';

function renderPage() {
  return render(
    <ConfigProvider locale={ptBR}>
      <MemoryRouter>
        <ProjetosGeraisPage />
      </MemoryRouter>
    </ConfigProvider>,
  );
}

async function linha(): Promise<HTMLElement> {
  return (await screen.findByRole('button', { name: `Editar: ${ITEM.nome}` }, { timeout: 15000 })).closest<HTMLElement>('tr')!;
}

async function abrirEditar(user: ReturnType<typeof userEvent.setup>): Promise<HTMLElement> {
  await user.click(within(await linha()).getByRole('button', { name: `Editar: ${ITEM.nome}` }));
  return (await screen.findByText('Editar Projeto Geral', {}, { timeout: 10000 })).closest<HTMLElement>('[role="dialog"]')!;
}

/** O campo está escondido (Form.Item `hidden`: continua no formulário, fora da tela). */
function escondido(modal: HTMLElement, rotulo: string): boolean {
  return within(modal).getByLabelText(rotulo).closest('.ant-form-item')!.classList.contains('ant-form-item-hidden');
}

describe('ProjetosGeraisPage: salvar e excluir (C2)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listProjetosGerais).mockResolvedValue({ results: [ITEM], count: 1, next: null, previous: null } as never);
    vi.mocked(updateProjetoGeral).mockResolvedValue(ITEM as never);
  });

  test('erro de validação ao salvar: o motivo do backend no toast e no campo', async () => {
    const erro = vi.spyOn(message, 'error').mockImplementation(() => (() => undefined) as never);
    vi.mocked(updateProjetoGeral).mockRejectedValue(
      Object.assign(new Error('Erro de validação.'), {
        response: { status: 400, data: { detail: 'Erro de validação.', errors: { nome: ['projeto geral com este nome já existe.'] } } },
      }),
    );
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user);
    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(erro).toHaveBeenCalledWith('Erro ao salvar: projeto geral com este nome já existe.'));
    expect(await within(modal).findByText('projeto geral com este nome já existe.')).toBeInTheDocument();
    erro.mockRestore();
  }, 40000);

  test('Salvar fica em loading enquanto a API trabalha', async () => {
    vi.mocked(updateProjetoGeral).mockReturnValue(new Promise(() => undefined));
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user);
    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(within(modal).getByRole('button', { name: /Salvar/ })).toHaveClass('ant-btn-loading'));
  }, 40000);

  test('a exclusão diz que os projetos da família, ativos e inativos, ficam sem projeto geral', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    vi.mocked(listProjetosGerais).mockResolvedValue({
      results: [ITEM, { ...ITEM, id: 2, nome: 'PROJETO VIDAS', projetos_count: 0 }], count: 2, next: null, previous: null,
    } as never);
    const user = userEvent.setup();
    renderPage();

    await user.click(within(await linha()).getByRole('button', { name: `Excluir: ${ITEM.nome}` }));
    await user.click(await screen.findByRole('button', { name: 'Excluir: PROJETO VIDAS' }));

    const [comAtivos, semAtivos] = confirmar.mock.calls.map(([opcoes]) => String(opcoes.content));
    // A contagem é só dos ativos, mas o SET_NULL também desvincula os inativos.
    expect(comAtivos).toBe(
      `Tem certeza que deseja excluir "${ITEM.nome}"? Os projetos desta família (3 ativo(s) e os inativos) ficarão sem projeto geral.`,
    );
    expect(semAtivos).toBe(
      'Tem certeza que deseja excluir "PROJETO VIDAS"? Não há projetos ativos nesta família; os inativos, se houver, ficarão sem projeto geral.',
    );
    confirmar.mockRestore();
  }, 30000);

  test('excluir registro em uso (409): o motivo e "Desativar", que grava ativo=false e recarrega a lista (C2b)', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const erro = vi.spyOn(message, 'error').mockImplementation(() => (() => undefined) as never);
    const sucesso = vi.spyOn(message, 'success').mockImplementation(() => (() => undefined) as never);
    const motivo = 'Este registro não pode ser excluído porque está em uso (Cadastros DAT).';
    vi.mocked(deleteProjetoGeral).mockRejectedValue(
      Object.assign(new Error(motivo), { response: { status: 409, data: { detail: motivo, code: 'CONFLICT' } } }),
    );
    vi.mocked(updateProjetoGeral).mockResolvedValue({ ...ITEM, ativo: false } as never);
    const user = userEvent.setup();
    renderPage();

    await user.click(within(await linha()).getByRole('button', { name: `Excluir: ${ITEM.nome}` }));
    await confirmar.mock.calls[0]![0].onOk!();
    // O diálogo do 409 só abre quando a confirmação termina de fechar: um por vez, sem perder o foco.
    expect(confirmar).toHaveBeenCalledTimes(1);
    confirmar.mock.calls[0]![0].afterClose!();

    expect(erro).not.toHaveBeenCalled();
    expect(confirmar).toHaveBeenCalledTimes(2);
    const emUso = confirmar.mock.calls[1]![0];
    expect(String(emUso.content)).toContain(motivo);
    expect(String(emUso.content)).toContain(`Você pode desativar o projeto geral "${ITEM.nome}"`);
    expect(emUso.okText).toBe('Desativar');
    const cargas = vi.mocked(listProjetosGerais).mock.calls.length;
    await emUso.onOk!();

    expect(updateProjetoGeral).toHaveBeenCalledWith(ITEM.id, { ativo: false });
    expect(sucesso).toHaveBeenCalledWith('Projeto geral desativado');
    await waitFor(() => expect(listProjetosGerais).toHaveBeenCalledTimes(cargas + 1));
    confirmar.mockRestore();
    erro.mockRestore();
    sucesso.mockRestore();
  }, 30000);

  test('só o parâmetro do cálculo escolhido aparece, e as opções falam português', async () => {
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user); // por aluno
    expect(escondido(modal, 'Divisor (por aluno)')).toBe(false);
    expect(escondido(modal, 'Multiplicador (por professor)')).toBe(true);

    // Rótulo curto no Select (a 360 px a fórmula cortava); a fórmula fica abaixo do campo.
    expect(within(modal).getByText('Cálculo: alunos ÷ divisor.')).toBeInTheDocument();

    await user.click(within(modal).getByRole('combobox', { name: 'Cálculo de códigos' }));
    await user.click(await screen.findByTitle('Por professor'));
    expect(escondido(modal, 'Divisor (por aluno)')).toBe(true);
    expect(escondido(modal, 'Multiplicador (por professor)')).toBe(false);
    expect(within(modal).getByText('Cálculo: professores × multiplicador.')).toBeInTheDocument();

    await user.click(within(modal).getByRole('combobox', { name: 'Cálculo de códigos' }));
    await user.click(await screen.findByTitle('Não se aplica'));
    expect(escondido(modal, 'Divisor (por aluno)')).toBe(true);
    expect(escondido(modal, 'Multiplicador (por professor)')).toBe(true);
    expect(within(modal).getByText('Cálculo: não gera códigos.')).toBeInTheDocument();
  }, 40000);

  test('falha ao carregar a lista: o motivo e "Tentar de novo", não "Não há dados"', async () => {
    vi.mocked(listProjetosGerais).mockRejectedValue(new Error('Você não tem permissão para realizar esta ação.'));
    renderPage();

    const alerta = await screen.findByText('Não foi possível carregar a lista.', {}, { timeout: 15000 });
    expect(alerta.closest('[role="alert"]')).toHaveTextContent('Você não tem permissão para realizar esta ação.');
    expect(screen.queryByText('Não há dados')).not.toBeInTheDocument();
  }, 30000);
});
