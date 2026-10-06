/**
 * Nova Solicitação — coordenador responsável e as duas perguntas (decisão do dono, 05/10/2026).
 *
 * - A lista "Coordenadores Acompanhantes" saiu; no lugar, "O coordenador responsável vai
 *   acompanhar o evento?" (Sim/Não, obrigatória).
 * - A prévia de agenda confere os formadores e o responsável só com "Sim".
 * - "Você pretende avaliar o formador nesse evento?" só aparece quando o projeto pergunta e há
 *   formador avaliável na lista; com "Sim", escolher qual formador.
 * - Quem cria sem a função Coordenador precisa escolher o responsável.
 */
import { useEffect } from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router';

const {
  createSolicitacaoMock,
  getMeMock,
  checkAvailabilityManyMock,
  lookupMunicipiosWithFiltersMock,
  lookupProjetosMock,
  lookupTiposEventoMock,
  navigateMock,
  formadoresEscolhidos,
} = vi.hoisted(() => ({
  createSolicitacaoMock: vi.fn(),
  getMeMock: vi.fn(),
  checkAvailabilityManyMock: vi.fn(),
  lookupMunicipiosWithFiltersMock: vi.fn(),
  lookupProjetosMock: vi.fn(),
  lookupTiposEventoMock: vi.fn(),
  navigateMock: vi.fn(),
  formadoresEscolhidos: { atual: [] as Array<{ id: number; label: string; avaliavel?: boolean }> },
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
    <button type="button" data-testid="pick-formador" onClick={() => onChange?.(formadoresEscolhidos.atual)}>
      pick-formador
    </button>
  ),
}));

let projetoEscolhido: Record<string, unknown> = {};

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
      data-testid={testid}
      onClick={() => {
        if (testid === 'cb-projeto') onChange?.(projetoEscolhido);
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

const COORDENADORA = { id: 1, name: 'Ana Coordenadora', username: 'ana', is_superuser: false, funcoes: ['Coordenador'] };
const SEM_FUNCAO_COORDENADOR = { id: 2, name: 'Davi Apoio', username: 'davi', is_superuser: false, funcoes: ['Apoio de Coordenação'] };
const AVALIAVEL = { id: 99, label: 'Bruno Formador', avaliavel: true };
const NAO_AVALIAVEL = { id: 98, label: 'Celia Coordenadora', avaliavel: false };

function renderWizard(): void {
  render(
    <MemoryRouter>
      <NewSolicitacaoWizard />
    </MemoryRouter>
  );
}

async function irParaParticipantes(): Promise<void> {
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

function responder(pergunta: RegExp, resposta: 'Sim' | 'Não'): void {
  fireEvent.click(within(screen.getByRole('radiogroup', { name: pergunta })).getByLabelText(resposta));
}

const ACOMPANHA = /O coordenador responsável vai acompanhar o evento\?/;
const AVALIAR = /Você pretende avaliar o formador nesse evento\?/;

// Percorrer o assistente com antd leva ~3 s por teste isolado; na suíte inteira passa dos 5 s padrão.
describe('NewSolicitacaoWizard — responsável e perguntas (05/10/2026)', { timeout: 20000 }, () => {
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
    projetoEscolhido = { id: 123, label: 'Projeto X', fluxo: 'NAO_SUPER', pergunta_avaliar_formador: true };
    formadoresEscolhidos.atual = [AVALIAVEL];
    lookupProjetosMock.mockResolvedValue([projetoEscolhido]);
    lookupTiposEventoMock.mockResolvedValue([{ id: 789, label: 'Formação' }]);
    lookupMunicipiosWithFiltersMock.mockResolvedValue([{ id: 456, label: 'Fortaleza - CE' }]);
    getMeMock.mockResolvedValue(COORDENADORA);
    checkAvailabilityManyMock.mockResolvedValue({ ok: true, results: [] });
    createSolicitacaoMock.mockResolvedValue({ id: 1 });
  });

  test('a lista de coordenadores acompanhantes saiu e a pergunta Sim/Não entrou', async () => {
    renderWizard();
    await irParaParticipantes();
    expect(screen.queryByText('Coordenadores Acompanhantes')).not.toBeInTheDocument();
    expect(screen.getByRole('radiogroup', { name: ACOMPANHA })).toBeInTheDocument();
  });

  test('não avança sem responder se o coordenador vai acompanhar', async () => {
    renderWizard();
    await irParaParticipantes();
    responder(AVALIAR, 'Não');
    fireEvent.click(screen.getByRole('button', { name: /Ir para proximo passo/i }));
    expect(await screen.findByText('Responda se o coordenador responsável vai acompanhar o evento.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Voltar para passo anterior/i })).toBeInTheDocument();
    expect(screen.getByTestId('pick-formador')).toBeInTheDocument();
  });

  test('prévia de agenda: o responsável só entra com Sim', async () => {
    renderWizard();
    await irParaParticipantes();
    responder(ACOMPANHA, 'Não');
    await waitFor(() => expect(checkAvailabilityManyMock).toHaveBeenCalled());
    expect(checkAvailabilityManyMock.mock.calls.at(-1)?.[0].usuarios_ids).toEqual([99]);

    responder(ACOMPANHA, 'Sim');
    await waitFor(() => expect(checkAvailabilityManyMock.mock.calls.at(-1)?.[0].usuarios_ids).toEqual([1, 99]));
  });

  test('pergunta de avaliar: aparece com formador avaliável e pede qual formador no Sim', async () => {
    renderWizard();
    await irParaParticipantes();
    expect(screen.getByRole('radiogroup', { name: AVALIAR })).toBeInTheDocument();
    expect(screen.queryByLabelText('Qual formador você pretende avaliar?')).not.toBeInTheDocument();
    responder(AVALIAR, 'Sim');
    expect(await screen.findByLabelText('Qual formador você pretende avaliar?')).toBeInTheDocument();
  });

  test('pergunta de avaliar some quando a gerência do projeto não pergunta', async () => {
    projetoEscolhido = { ...projetoEscolhido, pergunta_avaliar_formador: false };
    renderWizard();
    await irParaParticipantes();
    expect(screen.queryByRole('radiogroup', { name: AVALIAR })).not.toBeInTheDocument();
  });

  test('pergunta de avaliar some quando nenhum formador é avaliável (coordenador como formador)', async () => {
    formadoresEscolhidos.atual = [NAO_AVALIAVEL];
    renderWizard();
    await irParaParticipantes();
    expect(screen.queryByRole('radiogroup', { name: AVALIAR })).not.toBeInTheDocument();
  });

  test('quem não é coordenador precisa escolher o responsável', async () => {
    getMeMock.mockResolvedValue(SEM_FUNCAO_COORDENADOR);
    renderWizard();
    await irParaParticipantes();
    responder(ACOMPANHA, 'Não');
    responder(AVALIAR, 'Não');
    fireEvent.click(screen.getByRole('button', { name: /Ir para proximo passo/i }));
    expect(await screen.findByText('Escolha o coordenador responsável pelo evento.')).toBeInTheDocument();
  });

  test('envia as respostas e mostra-as na confirmação', async () => {
    renderWizard();
    await irParaParticipantes();
    responder(ACOMPANHA, 'Sim');
    responder(AVALIAR, 'Não');
    fireEvent.click(screen.getByRole('button', { name: /Ir para proximo passo/i }));
    await screen.findByLabelText('Local do Evento');
    fireEvent.click(screen.getByRole('button', { name: /Ir para proximo passo/i }));
    await screen.findByText('Revise sua solicitação');
    expect(screen.getByText('O coordenador responsável acompanha o evento')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Confirmar Solicitação/i }));
    await waitFor(() => expect(createSolicitacaoMock).toHaveBeenCalled());
    const payload = createSolicitacaoMock.mock.calls[0][0];
    expect(payload.coordenador_acompanha).toBe(true);
    expect(payload.pretende_avaliar_formador).toBe(false);
    expect(payload.extra_participants).toEqual({ formador_ids: [99] });
  });
});
