/**
 * G07 (alinhamento lote B, 05/11/2026) — Deslocamentos: botões só onde a pessoa pode, e o motivo do erro.
 *
 * - P#12 (D22): Editar e Excluir apareciam em toda linha; a escrita só vale para o dono ou para quem
 *   delega, e o resto dava 403. O servidor manda `pode_editar` por linha e a tela só mostra os botões aí.
 * - P#13 (D73): a tela procurava `end_date`/`destino` no próprio erro e sempre mostrava "Erro ao
 *   salvar deslocamento". O motivo chega em `response.data.errors` (validação) ou no `detail` (403).
 * - B#21: o resto do sistema diz "excluir", não "deletar".
 */

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message } from 'antd';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router';

import { ComAcesso } from '../../../test/comAcesso';

const { listDeslocamentosMock, updateMock, deleteMock } = vi.hoisted(() => ({
  listDeslocamentosMock: vi.fn(),
  updateMock: vi.fn(),
  deleteMock: vi.fn(),
}));

vi.mock('../../../api/deslocamentos', () => ({
  listDeslocamentos: listDeslocamentosMock,
  listFormadoresDoSetor: vi.fn().mockResolvedValue([]),
  listAlvosDeslocamento: vi.fn().mockResolvedValue([]),
  createDeslocamento: vi.fn(),
  updateDeslocamento: updateMock,
  deleteDeslocamento: deleteMock,
}));
vi.mock('../../../components/DatImportsCentralizedBanner', () => ({ default: () => null }));

import DeslocamentosPage from '../DeslocamentosPage';

function linha(id: number, nome: string, podeEditar: boolean) {
  return {
    id,
    usuario: id,
    usuario_nome: nome,
    pode_editar: podeEditar,
    origem: 'Fortaleza',
    destino: 'Sobral',
    start_date: '2026-11-10',
    end_date: '2026-11-10',
    observacao: '',
  };
}

/** O erro como `fetchAPI` lança (`ErroHttp`): `message` = detail, corpo em `response.data`. */
function erroHttp(status: number, data: { detail: string; errors?: Record<string, string[]> }) {
  return Object.assign(new Error(data.detail), { status, response: { status, data } });
}

async function renderComLinhas(...linhas: ReturnType<typeof linha>[]) {
  listDeslocamentosMock.mockResolvedValue({ count: linhas.length, next: null, previous: null, results: linhas });
  render(
    <MemoryRouter>
      <ComAcesso policies={['access_travel']}>
        <DeslocamentosPage />
      </ComAcesso>
    </MemoryRouter>,
  );
  await screen.findByText(linhas[0]!.usuario_nome, undefined, { timeout: 8000 });
}

function linhaDe(nome: string): HTMLElement {
  return screen.getByText(nome).closest('tr')!;
}

describe('DeslocamentosPage — G07', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.clearAllMocks();
  });

  function espiaMensagens() {
    return {
      erro: vi.spyOn(message, 'error').mockImplementation(() => (() => undefined) as never),
      sucesso: vi.spyOn(message, 'success').mockImplementation(() => (() => undefined) as never),
    };
  }

  test('Editar e Excluir só nas linhas com pode_editar', async () => {
    await renderComLinhas(linha(1, 'Minha Linha', true), linha(2, 'Da Colega', false));

    const minha = linhaDe('Minha Linha');
    expect(within(minha).getByRole('button', { name: 'Editar deslocamento' })).toBeInTheDocument();
    expect(within(minha).getByRole('button', { name: 'Excluir deslocamento' })).toBeInTheDocument();

    const daColega = linhaDe('Da Colega');
    expect(within(daColega).queryByRole('button', { name: 'Editar deslocamento' })).not.toBeInTheDocument();
    expect(within(daColega).queryByRole('button', { name: 'Excluir deslocamento' })).not.toBeInTheDocument();
  }, 20000);

  test('ao salvar, mostra o motivo da validação do servidor', async () => {
    updateMock.mockRejectedValue(
      erroHttp(400, {
        detail: 'Erro de validação.',
        errors: { end_date: ['Data fim não pode ser anterior à data início.'] },
      }),
    );
    const { erro } = espiaMensagens();
    await renderComLinhas(linha(1, 'Minha Linha', true));

    fireEvent.click(within(linhaDe('Minha Linha')).getByRole('button', { name: 'Editar deslocamento' }));
    const dialogo = await screen.findByRole('dialog', {}, { timeout: 8000 });
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(erro).toHaveBeenCalledWith('Data fim não pode ser anterior à data início.'), {
      timeout: 8000,
    });
    expect(updateMock).toHaveBeenCalledWith(1, expect.objectContaining({ end_date: '2026-11-10' }));
  }, 20000);

  test('ao excluir, confirma com "excluir" e mostra o 403 do servidor', async () => {
    deleteMock.mockRejectedValue(
      erroHttp(403, { detail: 'Você não tem permissão para alterar deslocamento de outro usuário.' }),
    );
    const { erro } = espiaMensagens();
    await renderComLinhas(linha(1, 'Minha Linha', true));

    fireEvent.click(within(linhaDe('Minha Linha')).getByRole('button', { name: 'Excluir deslocamento' }));
    expect(await screen.findByText('Excluir este deslocamento?')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Excluir' }));

    await waitFor(
      () => expect(erro).toHaveBeenCalledWith('Você não tem permissão para alterar deslocamento de outro usuário.'),
      { timeout: 8000 },
    );
    expect(deleteMock).toHaveBeenCalledWith(1);
  }, 20000);

  test('exclusão que dá certo diz "excluído"', async () => {
    deleteMock.mockResolvedValue(undefined);
    const { sucesso } = espiaMensagens();
    await renderComLinhas(linha(1, 'Minha Linha', true));

    fireEvent.click(within(linhaDe('Minha Linha')).getByRole('button', { name: 'Excluir deslocamento' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Excluir' }));

    await waitFor(() => expect(sucesso).toHaveBeenCalledWith('Deslocamento excluído.'), { timeout: 8000 });
  }, 20000);
});
