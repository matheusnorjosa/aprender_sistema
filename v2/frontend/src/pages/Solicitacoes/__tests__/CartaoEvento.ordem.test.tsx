/**
 * Cartão do evento (Nova Solicitação) — a ordem do resumo de erros e do foco é a da tela.
 *
 * "Nº da formação" fica na 1ª linha do cartão, depois de Projeto e Tipo de Evento e antes do
 * Município. Com os dois inválidos, o resumo lista "Nº da formação" antes de Município e o foco vai a ele.
 */
import { useEffect } from 'react';
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderNoRoteador } from '../../../test/comRoteador';
import { botaoDoTexto, grupoDaPergunta, PERGUNTA_ACOMPANHA } from './localizadores';

const { getMeMock, checkAvailabilityManyMock, createSolicitacoesEmLoteMock } = vi.hoisted(() => ({
  getMeMock: vi.fn(),
  checkAvailabilityManyMock: vi.fn(),
  createSolicitacoesEmLoteMock: vi.fn(),
}));

vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return { ...actual, useNavigate: () => vi.fn() };
});
vi.mock('../../../api/solicitacoes', () => ({ createSolicitacoesEmLote: createSolicitacoesEmLoteMock }));
vi.mock('../../../api/availability', () => ({
  getMe: getMeMock,
  checkAvailabilityMany: checkAvailabilityManyMock,
}));
vi.mock('../../../api/lookup', () => ({
  lookupMunicipiosWithFilters: vi.fn().mockResolvedValue([]),
  lookupProjetos: vi.fn().mockResolvedValue([]),
  lookupTiposEvento: vi.fn().mockResolvedValue([]),
  lookupUsuarios: vi.fn().mockResolvedValue([]),
}));
vi.mock('../../../components/DateTimeRange', () => ({
  default: ({ onChange }: { onChange?: (v: unknown) => void }) => (
    <button type="button" data-testid="set-date" onClick={() => onChange?.({ date: '2099-08-01', start: '09:00', end: '11:00' })}>
      set-date
    </button>
  ),
}));
vi.mock('../../../components/FormadoresPicker', () => ({
  default: ({ onChange }: { onChange?: (v: unknown) => void }) => (
    <button type="button" data-testid="pick-formador" onClick={() => onChange?.([{ id: 99, label: 'Bruno Formador', avaliavel: false }])}>
      pick-formador
    </button>
  ),
}));
vi.mock('../../../components/CoordenadoresPicker', () => ({
  default: ({ onChange, id }: { onChange?: (v: unknown) => void; id?: string }) => (
    <button type="button" id={id} data-testid="cb-responsavel" onClick={() => onChange?.([{ id: 7, label: 'Carla Coordenadora' }])}>
      cb-responsavel
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
  const testid = placeholder.includes('munic') ? 'cb-municipio' : placeholder.includes('projeto') ? 'cb-projeto' : 'cb-tipo';
  return (
    <button
      type="button"
      id={id}
      data-testid={testid}
      onClick={() => {
        if (testid === 'cb-projeto') onChange?.({ id: 123, label: 'Projeto X', fluxo: 'NAO_SUPER', responsavel_padrao: true });
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

const ESPERA_VALIDACAO = { timeout: 5000 };

describe('Cartão do evento — ordem do resumo de erros', { timeout: 20000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getMeMock.mockResolvedValue({ id: 1, name: 'Ana Coordenadora', username: 'ana', is_superuser: false });
    checkAvailabilityManyMock.mockResolvedValue({ ok: true, results: [] });
  });

  test('"Nº da formação" e Município inválidos: o resumo e o foco seguem a ordem da tela', async () => {
    renderNoRoteador(<NewSolicitacaoWizard />);
    await screen.findByTestId('cb-projeto');
    fireEvent.click(screen.getByTestId('cb-projeto'));
    fireEvent.click(screen.getByTestId('cb-tipo'));
    fireEvent.click(screen.getByTestId('set-date'));
    fireEvent.click(screen.getByTestId('pick-formador'));
    fireEvent.click(within(grupoDaPergunta(PERGUNTA_ACOMPANHA)).getByLabelText('Não'));
    const numero = screen.getByLabelText('Nº da formação');
    fireEvent.change(numero, { target: { value: '9'.repeat(101) } });

    fireEvent.click(botaoDoTexto('Criar solicitação'));

    await waitFor(() => expect(numero).toHaveFocus(), ESPERA_VALIDACAO);
    const resumo = screen.getByRole('alert');
    const texto = resumo.textContent ?? '';
    expect(texto).toContain('Máximo 100 caracteres');
    expect(texto).toContain('Por favor selecione um município');
    expect(texto.indexOf('Máximo 100 caracteres')).toBeLessThan(texto.indexOf('Por favor selecione um município'));
    expect(createSolicitacoesEmLoteMock).not.toHaveBeenCalled();
  });
});
