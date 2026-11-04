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

const { getSolicitacaoMock, updateSolicitacaoMock, escolha } = vi.hoisted(() => ({
  getSolicitacaoMock: vi.fn(),
  updateSolicitacaoMock: vi.fn(),
  // O município que o clique no campo escolhe (a marca do par vem da lista, como na tela).
  escolha: { municipio: { id: 6, label: 'Crato-CE', sem_compra: true } },
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
  default: ({ placeholder = '', onChange }: { placeholder?: string; onChange?: (item: unknown) => void }) =>
    placeholder.includes('município') ? (
      <button type="button" onClick={() => onChange?.(escolha.municipio)}>
        {placeholder}
      </button>
    ) : null,
}));
vi.mock('../../../components/DateTimeRange', () => ({ default: () => null }));
vi.mock('../../../components/FormadoresPicker', () => ({ default: () => null }));

import message from 'antd/es/message';
import { ComAcesso } from '../../../test/comAcesso';
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

async function salvar(policies: readonly string[] = [], escolherMunicipio = false): Promise<void> {
  const user = userEvent.setup();
  render(
    <ComAcesso policies={policies}>
      <MemoryRouter initialEntries={['/solicitacoes/42/editar']}>
        <Routes>
          <Route path="/solicitacoes/:id/editar" element={<EditSolicitacaoPage />} />
        </Routes>
      </MemoryRouter>
    </ComAcesso>,
  );
  await screen.findByText('Editar Solicitação #42');
  if (escolherMunicipio) await user.click(screen.getByRole('button', { name: 'Busque ou selecione um município' }));
  await user.click(screen.getByRole('button', { name: /salvar alterações/i }));
}

describe('EditSolicitacaoPage — aviso de volta para aprovação', () => {
  beforeEach(() => {
    escolha.municipio = { id: 6, label: 'Crato-CE', sem_compra: true };
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

  // Pedido do dono (03/11/2026): o par novo sem compra manda o evento para aprovação (qualquer fluxo).
  test('aprovada que volta pendente por par sem compra diz que é a compra', async () => {
    updateSolicitacaoMock.mockResolvedValue({ ...SOLICITACAO, municipio: 6, status: 'pendente', sem_compra: true });

    await salvar([], true);

    await waitFor(() =>
      expect(message.warning).toHaveBeenCalledWith(
        'Solicitação atualizada. Sem compra neste município para este projeto: o evento voltou para aprovação.',
      ),
    );
  });

  // A mensagem segue a marca do par escolhido na tela, não o `sem_compra` da resposta.
  test('município escolhido com compra: a mensagem não culpa a compra', async () => {
    escolha.municipio = { id: 6, label: 'Crato-CE', sem_compra: false };
    updateSolicitacaoMock.mockResolvedValue({ ...SOLICITACAO, municipio: 6, status: 'pendente', sem_compra: true });

    await salvar([], true);

    await waitFor(() => expect(message.warning).toHaveBeenCalledWith(expect.stringMatching(/A mudança de data/)));
  });

  test('quem é isento da regra da compra não leva a culpa da compra', async () => {
    updateSolicitacaoMock.mockResolvedValue({ ...SOLICITACAO, municipio: 6, status: 'pendente', sem_compra: true });

    await salvar(['edit_solicitation_as_owner_or_privileged', 'create_solicitation_without_purchase'], true);

    await waitFor(() => expect(message.warning).toHaveBeenCalledWith(expect.stringMatching(/A mudança de data/)));
  });

  test('par sem compra que não mudou não leva a culpa (a data mudou)', async () => {
    getSolicitacaoMock.mockResolvedValue({ ...SOLICITACAO, sem_compra: true });
    updateSolicitacaoMock.mockResolvedValue({ ...SOLICITACAO, status: 'pendente', sem_compra: true });

    await salvar();

    await waitFor(() => expect(message.warning).toHaveBeenCalledWith(expect.stringMatching(/A mudança de data/)));
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
