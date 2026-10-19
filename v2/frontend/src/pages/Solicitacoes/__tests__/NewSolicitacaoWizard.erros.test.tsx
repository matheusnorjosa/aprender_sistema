/**
 * Nova Solicitação — erros que a pessoa consegue corrigir (item 36, 19/10/2026).
 *
 * - Fim antes (ou igual) do início não passa do passo 1: a mensagem fica junto do horário.
 * - "Próximo" com campo faltando leva o foco ao primeiro campo com erro (não é clique mudo).
 * - Recusa do backend por campo mostra o motivo de `errors`, não o genérico "Erro de validação.".
 * - Sem conexão, a mensagem diz isso, e não "Verifique os dados".
 */
import { useEffect } from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router';
import message from 'antd/es/message';

const {
  createSolicitacaoMock,
  getMeMock,
  checkAvailabilityManyMock,
  lookupMunicipiosWithFiltersMock,
  lookupProjetosMock,
  lookupTiposEventoMock,
  navigateMock,
  horario,
} = vi.hoisted(() => ({
  createSolicitacaoMock: vi.fn(),
  getMeMock: vi.fn(),
  checkAvailabilityManyMock: vi.fn(),
  lookupMunicipiosWithFiltersMock: vi.fn(),
  lookupProjetosMock: vi.fn(),
  lookupTiposEventoMock: vi.fn(),
  navigateMock: vi.fn(),
  horario: { atual: { date: '2026-08-01', start: '09:00', end: '11:00' } },
}));

vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return { ...actual, useNavigate: () => navigateMock };
});
vi.mock('../../../api/solicitacoes', () => ({ createSolicitacao: createSolicitacaoMock }));
vi.mock('../../../api/availability', () => ({
  getMe: getMeMock,
  checkAvailabilityMany: checkAvailabilityManyMock,
}));
vi.mock('../../../api/lookup', () => ({
  lookupMunicipiosWithFilters: lookupMunicipiosWithFiltersMock,
  lookupProjetos: lookupProjetosMock,
  lookupTiposEvento: lookupTiposEventoMock,
  lookupUsuarios: vi.fn().mockResolvedValue([]),
}));
vi.mock('../../../components/DateTimeRange', () => ({
  default: ({ onChange, erro }: { onChange?: (v: unknown) => void; erro?: string | null }) => (
    <div>
      <button type="button" data-testid="set-date" onClick={() => onChange?.(horario.atual)}>
        set-date
      </button>
      {erro ? <p data-testid="erro-horario">{erro}</p> : null}
    </div>
  ),
}));
vi.mock('../../../components/FormadoresPicker', () => ({
  default: ({ onChange }: { onChange?: (v: unknown) => void }) => (
    <button
      type="button"
      data-testid="pick-formador"
      onClick={() => onChange?.([{ id: 99, label: 'Bruno Formador', avaliavel: false }])}
    >
      pick-formador
    </button>
  ),
}));

function MockComboBox({
  placeholder = '',
  lookupFunction,
  onChange,
  id,
}: {
  placeholder?: string;
  lookupFunction: (q: string) => Promise<unknown[]>;
  onChange?: (item: unknown) => void;
  id?: string;
}) {
  useEffect(() => {
    void lookupFunction('');
  }, [lookupFunction]);
  const testid = placeholder.includes('respons')
    ? 'cb-responsavel'
    : placeholder.includes('munic')
      ? 'cb-municipio'
      : placeholder.includes('projeto')
        ? 'cb-projeto'
        : 'cb-tipo';
  return (
    <button
      type="button"
      id={id}
      data-testid={testid}
      onClick={() => {
        if (testid === 'cb-projeto') onChange?.({ id: 123, label: 'Projeto X', fluxo: 'NAO_SUPER', responsavel_padrao: true });
        else if (testid === 'cb-tipo') onChange?.({ id: 789, label: 'Formação' });
        else if (testid === 'cb-responsavel') onChange?.({ id: 7, label: 'Carla Coordenadora' });
        else onChange?.({ id: 456, label: 'Fortaleza - CE' });
      }}
    >
      {testid}
    </button>
  );
}
vi.mock('../../../components/ComboBox', () => ({ default: MockComboBox }));

import NewSolicitacaoWizard from '../NewSolicitacaoWizard';

function renderWizard(): void {
  render(
    <MemoryRouter>
      <NewSolicitacaoWizard />
    </MemoryRouter>
  );
}

const proximo = (): HTMLElement => screen.getByRole('button', { name: /Ir para proximo passo/i });

async function preencherPasso1(): Promise<void> {
  await screen.findByTestId('cb-projeto');
  fireEvent.click(screen.getByTestId('cb-projeto'));
  await waitFor(() => screen.getByTestId('cb-tipo'));
  fireEvent.click(screen.getByTestId('cb-tipo'));
  fireEvent.click(screen.getByTestId('cb-municipio'));
  fireEvent.click(screen.getByTestId('set-date'));
}

async function irParaConfirmacao(): Promise<void> {
  await preencherPasso1();
  fireEvent.click(proximo());
  fireEvent.click(await screen.findByTestId('pick-formador'));
  fireEvent.click(within(screen.getByRole('radiogroup', { name: /vai acompanhar o evento/ })).getByLabelText('Não'));
  await waitFor(() => expect(proximo()).not.toBeDisabled());
  fireEvent.click(proximo());
  await screen.findByLabelText('Local do Evento');
  fireEvent.click(proximo());
  await screen.findByText('Revise sua solicitação');
}

// Percorrer o assistente com antd leva ~3 s por teste isolado; na suíte inteira passa dos 5 s padrão.
describe('NewSolicitacaoWizard — erros que a pessoa consegue corrigir (item 36)', { timeout: 20000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(message, 'error').mockImplementation(vi.fn()).mockClear();
    horario.atual = { date: '2026-08-01', start: '09:00', end: '11:00' };
    lookupProjetosMock.mockResolvedValue([]);
    lookupTiposEventoMock.mockResolvedValue([]);
    lookupMunicipiosWithFiltersMock.mockResolvedValue([]);
    getMeMock.mockResolvedValue({ id: 1, name: 'Ana Coordenadora', username: 'ana', is_superuser: false });
    checkAvailabilityManyMock.mockResolvedValue({ ok: true, results: [] });
    createSolicitacaoMock.mockResolvedValue({ id: 1 });
  });

  test('fim antes do início não passa do passo 1 e a mensagem fica junto do horário', async () => {
    horario.atual = { date: '2026-08-01', start: '14:00', end: '10:00' };
    renderWizard();
    await preencherPasso1();
    fireEvent.click(proximo());
    expect(await screen.findByTestId('erro-horario')).toHaveTextContent('O horário de fim precisa ser depois do início.');
    expect(screen.queryByTestId('pick-formador')).not.toBeInTheDocument();
  });

  test('fim igual ao início também não passa', async () => {
    horario.atual = { date: '2026-08-01', start: '10:00', end: '10:00' };
    renderWizard();
    await preencherPasso1();
    fireEvent.click(proximo());
    expect(await screen.findByTestId('erro-horario')).toHaveTextContent('O horário de fim precisa ser depois do início.');
  });

  test('sem data, o erro aparece junto do horário e também nos outros campos que faltam', async () => {
    renderWizard();
    await screen.findByTestId('cb-projeto');
    fireEvent.click(proximo());
    expect(await screen.findByTestId('erro-horario')).toHaveTextContent('Escolha a data e os horários de início e de fim do evento.');
    expect(await screen.findByText('Por favor selecione um projeto')).toBeInTheDocument();
  });

  test('"Próximo" com campo faltando leva o foco ao primeiro campo com erro', async () => {
    renderWizard();
    await screen.findByTestId('cb-projeto');
    fireEvent.click(screen.getByTestId('set-date'));
    fireEvent.click(proximo());
    await screen.findByText('Por favor selecione um projeto');
    await waitFor(() => expect(screen.getByTestId('cb-projeto')).toHaveFocus());
  });

  test('recusa do backend por campo mostra o motivo, não "Erro de validação."', async () => {
    createSolicitacaoMock.mockRejectedValueOnce({
      response: {
        status: 400,
        data: {
          detail: 'Erro de validação.',
          errors: { municipio: ['Não há compra que libere este projeto neste município.'] },
        },
      },
    });
    renderWizard();
    await irParaConfirmacao();
    fireEvent.click(screen.getByRole('button', { name: /Confirmar Solicitação/i }));
    await waitFor(() =>
      expect(message.error).toHaveBeenCalledWith('Não há compra que libere este projeto neste município.')
    );
    expect(message.error).not.toHaveBeenCalledWith('Erro de validação.');
  });

  test('sem conexão, a mensagem diz isso', async () => {
    createSolicitacaoMock.mockRejectedValueOnce(new TypeError('Sem conexão com o servidor.'));
    renderWizard();
    await irParaConfirmacao();
    fireEvent.click(screen.getByRole('button', { name: /Confirmar Solicitação/i }));
    await waitFor(() => expect(message.error).toHaveBeenCalledWith('Sem conexão com o servidor.'));
  });
});
