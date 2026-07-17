import { useEffect } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

const {
  createSolicitacaoMock,
  getMeMock,
  checkAvailabilityManyMock,
  lookupMunicipiosWithFiltersMock,
  lookupProjetosMock,
  lookupTiposEventoMock,
  navigateMock,
} = vi.hoisted(() => ({
  createSolicitacaoMock: vi.fn(),
  getMeMock: vi.fn(),
  checkAvailabilityManyMock: vi.fn(),
  lookupMunicipiosWithFiltersMock: vi.fn(),
  lookupProjetosMock: vi.fn(),
  lookupTiposEventoMock: vi.fn(),
  navigateMock: vi.fn(),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
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
}));

// Stubs que EMITEM onChange (o real dispara ao selecionar). Sem isso o gatilho
// da feature — "selecionar formador + data" — é intestável.
vi.mock('../../../components/DateTimeRange', () => ({
  default: ({ onChange }: { onChange?: (v: unknown) => void }) => (
    <button
      type="button"
      data-testid="set-date"
      onClick={() => onChange?.({ date: '2026-08-01', start: '09:00', end: '11:00' })}
    >
      set-date
    </button>
  ),
}));
vi.mock('../../../components/FormadoresPicker', () => ({
  default: ({ onChange }: { onChange?: (v: unknown) => void }) => (
    <button
      type="button"
      data-testid="pick-formador"
      onClick={() => onChange?.([{ id: 99, email: 'f@x.com', label: 'Bruno Formador' }])}
    >
      pick-formador
    </button>
  ),
}));
vi.mock('../../../components/CoordenadoresPicker', () => ({
  default: () => <div data-testid="coordenadores-picker">CoordenadoresPicker</div>,
}));

function MockComboBox({
  placeholder = '',
  lookupFunction,
  onChange,
}: {
  placeholder?: string;
  lookupFunction: (q: string) => Promise<unknown[]>;
  onChange?: (item: unknown) => void;
  disabled?: boolean;
}) {
  useEffect(() => {
    void lookupFunction('');
  }, [lookupFunction]);
  const testid = placeholder.includes('projeto')
    ? 'cb-projeto'
    : placeholder.includes('tipo')
      ? 'cb-tipo'
      : 'cb-municipio';
  return (
    <button
      type="button"
      data-testid={testid}
      onClick={() => {
        if (testid === 'cb-projeto') onChange?.({ id: 123, label: 'Projeto X', fluxo: 'SUPER' });
        else if (testid === 'cb-tipo') onChange?.({ id: 789, label: 'Formação' });
        else onChange?.({ id: 456, label: 'Fortaleza - CE' });
      }}
    >
      {testid}
    </button>
  );
}
vi.mock('../../../components/ComboBox', () => ({ default: MockComboBox }));

import NewSolicitacaoWizard from '../NewSolicitacaoWizard';

async function irParaParticipantesESelecionarFormador(): Promise<void> {
  await screen.findByTestId('cb-projeto');
  fireEvent.click(screen.getByTestId('cb-projeto'));
  await waitFor(() => screen.getByTestId('cb-tipo'));
  fireEvent.click(screen.getByTestId('cb-tipo'));
  fireEvent.click(screen.getByTestId('cb-municipio'));
  fireEvent.click(screen.getByTestId('set-date'));
  fireEvent.click(screen.getByRole('button', { name: /Ir para proximo passo/i }));
  await screen.findByTestId('pick-formador');
  fireEvent.click(screen.getByTestId('pick-formador'));
}

const RESP_CONFLITO = {
  ok: false,
  results: [
    { usuario_id: 1, ok: true, conflicts: [] },
    {
      usuario_id: 99,
      ok: false,
      conflicts: [{ code: 'X', title: 'Sobreposição', detail: 'Conflita com evento aprovado #5', ref_id: 5 }],
    },
  ],
};

describe('NewSolicitacaoWizard — aviso antecipado de disponibilidade (#1452)', () => {
  beforeEach(() => {
    if (!window.matchMedia) {
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation((query: string) => ({
          matches: false,
          media: query,
          onchange: null,
          addListener: vi.fn(),
          removeListener: vi.fn(),
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
          dispatchEvent: vi.fn(),
        })),
      });
    }
    vi.clearAllMocks();
    lookupProjetosMock.mockResolvedValue([{ id: 123, label: 'Projeto X', fluxo: 'SUPER' }]);
    lookupTiposEventoMock.mockResolvedValue([{ id: 789, label: 'Formação' }]);
    lookupMunicipiosWithFiltersMock.mockResolvedValue([{ id: 456, label: 'Fortaleza - CE' }]);
    getMeMock.mockResolvedValue({ is_superuser: true, id: 1, name: 'Ana Criadora', username: 'ana' });
    checkAvailabilityManyMock.mockResolvedValue({ ok: true, results: [] });
  });

  test('selecionar formador + data dispara check-many com o criador incluso e deduplicado', async () => {
    render(
      <MemoryRouter>
        <NewSolicitacaoWizard />
      </MemoryRouter>
    );
    await irParaParticipantesESelecionarFormador();

    await waitFor(() => expect(checkAvailabilityManyMock).toHaveBeenCalled());
    const arg = checkAvailabilityManyMock.mock.calls[0][0];
    expect(arg.usuarios_ids).toEqual([1, 99]); // criador (1) + formador (99)
    expect(arg.municipio_id).toBe(456);
    expect(arg.inicio).toBeTruthy();
  });

  test('conflito confirmado: mostra o formador e DESABILITA o Próximo', async () => {
    checkAvailabilityManyMock.mockResolvedValue(RESP_CONFLITO);
    render(
      <MemoryRouter>
        <NewSolicitacaoWizard />
      </MemoryRouter>
    );
    await irParaParticipantesESelecionarFormador();

    expect(await screen.findByText('Não é possível criar o evento')).toBeInTheDocument();
    expect(screen.getByText('Bruno Formador')).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Ir para proximo passo/i })).toBeDisabled()
    );
  });

  test('sem conflito: nenhum alerta de bloqueio e Próximo habilitado', async () => {
    checkAvailabilityManyMock.mockResolvedValue({ ok: true, results: [] });
    render(
      <MemoryRouter>
        <NewSolicitacaoWizard />
      </MemoryRouter>
    );
    await irParaParticipantesESelecionarFormador();

    await waitFor(() => expect(checkAvailabilityManyMock).toHaveBeenCalled());
    expect(screen.queryByText('Não é possível criar o evento')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Ir para proximo passo/i })).not.toBeDisabled();
  });

  test('checagem falha (500): fail-open — Próximo continua habilitado', async () => {
    checkAvailabilityManyMock.mockRejectedValue(Object.assign(new Error('boom'), { status: 500 }));
    render(
      <MemoryRouter>
        <NewSolicitacaoWizard />
      </MemoryRouter>
    );
    await irParaParticipantesESelecionarFormador();

    await waitFor(() => expect(checkAvailabilityManyMock).toHaveBeenCalled());
    expect(screen.queryByText('Não é possível criar o evento')).not.toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Ir para proximo passo/i })).not.toBeDisabled()
    );
  });

  test('avançar sem tocar em Coordenadores NÃO quebra o wizard (guarda do P0)', async () => {
    render(
      <MemoryRouter>
        <NewSolicitacaoWizard />
      </MemoryRouter>
    );
    await irParaParticipantesESelecionarFormador();
    // sai do step 1 SEM ter tocado no CoordenadoresPicker
    fireEvent.click(screen.getByRole('button', { name: /Ir para proximo passo/i }));
    // Se o P0 (coordenadores undefined -> .length) não estivesse guardado, o render
    // do resumo estouraria e desmontaria a árvore. Chegar ao passo seguinte prova o fix.
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Voltar para passo anterior/i })).toBeInTheDocument()
    );
  });
});
