/**
 * EditSolicitacaoPage — CON-09: "Nº da formação" obrigatório no evento de formação que ainda não terminou.
 *
 * A marca vem do servidor (`tipo_evento_de_formacao` no detalhe). Sem o número, o salvar para no campo (erro
 * ligado ao campo, foco nele) e nada vai ao servidor. Evento que já terminou edita sem o número, como no
 * servidor. A recusa do servidor no campo `encontro` também vai ao campo.
 *
 * Os campos do formulário (ComboBox/DateTimeRange/FormadoresPicker) são stubs: o formData vem do
 * GET da solicitação. O stub do tipo devolve o item do lookup (com `de_formacao`) e o da data devolve um dia
 * que já passou, para provar que trocar o tipo ou a data reconfere o número.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { getSolicitacaoMock, updateSolicitacaoMock } = vi.hoisted(() => ({
  getSolicitacaoMock: vi.fn(),
  updateSolicitacaoMock: vi.fn(),
}));

vi.mock('../../../api/solicitacoes', () => ({
  getSolicitacao: getSolicitacaoMock,
  updateSolicitacao: updateSolicitacaoMock,
}));
vi.mock('../../../api/lookup', () => ({
  lookupMunicipiosWithFilters: vi.fn().mockResolvedValue([]),
  lookupProjetos: vi.fn().mockResolvedValue([]),
  lookupTiposEvento: vi.fn().mockResolvedValue([]),
}));
vi.mock('../../../components/ComboBox', () => ({
  // Só o tipo interessa: devolve o item do lookup, que traz a marca do servidor.
  default: ({ id, onChange }: { id?: string; onChange?: (v: unknown) => void }) =>
    id === 'edit-tipo-evento' ? (
      <button
        type="button"
        data-testid="tipo-presencial"
        onClick={() => onChange?.({ id: 3, label: 'Presencial', kind: 'tipo_evento', de_formacao: true })}
      >
        tipo
      </button>
    ) : null,
}));
vi.mock('../../../components/DateTimeRange', () => ({
  default: ({ onChange }: { onChange?: (v: unknown) => void }) => (
    <button
      type="button"
      data-testid="data-passada"
      onClick={() => onChange?.({ date: '2020-01-10', start: '09:00', end: '11:00' })}
    >
      data
    </button>
  ),
}));
vi.mock('../../../components/FormadoresPicker', () => ({ default: () => null }));

import message from 'antd/es/message';
import EditSolicitacaoPage from '../EditSolicitacaoPage';
import { MSG_NUMERO_DA_FORMACAO } from '../evento';

const FUTURO = { inicio: '2099-10-10T12:00:00Z', fim: '2099-10-10T15:00:00Z' };
const PASSADO = { inicio: '2020-10-10T12:00:00Z', fim: '2020-10-10T15:00:00Z' };

function solicitacao(extra: Record<string, unknown>): Record<string, unknown> {
  return {
    id: 42,
    usuario: 1,
    municipio: 5,
    municipio_nome: 'Sobral',
    projeto: 10,
    projeto_nome: 'Vidas',
    tipo_evento: 2,
    tipo_evento_nome: 'Presencial',
    tipo_evento_de_formacao: true,
    encontro: null,
    status: 'pendente',
    gcal_status: 'NONE',
    participations: [
      { role: 'FORMADOR', usuario: { id: 7, username: 'formador1', first_name: 'Ana', last_name: 'Lima', email: '' } },
    ],
    ...FUTURO,
    ...extra,
  };
}

function erroDaApi(status: number, data: Record<string, unknown>): Error {
  return Object.assign(new Error(String(data['detail'] ?? `Erro ${status}`)), {
    status,
    response: { status, data },
  });
}

async function abrir(): Promise<HTMLElement> {
  render(
    <MemoryRouter initialEntries={['/solicitacoes/42/editar']}>
      <Routes>
        <Route path="/solicitacoes/:id/editar" element={<EditSolicitacaoPage />} />
      </Routes>
    </MemoryRouter>,
  );
  await screen.findByText('Editar Solicitação #42');
  return screen.getByLabelText(/Nº da formação/);
}

async function salvar(): Promise<void> {
  await userEvent.setup().click(screen.getByRole('button', { name: /salvar alterações/i }));
}

describe('EditSolicitacaoPage — Nº da formação no evento de formação (CON-09)', { timeout: 20000 }, () => {
  beforeEach(() => {
    getSolicitacaoMock.mockReset();
    updateSolicitacaoMock.mockReset().mockResolvedValue({ status: 'pendente' });
    vi.spyOn(message, 'error').mockImplementation(vi.fn()).mockClear();
  });

  test('evento futuro de formação sem o número: não salva e o erro fica no campo', async () => {
    getSolicitacaoMock.mockResolvedValue(solicitacao({}));
    const numero = await abrir();
    expect(numero).toHaveAttribute('aria-required', 'true');

    await salvar();

    await waitFor(() => expect(numero).toHaveAttribute('aria-invalid', 'true'));
    expect(numero).toHaveFocus();
    // O motivo chega ao leitor de tela pelo aria-describedby do campo (não só pela cor).
    const descricao = (): string =>
      (numero.getAttribute('aria-describedby') ?? '')
        .split(' ')
        .map((idDaDescricao) => document.getElementById(idDaDescricao)?.textContent ?? '')
        .join(' ');
    await waitFor(() => expect(descricao()).toContain(MSG_NUMERO_DA_FORMACAO));
    expect(updateSolicitacaoMock).not.toHaveBeenCalled();
  });

  test('evento futuro de formação com o número: salva', async () => {
    getSolicitacaoMock.mockResolvedValue(solicitacao({ encontro: '4' }));
    await abrir();

    await salvar();

    await waitFor(() => expect(updateSolicitacaoMock).toHaveBeenCalledTimes(1));
    expect(updateSolicitacaoMock.mock.calls[0]?.[1]).toMatchObject({ encontro: '4' });
  });

  test('evento que já terminou edita sem o número', async () => {
    getSolicitacaoMock.mockResolvedValue(solicitacao(PASSADO));
    const numero = await abrir();
    expect(numero).not.toHaveAttribute('aria-required');

    await salvar();

    await waitFor(() => expect(updateSolicitacaoMock).toHaveBeenCalledTimes(1));
  });

  test('tipo que não é de formação edita sem o número', async () => {
    getSolicitacaoMock.mockResolvedValue(solicitacao({ tipo_evento_nome: 'Reunião', tipo_evento_de_formacao: false }));
    await abrir();

    await salvar();

    await waitFor(() => expect(updateSolicitacaoMock).toHaveBeenCalledTimes(1));
  });

  // TELA-1: o "só espaços" vale só quando o campo é obrigatório.
  test('tipo que não é de formação com o número só de espaços: salva', async () => {
    getSolicitacaoMock.mockResolvedValue(
      solicitacao({ tipo_evento_nome: 'Reunião', tipo_evento_de_formacao: false, encontro: ' ' }),
    );
    const numero = await abrir();

    await salvar();

    await waitFor(() => expect(updateSolicitacaoMock).toHaveBeenCalledTimes(1));
    expect(numero).not.toHaveAttribute('aria-invalid');
  });

  test('trocar para um tipo de formação exige o número', async () => {
    getSolicitacaoMock.mockResolvedValue(solicitacao({ tipo_evento_nome: 'Reunião', tipo_evento_de_formacao: false }));
    const numero = await abrir();
    expect(numero).not.toHaveAttribute('aria-required');

    fireEvent.click(screen.getByTestId('tipo-presencial'));
    await waitFor(() => expect(numero).toHaveAttribute('aria-required', 'true'));
    await salvar();

    await waitFor(() => expect(numero).toHaveAttribute('aria-invalid', 'true'));
    expect(updateSolicitacaoMock).not.toHaveBeenCalled();
  });

  test('mudar a data para um dia que já passou tira o erro do número', async () => {
    getSolicitacaoMock.mockResolvedValue(solicitacao({}));
    const numero = await abrir();
    await salvar();
    await waitFor(() => expect(numero).toHaveAttribute('aria-invalid', 'true'));

    fireEvent.click(screen.getByTestId('data-passada'));

    await waitFor(() => expect(numero).not.toHaveAttribute('aria-invalid'));
    expect(numero).not.toHaveAttribute('aria-required');
  });

  test('a recusa do servidor no número vai ao campo', async () => {
    const motivo = 'Este tipo de evento pede o Nº da formação: só o número.';
    getSolicitacaoMock.mockResolvedValue(solicitacao({ encontro: 'Encontro 1' }));
    updateSolicitacaoMock.mockRejectedValue(
      erroDaApi(400, { detail: 'Erro de validação.', code: 'VALIDATION_ERROR', errors: { encontro: [motivo] } }),
    );
    const numero = await abrir();

    await salvar();

    await waitFor(() => expect(numero).toHaveAttribute('aria-invalid', 'true'));
    expect(screen.getByText(motivo)).toBeInTheDocument();
  });
});
