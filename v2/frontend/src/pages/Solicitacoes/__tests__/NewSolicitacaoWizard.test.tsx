import { useEffect } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

const {
  createSolicitacaoMock,
  getMeMock,
  lookupMunicipiosWithFiltersMock,
  lookupProjetosMock,
  lookupTiposEventoMock,
  navigateMock,
} = vi.hoisted(() => ({
  createSolicitacaoMock: vi.fn(),
  getMeMock: vi.fn(),
  lookupMunicipiosWithFiltersMock: vi.fn(),
  lookupProjetosMock: vi.fn(),
  lookupTiposEventoMock: vi.fn(),
  navigateMock: vi.fn(),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock('../../../api/solicitacoes', () => ({
  createSolicitacao: createSolicitacaoMock,
}));

vi.mock('../../../api/availability', () => ({
  getMe: getMeMock,
}));

vi.mock('../../../api/lookup', () => ({
  lookupMunicipiosWithFilters: lookupMunicipiosWithFiltersMock,
  lookupProjetos: lookupProjetosMock,
  lookupTiposEvento: lookupTiposEventoMock,
}));

vi.mock('../../../components/DateTimeRange', () => ({
  default: () => <div data-testid="datetime-range">DateTimeRange</div>,
}));

vi.mock('../../../components/FormadoresPicker', () => ({
  default: () => <div data-testid="formadores-picker">FormadoresPicker</div>,
}));

vi.mock('../../../components/CoordenadoresPicker', () => ({
  default: () => <div data-testid="coordenadores-picker">CoordenadoresPicker</div>,
}));

vi.mock('../../../components/ComboBox', () => ({
  default: ({
    placeholder = '',
    lookupFunction,
    onChange,
    disabled = false,
  }: {
    placeholder?: string;
    lookupFunction: (query: string) => Promise<unknown[]>;
    onChange?: (item: unknown) => void;
    disabled?: boolean;
  }) => {
    useEffect(() => {
      void lookupFunction('');
    }, [lookupFunction]);

    return (
      <button
        type="button"
        data-testid={placeholder}
        disabled={disabled}
        onClick={() => {
          if (placeholder.includes('projeto')) {
            onChange?.({ id: 123, label: 'Projeto X', fluxo: 'SUPER' });
            return;
          }
          onChange?.({ id: 456, label: 'Fortaleza - CE' });
        }}
      >
        {placeholder}
      </button>
    );
  },
}));

import NewSolicitacaoWizard from '../NewSolicitacaoWizard';

describe('NewSolicitacaoWizard - filtros dependentes municipio/projeto', () => {
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
    lookupProjetosMock.mockResolvedValue([]);
    lookupTiposEventoMock.mockResolvedValue([]);
    lookupMunicipiosWithFiltersMock.mockResolvedValue([]);
    getMeMock.mockResolvedValue({ is_superuser: false });
  });

  test('usuário comum consulta municípios elegíveis por projeto e mostra estado vazio', async () => {
    render(
      <MemoryRouter>
        <NewSolicitacaoWizard />
      </MemoryRouter>
    );

    const municipioDisabledButton = await screen.findByRole('button', {
      name: 'Selecione um projeto para carregar municípios elegíveis',
    });
    expect(municipioDisabledButton).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: 'Busque ou selecione um projeto' }));

    await waitFor(() => {
      expect(lookupMunicipiosWithFiltersMock).toHaveBeenCalledWith({
        q: '',
        com_compra: true,
        projeto_id: 123,
      });
    });

    expect(await screen.findByText('Sem municípios elegíveis')).toBeInTheDocument();
    expect(
      screen.getByText('Não há municípios com compra registrada para o projeto selecionado.')
    ).toBeInTheDocument();
  });

  test('superuser mantém lookup de municípios sem filtro de compra/projeto', async () => {
    getMeMock.mockResolvedValue({ is_superuser: true });
    lookupMunicipiosWithFiltersMock.mockResolvedValue([{ id: 1, label: 'Fortaleza - CE' }]);

    render(
      <MemoryRouter>
        <NewSolicitacaoWizard />
      </MemoryRouter>
    );

    const municipioButton = await screen.findByRole('button', {
      name: 'Busque ou selecione um município',
    });
    expect(municipioButton).not.toBeDisabled();

    await waitFor(() => {
      expect(lookupMunicipiosWithFiltersMock).toHaveBeenCalled();
    });

    const firstCallArg = lookupMunicipiosWithFiltersMock.mock.calls[0][0];
    expect(firstCallArg.q).toBe('');
    expect(firstCallArg.com_compra).toBeUndefined();
    expect(firstCallArg.projeto_id).toBeUndefined();

    fireEvent.click(screen.getByRole('button', { name: 'Busque ou selecione um projeto' }));

    await waitFor(() => {
      const lastCallArg =
        lookupMunicipiosWithFiltersMock.mock.calls[lookupMunicipiosWithFiltersMock.mock.calls.length - 1][0];
      expect(lastCallArg.q).toBe('');
      expect(lastCallArg.com_compra).toBeUndefined();
      expect(lastCallArg.projeto_id).toBeUndefined();
    });

    expect(screen.queryByText('Sem municípios elegíveis')).not.toBeInTheDocument();
  });
});
