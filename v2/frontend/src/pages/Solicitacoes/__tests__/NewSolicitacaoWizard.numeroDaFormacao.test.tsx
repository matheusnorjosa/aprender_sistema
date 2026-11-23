/**
 * Nova Solicitação — CON-09: "Nº da formação" obrigatório quando o tipo escolhido é de formação.
 *
 * A marca vem do servidor (`de_formacao` no lookup de tipos); a tela não compara nome de tipo. Com a marca, o
 * campo é obrigatório (aria-required), o envio sem o número para no cartão com o motivo no resumo e o foco no
 * campo. Sem a marca, o campo segue livre (até só com espaços). Trocar para um tipo sem a marca tira o erro do campo.
 */
import { useEffect } from 'react';
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderNoRoteador } from '../../../test/comRoteador';
import { MSG_NUMERO_DA_FORMACAO } from '../evento';
import { botaoDoTexto, grupoDaPergunta, PERGUNTA_ACOMPANHA } from './localizadores';

const { getMeMock, checkAvailabilityManyMock, createSolicitacoesEmLoteMock, tipo } = vi.hoisted(() => ({
  getMeMock: vi.fn(),
  checkAvailabilityManyMock: vi.fn(),
  createSolicitacoesEmLoteMock: vi.fn(),
  tipo: { atual: { id: 789, label: 'Presencial', kind: 'tipo_evento', de_formacao: true } },
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
        else if (testid === 'cb-tipo') onChange?.(tipo.atual);
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

async function preencherMenosONumero(): Promise<HTMLElement> {
  renderNoRoteador(<NewSolicitacaoWizard />);
  await screen.findByTestId('cb-projeto');
  fireEvent.click(screen.getByTestId('cb-projeto'));
  fireEvent.click(screen.getByTestId('cb-tipo'));
  fireEvent.click(screen.getByTestId('cb-municipio'));
  fireEvent.click(screen.getByTestId('set-date'));
  fireEvent.click(screen.getByTestId('pick-formador'));
  fireEvent.click(within(grupoDaPergunta(PERGUNTA_ACOMPANHA)).getByLabelText('Não'));
  return screen.getByLabelText(/Nº da formação/);
}

describe('Nova Solicitação — Nº da formação no evento de formação (CON-09)', { timeout: 20000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    tipo.atual = { id: 789, label: 'Presencial', kind: 'tipo_evento', de_formacao: true };
    getMeMock.mockResolvedValue({ id: 1, name: 'Ana Coordenadora', username: 'ana', is_superuser: false });
    checkAvailabilityManyMock.mockResolvedValue({ ok: true, results: [] });
    createSolicitacoesEmLoteMock.mockResolvedValue({ eventos: [{ indice: 0, id: 1, status: 'aprovado' }] });
  });

  test('tipo de formação sem o número: não envia, o motivo vai ao resumo e o foco ao campo', async () => {
    const numero = await preencherMenosONumero();
    expect(numero).toHaveAttribute('aria-required', 'true');

    fireEvent.click(botaoDoTexto('Criar solicitação'));

    await waitFor(() => expect(numero).toHaveFocus(), ESPERA_VALIDACAO);
    // O resumo do topo (a região viva da página) diz o motivo.
    const resumo = screen.getByText(/Corrija antes de criar a solicitação/).closest('[role="alert"]');
    expect(resumo?.textContent).toContain(`Evento 1: ${MSG_NUMERO_DA_FORMACAO}`);
    expect(numero).toHaveAttribute('aria-invalid', 'true');
    expect(createSolicitacoesEmLoteMock).not.toHaveBeenCalled();
  });

  test('tipo de formação com o número: envia', async () => {
    const numero = await preencherMenosONumero();
    fireEvent.change(numero, { target: { value: '4' } });

    fireEvent.click(botaoDoTexto('Criar solicitação'));

    await waitFor(() => expect(createSolicitacoesEmLoteMock).toHaveBeenCalledTimes(1), ESPERA_VALIDACAO);
    expect(createSolicitacoesEmLoteMock.mock.calls[0]?.[0]?.[0]).toMatchObject({ encontro: '4' });
  });

  test('tipo sem a marca: o número segue livre', async () => {
    tipo.atual = { id: 790, label: 'Reunião', kind: 'tipo_evento', de_formacao: false };
    const numero = await preencherMenosONumero();
    expect(numero).not.toHaveAttribute('aria-required');

    fireEvent.click(botaoDoTexto('Criar solicitação'));

    await waitFor(() => expect(createSolicitacoesEmLoteMock).toHaveBeenCalledTimes(1), ESPERA_VALIDACAO);
  });

  // TELA-1: o "só espaços" vale só quando o campo é obrigatório.
  test('tipo sem a marca com o número só de espaços: envia', async () => {
    tipo.atual = { id: 790, label: 'Reunião', kind: 'tipo_evento', de_formacao: false };
    const numero = await preencherMenosONumero();
    fireEvent.change(numero, { target: { value: ' ' } });

    fireEvent.click(botaoDoTexto('Criar solicitação'));

    await waitFor(() => expect(createSolicitacoesEmLoteMock).toHaveBeenCalledTimes(1), ESPERA_VALIDACAO);
    expect(numero).not.toHaveAttribute('aria-invalid');
  });

  test('trocar para um tipo sem a marca tira o erro do número', async () => {
    const numero = await preencherMenosONumero();
    fireEvent.click(botaoDoTexto('Criar solicitação'));
    await waitFor(() => expect(numero).toHaveAttribute('aria-invalid', 'true'), ESPERA_VALIDACAO);

    tipo.atual = { id: 790, label: 'Reunião', kind: 'tipo_evento', de_formacao: false };
    fireEvent.click(screen.getByTestId('cb-tipo'));

    await waitFor(() => expect(numero).not.toHaveAttribute('aria-invalid'), ESPERA_VALIDACAO);
    expect(numero).not.toHaveAttribute('aria-required');
  });
});
