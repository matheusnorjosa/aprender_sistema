/**
 * EditSolicitacaoPage — a caixa "Coordenador(es)" (decisões do dono, 03/11/2026).
 *
 * A edição usa a caixa única da criação: o 1º é o responsável (com a pergunta "vai acompanhar?" sobre
 * ele) e os demais são as participações COORD_ACOMPANHA. Trocar o 1º troca o responsável e apaga a
 * resposta de acompanhar (o novo responsável responde). Salvar manda `coordenador` e a lista inteira em
 * `extra_participants.coord_acompanha_ids`. Evento antigo sem responsável gravado: o 1º da caixa é quem
 * criou (o responsável para o backend) e salvar sem trocar o 1º não manda `coordenador`.
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import message from 'antd/es/message';

const { getSolicitacaoMock, updateSolicitacaoMock, novaLista } = vi.hoisted(() => ({
  getSolicitacaoMock: vi.fn(),
  updateSolicitacaoMock: vi.fn(),
  /** Lista que o CoordenadoresPicker simulado entrega ao clicar em "Trocar coordenadores". */
  novaLista: { value: [] as { id: number; label: string }[] },
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
vi.mock('../../../components/CoordenadoresPicker', () => ({
  default: ({
    value = [],
    onChange,
    id,
    'aria-describedby': descrito,
  }: {
    value?: Array<{ id: number; label: string }>;
    onChange?: (v: unknown) => void;
    id?: string;
    'aria-describedby'?: string;
  }) => (
    <>
      <input
        data-testid="caixa-coordenadores"
        id={id}
        aria-describedby={descrito}
        readOnly
        value={value.map((c) => c.label).join(', ')}
      />
      <button type="button" onClick={() => onChange?.(novaLista.value)}>
        Trocar coordenadores
      </button>
    </>
  ),
}));

import EditSolicitacaoPage from '../EditSolicitacaoPage';

const pessoa = (id: number, first: string, last: string) => ({
  id,
  username: `u${id}`,
  first_name: first,
  last_name: last,
  email: `u${id}@example.invalid`,
});

const SOLICITACAO = {
  id: 42,
  usuario: 1,
  municipio: 5,
  municipio_nome: 'Sobral',
  projeto: 10,
  projeto_nome: 'Vidas',
  tipo_evento: 2,
  tipo_evento_nome: 'Formação',
  coordenador: 1,
  coordenador_nome: 'Ana Coordenadora',
  coordenador_acompanha: false,
  inicio: '2026-10-10T12:00:00Z',
  fim: '2026-10-10T15:00:00Z',
  status: 'pendente',
  fluxo: 'SUPER',
  gcal_status: 'NONE',
  participations: [
    { role: 'COORDENADOR', usuario: pessoa(1, 'Ana', 'Coordenadora') },
    { role: 'FORMADOR', usuario: pessoa(99, 'Bruno', 'Formador') },
    { role: 'COORD_ACOMPANHA', usuario: pessoa(8, 'Dora', 'Coordenadora') },
  ],
};

const ACOMPANHA = /O coordenador responsável vai acompanhar o evento\?/;

function renderPage(): void {
  render(
    <MemoryRouter initialEntries={['/solicitacoes/42/editar']}>
      <Routes>
        <Route path="/solicitacoes/:id/editar" element={<EditSolicitacaoPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

const salvar = (): void => fireEvent.click(screen.getByRole('button', { name: /salvar alterações/i }));
const caixa = (): HTMLElement => screen.getByTestId('caixa-coordenadores');

describe('EditSolicitacaoPage — caixa "Coordenador(es)"', { timeout: 20000 }, () => {
  beforeEach(() => {
    getSolicitacaoMock.mockReset().mockResolvedValue(SOLICITACAO);
    updateSolicitacaoMock.mockReset().mockResolvedValue({ ...SOLICITACAO });
    vi.spyOn(message, 'success').mockImplementation(vi.fn()).mockClear();
    vi.spyOn(message, 'error').mockImplementation(vi.fn()).mockClear();
    novaLista.value = [];
  });

  test('uma caixa só, "Coordenador(es)", com o responsável em 1º e a explicação ligada a ela', async () => {
    renderPage();
    await waitFor(() => expect(caixa()).toHaveValue('Ana Coordenadora, Dora Coordenadora'));
    expect(document.querySelector(`label[for="${caixa().id}"]`)).toHaveTextContent(/^Coordenador\(es\)$/);
    const descricao = (caixa().getAttribute('aria-describedby') ?? '')
      .split(' ')
      .map((id) => document.getElementById(id)?.textContent ?? '')
      .join(' ');
    expect(descricao).toContain('O 1º escolhido é o coordenador responsável.');
    expect(screen.queryByText('Outros coordenadores')).not.toBeInTheDocument();
    expect(screen.queryByText('Coordenador responsável')).not.toBeInTheDocument();
  });

  test('salvar sem mexer manda o responsável e os demais', async () => {
    renderPage();
    await waitFor(() => expect(caixa()).toHaveValue('Ana Coordenadora, Dora Coordenadora'));
    salvar();
    await waitFor(() => expect(updateSolicitacaoMock).toHaveBeenCalled());
    const payload = updateSolicitacaoMock.mock.calls[0][1];
    expect(payload.coordenador).toBe(1);
    expect(payload.coordenador_acompanha).toBe(false);
    expect(payload.extra_participants).toEqual({ formador_ids: [99], coord_acompanha_ids: [8] });
  });

  test('trocar o 1º troca o responsável e pede de novo a resposta de acompanhar', async () => {
    novaLista.value = [
      { id: 5, label: 'Eva Coordenadora' },
      { id: 8, label: 'Dora Coordenadora' },
    ];
    renderPage();
    await waitFor(() => expect(caixa()).toHaveValue('Ana Coordenadora, Dora Coordenadora'));
    fireEvent.click(screen.getByRole('button', { name: 'Trocar coordenadores' }));
    expect(caixa()).toHaveValue('Eva Coordenadora, Dora Coordenadora');
    const grupo = screen.getByRole('radiogroup', { name: ACOMPANHA });
    expect(within(grupo).getByLabelText('Não')).not.toBeChecked();

    salvar();
    await waitFor(() =>
      expect(message.error).toHaveBeenCalledWith('Responda se o coordenador responsável vai acompanhar o evento.'),
    );
    expect(updateSolicitacaoMock).not.toHaveBeenCalled();

    fireEvent.click(within(grupo).getByLabelText('Sim'));
    salvar();
    await waitFor(() => expect(updateSolicitacaoMock).toHaveBeenCalled());
    const payload = updateSolicitacaoMock.mock.calls[0][1];
    expect(payload.coordenador).toBe(5);
    expect(payload.coordenador_acompanha).toBe(true);
    expect(payload.extra_participants.coord_acompanha_ids).toEqual([8]);
  });

  test('caixa vazia num evento com responsável não salva', async () => {
    renderPage();
    await waitFor(() => expect(caixa()).toHaveValue('Ana Coordenadora, Dora Coordenadora'));
    fireEvent.click(screen.getByRole('button', { name: 'Trocar coordenadores' }));
    salvar();
    await waitFor(() => expect(message.error).toHaveBeenCalledWith('Escolha o coordenador responsável pelo evento.'));
    expect(updateSolicitacaoMock).not.toHaveBeenCalled();
  });

  // Evento antigo sem `coordenador` gravado: para o backend o responsável é quem criou
  // (`coordenador_id or usuario_id`). A linha COORD_ACOMPANHA que repete quem criou não vira outra tag.
  const ANTIGO = {
    ...SOLICITACAO,
    coordenador: null,
    coordenador_nome: null,
    participations: [
      { role: 'COORDENADOR', usuario: pessoa(1, 'Ana', 'Coordenadora') },
      { role: 'FORMADOR', usuario: pessoa(99, 'Bruno', 'Formador') },
      { role: 'COORD_ACOMPANHA', usuario: pessoa(8, 'Dora', 'Coordenadora') },
      { role: 'COORD_ACOMPANHA', usuario: pessoa(1, 'Ana', 'Coordenadora') },
    ],
  };

  test('evento antigo sem responsável gravado: quem criou é o 1º da caixa, sem repetir', async () => {
    getSolicitacaoMock.mockResolvedValue(ANTIGO);
    renderPage();
    await waitFor(() => expect(caixa()).toHaveValue('Ana Coordenadora, Dora Coordenadora'));
  });

  test('evento antigo salvo sem mexer não ganha `coordenador` e manda os mesmos demais', async () => {
    getSolicitacaoMock.mockResolvedValue(ANTIGO);
    renderPage();
    await waitFor(() => expect(caixa()).toHaveValue('Ana Coordenadora, Dora Coordenadora'));
    salvar();
    await waitFor(() => expect(updateSolicitacaoMock).toHaveBeenCalled());
    const payload = updateSolicitacaoMock.mock.calls[0][1];
    expect(payload).not.toHaveProperty('coordenador');
    expect(payload.coordenador_acompanha).toBe(false);
    expect(payload.extra_participants.coord_acompanha_ids).toEqual([8]);
  });

  test('evento antigo com outro 1º na caixa manda o novo responsável', async () => {
    getSolicitacaoMock.mockResolvedValue(ANTIGO);
    novaLista.value = [
      { id: 8, label: 'Dora Coordenadora' },
      { id: 1, label: 'Ana Coordenadora' },
    ];
    renderPage();
    await waitFor(() => expect(caixa()).toHaveValue('Ana Coordenadora, Dora Coordenadora'));
    fireEvent.click(screen.getByRole('button', { name: 'Trocar coordenadores' }));
    fireEvent.click(within(screen.getByRole('radiogroup', { name: ACOMPANHA })).getByLabelText('Não'));
    salvar();
    await waitFor(() => expect(updateSolicitacaoMock).toHaveBeenCalled());
    const payload = updateSolicitacaoMock.mock.calls[0][1];
    expect(payload.coordenador).toBe(8);
    expect(payload.extra_participants.coord_acompanha_ids).toEqual([1]);
  });

  test('evento antigo sem a linha COORDENADOR de quem criou: o nome vem de `coordenador_nome`', async () => {
    // Sem `coordenador`, o detalhe já devolve em `coordenador_nome` o nome de quem criou.
    getSolicitacaoMock.mockResolvedValue({
      ...ANTIGO,
      coordenador_nome: 'Ana Coordenadora',
      participations: ANTIGO.participations.filter((p) => p.role !== 'COORDENADOR'),
    });
    renderPage();
    await waitFor(() => expect(caixa()).toHaveValue('Ana Coordenadora, Dora Coordenadora'));
  });

  test('evento antigo com a caixa esvaziada não salva', async () => {
    getSolicitacaoMock.mockResolvedValue(ANTIGO);
    renderPage();
    await waitFor(() => expect(caixa()).toHaveValue('Ana Coordenadora, Dora Coordenadora'));
    fireEvent.click(screen.getByRole('button', { name: 'Trocar coordenadores' }));
    salvar();
    await waitFor(() => expect(message.error).toHaveBeenCalledWith('Escolha o coordenador responsável pelo evento.'));
    expect(updateSolicitacaoMock).not.toHaveBeenCalled();
  });

  test('o erro do servidor na lista aparece', async () => {
    const motivo = 'Cada coordenador precisa ser coordenador da gerência do projeto.';
    updateSolicitacaoMock.mockRejectedValue({
      response: { status: 400, data: { code: 'INVALID', detail: 'Erro de validação.', errors: { coord_acompanha_ids: [motivo] } } },
    });
    renderPage();
    await waitFor(() => expect(caixa()).toHaveValue('Ana Coordenadora, Dora Coordenadora'));
    salvar();
    await waitFor(() => expect(message.error).toHaveBeenCalledWith(motivo));
  });
});
