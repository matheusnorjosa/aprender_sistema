/**
 * EditSolicitacaoPage — aviso de que o evento voltou para aprovação.
 *
 * Decisão do dono (14/10/2026): SUPER aprovada que muda data, horário, município ou formadores
 * volta para pendente no backend. O salvar avisa a pessoa quando isso acontece, pelo status que
 * a API devolve, sem repetir a regra na tela.
 *
 * Os campos do formulário (ComboBox/DateTimeRange/FormadoresPicker) são stubs: o formData vem do
 * GET da solicitação.
 */
import { render, screen, waitFor } from '@testing-library/react';
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
vi.mock('../../../components/ComboBox', () => ({ default: () => null }));
vi.mock('../../../components/DateTimeRange', () => ({ default: () => null }));
vi.mock('../../../components/FormadoresPicker', () => ({ default: () => null }));

import message from 'antd/es/message';
import EditSolicitacaoPage from '../EditSolicitacaoPage';

const SOLICITACAO = {
  id: 42,
  usuario: 1,
  municipio: 5,
  municipio_nome: 'Sobral',
  projeto: 10,
  projeto_nome: 'Vidas',
  tipo_evento: 2,
  tipo_evento_nome: 'Formação',
  inicio: '2026-10-10T12:00:00Z',
  fim: '2026-10-10T15:00:00Z',
  status: 'aprovado',
  fluxo: 'SUPER',
  gcal_status: 'NONE',
  participations: [
    { role: 'FORMADOR', usuario: { id: 7, username: 'formador1', first_name: 'Ana', last_name: 'Lima', email: '' } },
  ],
};

async function salvar(): Promise<void> {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={['/solicitacoes/42/editar']}>
      <Routes>
        <Route path="/solicitacoes/:id/editar" element={<EditSolicitacaoPage />} />
      </Routes>
    </MemoryRouter>,
  );
  await screen.findByText('Editar Solicitação #42');
  await user.click(screen.getByRole('button', { name: /salvar alterações/i }));
}

describe('EditSolicitacaoPage — aviso de volta para aprovação', () => {
  beforeEach(() => {
    getSolicitacaoMock.mockReset().mockResolvedValue(SOLICITACAO);
    updateSolicitacaoMock.mockReset();
    vi.spyOn(message, 'success').mockImplementation(vi.fn()).mockClear();
    vi.spyOn(message, 'warning').mockImplementation(vi.fn()).mockClear();
  });

  test('aprovada que volta pendente avisa que precisa de nova aprovação', async () => {
    updateSolicitacaoMock.mockResolvedValue({ ...SOLICITACAO, status: 'pendente' });

    await salvar();

    await waitFor(() => expect(message.warning).toHaveBeenCalledWith(expect.stringMatching(/voltou o evento para aprovação/i)));
    expect(message.success).not.toHaveBeenCalled();
  });

  test('aprovada que continua aprovada mostra o sucesso de sempre', async () => {
    updateSolicitacaoMock.mockResolvedValue(SOLICITACAO);

    await salvar();

    await waitFor(() => expect(message.success).toHaveBeenCalledWith('Solicitação atualizada com sucesso!'));
    expect(message.warning).not.toHaveBeenCalled();
  });

  test('pendente que continua pendente mostra o sucesso de sempre', async () => {
    const pendente = { ...SOLICITACAO, status: 'pendente' };
    getSolicitacaoMock.mockResolvedValue(pendente);
    updateSolicitacaoMock.mockResolvedValue(pendente);

    await salvar();

    await waitFor(() => expect(message.success).toHaveBeenCalledWith('Solicitação atualizada com sucesso!'));
    expect(message.warning).not.toHaveBeenCalled();
  });
});
