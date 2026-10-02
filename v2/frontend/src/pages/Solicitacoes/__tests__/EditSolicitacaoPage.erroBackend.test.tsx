/**
 * EditSolicitacaoPage — o motivo que o backend dá ao recusar o salvar aparece na tela.
 *
 * Regra do dono (30/09): a gerência da Superintendência só edita o próprio alcance — fluxo SUPER da
 * Superintendência + gerências de um 2º vínculo de GERENTE — (403 com `detail`) e só move para projeto
 * desse alcance (400 em `errors.projeto`). Antes a tela
 * mostrava texto fixo e a pessoa não via o porquê.
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
  lookupMunicipios: vi.fn().mockResolvedValue([]),
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
  status: 'pendente',
  gcal_status: 'NONE',
  participations: [
    { role: 'FORMADOR', usuario: { id: 7, username: 'formador1', first_name: 'Ana', last_name: 'Lima', email: '' } },
  ],
};

function erroDaApi(status: number, data: Record<string, unknown>): Error {
  return Object.assign(new Error(String(data['detail'] ?? `Erro ${status}`)), {
    status,
    response: { status, data },
  });
}

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

describe('EditSolicitacaoPage — motivo do backend ao recusar o salvar', () => {
  beforeEach(() => {
    getSolicitacaoMock.mockReset().mockResolvedValue(SOLICITACAO);
    updateSolicitacaoMock.mockReset();
    vi.spyOn(message, 'error').mockImplementation(vi.fn()).mockClear();
  });

  test('403 mostra o detail do backend', async () => {
    const detail = 'A gerência da Superintendência só edita ou exclui solicitações do fluxo SUPER da Superintendência.';
    updateSolicitacaoMock.mockRejectedValue(erroDaApi(403, { detail, code: 'PERMISSION_DENIED' }));

    await salvar();

    await waitFor(() => expect(message.error).toHaveBeenCalledWith(detail));
  });

  test('403 sem detail mantém o texto padrão', async () => {
    updateSolicitacaoMock.mockRejectedValue(erroDaApi(403, {}));

    await salvar();

    await waitFor(() => expect(message.error).toHaveBeenCalledWith('Você não tem permissão para editar esta solicitação.'));
  });

  test('400 mostra o motivo do campo (errors.projeto)', async () => {
    const motivo = 'Você só pode criar ou mover solicitação para projeto do fluxo SUPER da Superintendência.';
    updateSolicitacaoMock.mockRejectedValue(
      erroDaApi(400, { detail: 'Erro de validação.', code: 'VALIDATION_ERROR', errors: { projeto: [motivo] } }),
    );

    await salvar();

    await waitFor(() => expect(message.error).toHaveBeenCalledWith(motivo));
  });

  test('400 de conflito de agenda mostra a frase do detail, não o e-mail do convidado', async () => {
    const detail = 'Não é possível salvar a alteração: Bruno Formador passa do limite diário de horas.';
    const convidado = 'convidado.externo@example.invalid';
    updateSolicitacaoMock.mockRejectedValue(
      erroDaApi(400, {
        detail,
        code: 'availability_conflict',
        errors: {
          conflicts: [{ code: 'M', title: 'Capacidade diária excedida', detail: 'x' }],
          blocked_participants: [
            { usuario_id: 7, usuario_nome: 'Bruno Formador', conflicts: [{ code: 'M', title: 'Capacidade diária excedida', detail: 'x' }] },
          ],
          skipped_guests: [convidado],
        },
      }),
    );

    await salvar();

    await waitFor(() => expect(message.error).toHaveBeenCalledWith(detail));
    expect(message.error).toHaveBeenCalledTimes(1);
    expect(message.error).not.toHaveBeenCalledWith(convidado);
  });
});
