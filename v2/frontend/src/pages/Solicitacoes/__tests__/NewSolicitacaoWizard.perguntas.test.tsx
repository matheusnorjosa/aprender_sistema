/**
 * Nova Solicitação — coordenador responsável e as duas perguntas (decisão do dono, 05/10/2026).
 *
 * - A lista "Coordenadores Acompanhantes" saiu; no lugar, "O coordenador responsável vai
 *   acompanhar o evento?" (Sim/Não, obrigatória).
 * - A prévia de agenda confere os formadores e o responsável só com "Sim".
 * - "Você pretende avaliar o formador nesse evento?" só aparece quando o projeto pergunta e há
 *   formador avaliável na lista; com "Sim", escolher qual formador.
 * - Vazio no responsável = quem cria só quando o backend aceita para o projeto escolhido
 *   (`responsavel_padrao` do lookup de projetos: papel COORDENADOR na gerência do projeto, PR 8/PR 9);
 *   senão é obrigatório escolher.
 * - Trocar o projeto limpa formadores e responsável (PR 9, P9-5: só pessoas da gerência do projeto).
 */
import { useEffect } from 'react';
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import Modal from 'antd/es/modal';

import { enderecoAtual, renderNoRoteador } from '../../../test/comRoteador';

const {
  createSolicitacoesEmLoteMock,
  getMeMock,
  checkAvailabilityManyMock,
  lookupMunicipiosWithFiltersMock,
  lookupProjetosMock,
  lookupTiposEventoMock,
  formadoresEscolhidos,
  lookupUsuariosMock,
  formadoresPickerProps,
} = vi.hoisted(() => ({
  createSolicitacoesEmLoteMock: vi.fn(),
  getMeMock: vi.fn(),
  checkAvailabilityManyMock: vi.fn(),
  lookupMunicipiosWithFiltersMock: vi.fn(),
  lookupProjetosMock: vi.fn(),
  lookupTiposEventoMock: vi.fn(),
  formadoresEscolhidos: { atual: [] as Array<{ id: number; label: string; avaliavel?: boolean }> },
  lookupUsuariosMock: vi.fn(),
  formadoresPickerProps: { projetoIds: [] as unknown[] },
}));

vi.mock('../../../api/solicitacoes', () => ({ createSolicitacoesEmLote: createSolicitacoesEmLoteMock }));
vi.mock('../../../api/availability', () => ({
  getMe: getMeMock,
  checkAvailabilityMany: checkAvailabilityManyMock,
}));
vi.mock('../../../api/lookup', () => ({
  lookupMunicipiosWithFilters: lookupMunicipiosWithFiltersMock,
  lookupProjetos: lookupProjetosMock,
  lookupTiposEvento: lookupTiposEventoMock,
  lookupUsuarios: lookupUsuariosMock,
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
  default: ({ onChange, projetoId }: { onChange?: (v: unknown) => void; projetoId?: unknown }) => {
    formadoresPickerProps.projetoIds.push(projetoId);
    return (
      <button type="button" data-testid="pick-formador" onClick={() => onChange?.(formadoresEscolhidos.atual)}>
        pick-formador
      </button>
    );
  },
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

const vinculo = (papel: string) => [{ id: 10, rotulo: 'Vidas', papeis: [papel] }];
const COORDENADORA = {
  id: 1,
  name: 'Ana Coordenadora',
  username: 'ana',
  is_superuser: false,
  funcoes: ['Coordenador'],
  gerencias: vinculo('COORDENADOR'),
};
const SEM_FUNCAO_COORDENADOR = {
  id: 2,
  name: 'Davi Apoio',
  username: 'davi',
  is_superuser: false,
  funcoes: ['Apoio de Coordenação'],
  gerencias: vinculo('APOIO'),
};
const AVALIAVEL = { id: 99, label: 'Bruno Formador', avaliavel: true };
const NAO_AVALIAVEL = { id: 98, label: 'Celia Coordenadora', avaliavel: false };

function renderWizard(): ReturnType<typeof renderNoRoteador>['router'] {
  return renderNoRoteador(<NewSolicitacaoWizard />, { em: '/solicitacoes/nova' }).router;
}

/** Preenche a linha 1, o horário e os formadores do cartão (tudo na mesma página). */
async function preencherEvento(): Promise<void> {
  await screen.findByTestId('cb-projeto');
  fireEvent.click(screen.getByTestId('cb-projeto'));
  fireEvent.click(screen.getByTestId('cb-tipo'));
  fireEvent.click(screen.getByTestId('cb-municipio'));
  fireEvent.click(screen.getByTestId('set-date'));
  fireEvent.click(screen.getByTestId('pick-formador'));
}

function responder(pergunta: RegExp, resposta: 'Sim' | 'Não'): void {
  fireEvent.click(within(screen.getByRole('radiogroup', { name: pergunta })).getByLabelText(resposta));
}

const criar = (): HTMLElement => screen.getByRole('button', { name: 'Criar solicitação' });
const ACOMPANHA = /O coordenador responsável vai acompanhar o evento\?/;
const AVALIAR = /Você pretende avaliar o formador nesse evento\?/;
// A validação do Form do AntD é assíncrona: aqui leva 0,2–0,6 s; na CI, com a suíte inteira e a
// cobertura, passa de 1 s (o padrão do findBy) — o aviso aparece, só demora.
const ESPERA_VALIDACAO = { timeout: 5000 };

// A página com antd leva ~3 s por teste isolado; na suíte inteira passa dos 5 s padrão.
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
    projetoEscolhido = {
      id: 123,
      label: 'Projeto X',
      fluxo: 'NAO_SUPER',
      pergunta_avaliar_formador: true,
      responsavel_padrao: true,
    };
    formadoresEscolhidos.atual = [AVALIAVEL];
    lookupProjetosMock.mockResolvedValue([projetoEscolhido]);
    lookupTiposEventoMock.mockResolvedValue([{ id: 789, label: 'Formação' }]);
    lookupMunicipiosWithFiltersMock.mockResolvedValue([{ id: 456, label: 'Fortaleza - CE' }]);
    getMeMock.mockResolvedValue(COORDENADORA);
    checkAvailabilityManyMock.mockResolvedValue({ ok: true, results: [] });
    createSolicitacoesEmLoteMock.mockResolvedValue({ eventos: [{ indice: 0, id: 1, status: 'aprovado' }] });
    lookupUsuariosMock.mockResolvedValue([]);
    formadoresPickerProps.projetoIds.length = 0;
  });

  test('formadores e responsável vêm da gerência do projeto escolhido (PR 9, P9-5)', async () => {
    getMeMock.mockResolvedValue(SEM_FUNCAO_COORDENADOR);
    projetoEscolhido = { ...projetoEscolhido, responsavel_padrao: false };
    renderWizard();
    await preencherEvento();
    expect(formadoresPickerProps.projetoIds.at(-1)).toBe(123);
    await waitFor(() => expect(lookupUsuariosMock).toHaveBeenCalledWith('', 'Coordenador', 123));
  });

  test('a lista de coordenadores acompanhantes saiu e a pergunta Sim/Não entrou', async () => {
    renderWizard();
    await preencherEvento();
    expect(screen.queryByText('Coordenadores Acompanhantes')).not.toBeInTheDocument();
    expect(screen.getByRole('radiogroup', { name: ACOMPANHA })).toBeInTheDocument();
  });

  test('não envia sem responder se o coordenador vai acompanhar', async () => {
    renderWizard();
    await preencherEvento();
    responder(AVALIAR, 'Não');
    fireEvent.click(criar());
    expect(await screen.findByText('Responda se o coordenador responsável vai acompanhar o evento.', undefined, ESPERA_VALIDACAO)).toBeInTheDocument();
    expect(createSolicitacoesEmLoteMock).not.toHaveBeenCalled();
    expect(screen.getByTestId('pick-formador')).toBeInTheDocument();
  });

  test('prévia de agenda: o responsável só entra com Sim', async () => {
    renderWizard();
    await preencherEvento();
    responder(ACOMPANHA, 'Não');
    await waitFor(() => expect(checkAvailabilityManyMock).toHaveBeenCalled());
    expect(checkAvailabilityManyMock.mock.calls.at(-1)?.[0].usuarios_ids).toEqual([99]);

    responder(ACOMPANHA, 'Sim');
    await waitFor(() => expect(checkAvailabilityManyMock.mock.calls.at(-1)?.[0].usuarios_ids).toEqual([1, 99]));
  });

  test('pergunta de avaliar: aparece com formador avaliável, fora de "Mais detalhes", e pede qual formador no Sim', async () => {
    renderWizard();
    await preencherEvento();
    const pergunta = screen.getByRole('radiogroup', { name: AVALIAR });
    expect(pergunta.closest('.ant-collapse')).toBeNull();
    expect(screen.queryByLabelText('Qual formador você pretende avaliar?')).not.toBeInTheDocument();
    responder(AVALIAR, 'Sim');
    const qual = await screen.findByLabelText('Qual formador você pretende avaliar?');
    expect(qual.closest('.ant-collapse')).toBeNull();
  });

  test('pergunta de avaliar some quando a gerência do projeto não pergunta', async () => {
    projetoEscolhido = { ...projetoEscolhido, pergunta_avaliar_formador: false };
    renderWizard();
    await preencherEvento();
    expect(screen.queryByRole('radiogroup', { name: AVALIAR })).not.toBeInTheDocument();
  });

  test('pergunta de avaliar some quando nenhum formador é avaliável (coordenador como formador)', async () => {
    formadoresEscolhidos.atual = [NAO_AVALIAVEL];
    renderWizard();
    await preencherEvento();
    expect(screen.queryByRole('radiogroup', { name: AVALIAR })).not.toBeInTheDocument();
  });

  test('quem não é coordenador precisa escolher o responsável', async () => {
    getMeMock.mockResolvedValue(SEM_FUNCAO_COORDENADOR);
    projetoEscolhido = { ...projetoEscolhido, responsavel_padrao: false };
    renderWizard();
    await preencherEvento();
    responder(ACOMPANHA, 'Não');
    responder(AVALIAR, 'Não');
    fireEvent.click(criar());
    expect(await screen.findByText('Escolha o coordenador responsável pelo evento.', undefined, ESPERA_VALIDACAO)).toBeInTheDocument();
    expect(createSolicitacoesEmLoteMock).not.toHaveBeenCalled();
  });

  test('projeto em que o backend aceita o vazio: quem cria é o responsável', async () => {
    renderWizard();
    await preencherEvento();
    expect(screen.getByText('Vazio: você é o coordenador responsável.')).toBeInTheDocument();
    responder(ACOMPANHA, 'Sim');
    responder(AVALIAR, 'Não');
    await waitFor(() => expect(checkAvailabilityManyMock.mock.calls.at(-1)?.[0].usuarios_ids).toEqual([1, 99]));
    fireEvent.click(criar());
    await waitFor(() => expect(createSolicitacoesEmLoteMock).toHaveBeenCalled());
    expect(createSolicitacoesEmLoteMock.mock.calls[0][0][0].coordenador).toBeNull();
  });

  test('coordenadora só de outra gerência: o texto do vazio não aparece e precisa escolher (PR 9)', async () => {
    // `me.gerencias` diz COORDENADOR, mas não na gerência do projeto: o backend recusaria o vazio.
    projetoEscolhido = { ...projetoEscolhido, responsavel_padrao: false };
    renderWizard();
    await preencherEvento();
    expect(screen.queryByText('Vazio: você é o coordenador responsável.')).not.toBeInTheDocument();
    responder(ACOMPANHA, 'Não');
    responder(AVALIAR, 'Não');
    fireEvent.click(criar());
    expect(await screen.findByText('Escolha o coordenador responsável pelo evento.', undefined, ESPERA_VALIDACAO)).toBeInTheDocument();
  });

  test('envia as respostas', async () => {
    renderWizard();
    await preencherEvento();
    responder(ACOMPANHA, 'Sim');
    responder(AVALIAR, 'Não');
    fireEvent.click(criar());
    await waitFor(() => expect(createSolicitacoesEmLoteMock).toHaveBeenCalled());
    const payload = createSolicitacoesEmLoteMock.mock.calls[0][0][0];
    expect(payload.coordenador_acompanha).toBe(true);
    expect(payload.pretende_avaliar_formador).toBe(false);
    expect(payload.extra_participants).toEqual({ formador_ids: [99] });
  });

  // Prints de 28/10/2026: o antd não foca um Radio.Group; o foco vai à primeira opção da pergunta.
  test('"pretende avaliar" sem resposta: o foco vai à primeira opção da pergunta', async () => {
    renderWizard();
    await preencherEvento();
    responder(ACOMPANHA, 'Não');
    fireEvent.click(criar());
    expect(await screen.findByText('Responda se você pretende avaliar o formador.', undefined, ESPERA_VALIDACAO)).toBeInTheDocument();
    const grupo = screen.getByRole('radiogroup', { name: AVALIAR });
    await waitFor(() => expect(within(grupo).getByLabelText('Sim')).toHaveFocus(), ESPERA_VALIDACAO);
    expect(createSolicitacoesEmLoteMock).not.toHaveBeenCalled();
  });

  test('avaliar com Sim exige e envia qual formador', async () => {
    renderWizard();
    await preencherEvento();
    responder(ACOMPANHA, 'Não');
    responder(AVALIAR, 'Sim');
    fireEvent.click(criar());
    expect(await screen.findByText('Escolha qual formador você pretende avaliar.', undefined, ESPERA_VALIDACAO)).toBeInTheDocument();
    expect(createSolicitacoesEmLoteMock).not.toHaveBeenCalled();
  });

  // Item 38 (ensaio de 20/10/2026): a tela mostrava o código NAO_SUPER. A situação do cartão diz o
  // que acontece com o evento, em palavras.
  test('a situação do cartão diz o fluxo em palavras, sem o código', async () => {
    renderWizard();
    await preencherEvento();
    expect(screen.getByText('Aprovado na hora')).toBeInTheDocument();
    expect(screen.queryByText('Vai para aprovação')).not.toBeInTheDocument();
    expect(screen.queryByText(/NAO_SUPER/)).not.toBeInTheDocument();
  });

  // Item 36: sair da tela com algo preenchido pergunta; depois do envio com sucesso, não
  // (o que foi preenchido virou a solicitação).
  test('depois de enviar com sucesso, vai para Minhas Solicitações sem perguntar', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm');
    const router = renderWizard();
    await preencherEvento();
    responder(ACOMPANHA, 'Não');
    responder(AVALIAR, 'Não');
    fireEvent.click(criar());

    await waitFor(() => expect(enderecoAtual(router)).toBe('/solicitacoes/minhas'));
    expect(confirmar).not.toHaveBeenCalled();
    confirmar.mockRestore();
  });

  test('trocar o projeto limpa os formadores e o responsável já escolhidos (PR 9, P9-5)', async () => {
    renderWizard();
    await preencherEvento();
    fireEvent.click(screen.getByTestId('cb-responsavel'));

    projetoEscolhido = { ...projetoEscolhido, id: 124, label: 'Projeto Y' };
    fireEvent.click(screen.getByTestId('cb-projeto'));
    fireEvent.click(screen.getByTestId('cb-municipio'));
    expect(formadoresPickerProps.projetoIds.at(-1)).toBe(124);

    // Sem formador escolhido de novo, não envia.
    responder(ACOMPANHA, 'Não');
    fireEvent.click(criar());
    expect(await screen.findByText('Por favor selecione pelo menos um formador', undefined, ESPERA_VALIDACAO)).toBeInTheDocument();
    expect(createSolicitacoesEmLoteMock).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId('pick-formador'));
    responder(AVALIAR, 'Não');
    expect(screen.getByText('Vazio: você é o coordenador responsável.')).toBeInTheDocument();
    fireEvent.click(criar());
    await waitFor(() => expect(createSolicitacoesEmLoteMock).toHaveBeenCalled());
    const payload = createSolicitacoesEmLoteMock.mock.calls[0][0][0];
    expect(payload.projeto).toBe(124);
    expect(payload.coordenador).toBeNull();
    expect(payload.extra_participants).toEqual({ formador_ids: [99] });
  });
});
