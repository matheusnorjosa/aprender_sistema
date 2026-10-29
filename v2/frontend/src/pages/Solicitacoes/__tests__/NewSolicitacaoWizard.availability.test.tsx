import { useEffect } from 'react';
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderNoRoteador } from '../../../test/comRoteador';

import { ComAcesso } from '../../../test/comAcesso';
import { botaoDoTexto, grupoDaPergunta, PERGUNTA_ACOMPANHA } from './localizadores';

const {
  createSolicitacoesEmLoteMock,
  getMeMock,
  checkAvailabilityManyMock,
  lookupMunicipiosWithFiltersMock,
  lookupProjetosMock,
  lookupTiposEventoMock,
  navigateMock,
} = vi.hoisted(() => ({
  createSolicitacoesEmLoteMock: vi.fn(),
  getMeMock: vi.fn(),
  checkAvailabilityManyMock: vi.fn(),
  lookupMunicipiosWithFiltersMock: vi.fn(),
  lookupProjetosMock: vi.fn(),
  lookupTiposEventoMock: vi.fn(),
  navigateMock: vi.fn(),
}));

vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return { ...actual, useNavigate: () => navigateMock };
});
vi.mock('../../../api/solicitacoes', () => ({ createSolicitacoesEmLote: createSolicitacoesEmLoteMock }));
vi.mock('../../../api/availability', () => ({
  getMe: getMeMock,
  checkAvailabilityMany: checkAvailabilityManyMock,
}));
vi.mock('../../../api/lookup', () => ({
  lookupMunicipiosWithFilters: lookupMunicipiosWithFiltersMock,
  lookupProjetos: lookupProjetosMock,
  lookupTiposEvento: lookupTiposEventoMock,
  // #1666: a tela busca coordenadores (ComboBox "Coordenador responsável").
  lookupUsuarios: vi.fn().mockResolvedValue([]),
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
    <>
      <button
        type="button"
        data-testid="pick-formador"
        onClick={() => onChange?.([{ id: 99, email: 'f@x.com', label: 'Bruno Formador' }])}
      >
        pick-formador
      </button>
      <button
        type="button"
        data-testid="pick-outro-formador"
        onClick={() => onChange?.([{ id: 77, email: 'g@x.com', label: 'Gil Formador' }])}
      >
        pick-outro-formador
      </button>
    </>
  ),
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
  // Página única: os quatro ComboBox do cartão ficam na tela ao mesmo tempo.
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
        if (testid === 'cb-projeto') onChange?.({ id: 123, label: 'Projeto X', fluxo: 'SUPER' });
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

async function preencherEventoComFormador(): Promise<void> {
  await screen.findByTestId('cb-projeto');
  fireEvent.click(screen.getByTestId('cb-projeto'));
  fireEvent.click(screen.getByTestId('cb-tipo'));
  fireEvent.click(screen.getByTestId('cb-municipio'));
  fireEvent.click(screen.getByTestId('set-date'));
  fireEvent.click(screen.getByTestId('pick-formador'));
}

/**
 * O resto do que é obrigatório: o responsável e a resposta de acompanhar. Espera a prévia de agenda
 * terminar (o "Verificando" sai da tela), como quem preenche e só depois clica em Criar.
 */
async function completarResponsavel(): Promise<void> {
  fireEvent.click(screen.getByTestId('cb-responsavel'));
  fireEvent.click(within(grupoDaPergunta(PERGUNTA_ACOMPANHA)).getByLabelText('Não'));
  await waitFor(() => expect(screen.queryByText(/Verificando disponibilidade/)).not.toBeInTheDocument());
}

const criar = (): HTMLElement => botaoDoTexto('Criar solicitação');

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

// O 400 do lote: `blocked_participants` no topo do item (formato do batch-approve).
const RECUSA_POR_CONFLITO = {
  status: 400,
  response: {
    status: 400,
    data: {
      code: 'lote_invalido',
      detail: '1 de 1 eventos tem problema. Nada foi criado.',
      errors: {
        itens: [
          {
            indice: 0,
            code: 'availability_conflict',
            detail: 'Não é possível criar o evento: Bruno Formador já tem evento neste horário.',
            blocked_participants: [
              {
                usuario_id: 99,
                usuario_nome: 'Bruno Formador',
                conflicts: [{ code: 'X', title: 'Sobreposição', detail: 'Conflita com evento aprovado #5', ref_id: 5 }],
              },
            ],
          },
        ],
      },
    },
  },
};

function renderComDispensa(): void {
  renderNoRoteador(
    <ComAcesso policies={['create_solicitation', 'create_solicitation_without_purchase']}>
      <NewSolicitacaoWizard />
    </ComAcesso>
  );
}

// A página com antd leva ~3 s por teste isolado; na suíte inteira passa dos 5 s padrão.
describe('NewSolicitacaoWizard — aviso antecipado de disponibilidade (#1452)', { timeout: 20000 }, () => {
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
    createSolicitacoesEmLoteMock.mockResolvedValue({ eventos: [{ indice: 0, id: 1, status: 'aprovado' }] });
  });

  test('selecionar formador + data dispara check-many com os formadores (quem cria não entra por criar)', async () => {
    renderComDispensa();
    await preencherEventoComFormador();

    await waitFor(() => expect(checkAvailabilityManyMock).toHaveBeenCalled());
    const arg = checkAvailabilityManyMock.mock.calls[0][0];
    // 05/10/2026: quem cria (1) não entra por ter criado; o responsável só entra se acompanhar.
    expect(arg.usuarios_ids).toEqual([99]);
    expect(arg.municipio_id).toBe(456);
    expect(arg.inicio).toBeTruthy();
  });

  test('conflito confirmado: mostra o formador e DESABILITA o Criar solicitação', async () => {
    checkAvailabilityManyMock.mockResolvedValue(RESP_CONFLITO);
    renderComDispensa();
    await preencherEventoComFormador();

    expect(await screen.findByText('Não é possível criar o evento')).toBeInTheDocument();
    expect(screen.getByText('Bruno Formador')).toBeInTheDocument();
    await waitFor(() => expect(criar()).toBeDisabled());
    // O botão desabilitado aponta o motivo (o alerta do cartão).
    expect(criar()).toHaveAttribute('aria-describedby', 'preview-conflito-1');
    expect(document.getElementById('preview-conflito-1')).toHaveTextContent('Bruno Formador');
    // A orientação não fala mais em passo anterior: tudo está na mesma página.
    expect(screen.getByText('Remova o participante em conflito ou escolha outra data ou horário.')).toBeInTheDocument();
  });

  test('sem conflito: nenhum alerta de bloqueio e Criar habilitado', async () => {
    checkAvailabilityManyMock.mockResolvedValue({ ok: true, results: [] });
    renderComDispensa();
    await preencherEventoComFormador();

    await waitFor(() => expect(checkAvailabilityManyMock).toHaveBeenCalled());
    expect(screen.queryByText('Não é possível criar o evento')).not.toBeInTheDocument();
    expect(criar()).not.toBeDisabled();
  });

  test('limite diário é só aviso: mostra a informação e NÃO desabilita o Criar', async () => {
    checkAvailabilityManyMock.mockResolvedValue({
      ok: true,
      results: [
        { usuario_id: 1, ok: true, conflicts: [], warnings: [] },
        {
          usuario_id: 99,
          ok: true,
          conflicts: [],
          warnings: [
            {
              code: 'M',
              title: 'Dia com mais de 8 horas de eventos',
              detail: 'No dia 01/08 a soma dos eventos chega a 10h. Isso não impede o evento.',
              ref_id: null,
            },
          ],
        },
      ],
    });
    renderComDispensa();
    await preencherEventoComFormador();

    // A região já está na página, vazia; o texto entra nela quando a checagem responde.
    const aviso = screen.getByRole('status');
    await waitFor(() => expect(aviso).toHaveTextContent('Aviso de agenda: isso não impede o evento'));
    expect(aviso).toHaveTextContent('Bruno Formador');
    expect(aviso).toHaveTextContent('Dia com mais de 8 horas de eventos');
    expect(screen.queryByText('Não é possível criar o evento')).not.toBeInTheDocument();
    expect(criar()).not.toBeDisabled();
  });

  test('checagem falha (500): fail-open — Criar continua habilitado', async () => {
    checkAvailabilityManyMock.mockRejectedValue(Object.assign(new Error('boom'), { status: 500 }));
    renderComDispensa();
    await preencherEventoComFormador();

    await waitFor(() => expect(checkAvailabilityManyMock).toHaveBeenCalled());
    expect(screen.queryByText('Não é possível criar o evento')).not.toBeInTheDocument();
    await waitFor(() => expect(criar()).not.toBeDisabled());
  });

  test('conflito recusado no envio: trocar o formador destrava o Criar e tira o alerta antigo', async () => {
    createSolicitacoesEmLoteMock.mockRejectedValueOnce(RECUSA_POR_CONFLITO);
    renderComDispensa();
    await preencherEventoComFormador();
    await completarResponsavel();

    await waitFor(() => expect(criar()).not.toBeDisabled());
    fireEvent.click(criar());
    expect(await screen.findByText('Não é possível criar o evento')).toBeInTheDocument();
    await waitFor(() => expect(criar()).toBeDisabled());
    expect(criar()).toHaveAttribute('aria-describedby', 'submit-conflito-1');

    // Segue a orientação do alerta, no mesmo cartão: troca o formador.
    fireEvent.click(screen.getByTestId('pick-outro-formador'));
    await waitFor(() => expect(criar()).not.toBeDisabled());
    expect(screen.queryByText('Não é possível criar o evento')).not.toBeInTheDocument();
  });

  // O conflito com evento que já está no banco continua valendo enquanto horário, município e pessoas
  // de todos os eventos forem os do envio: mudar outro campo ou pôr um evento em branco não destrava
  // (a prévia não o pega de novo, e o próximo clique receberia a mesma recusa).
  test('conflito recusado no envio: mudar o que não é horário, município ou pessoa não destrava', async () => {
    createSolicitacoesEmLoteMock.mockRejectedValueOnce(RECUSA_POR_CONFLITO);
    renderComDispensa();
    await preencherEventoComFormador();
    await completarResponsavel();
    await waitFor(() => expect(criar()).not.toBeDisabled());
    fireEvent.click(criar());
    expect(await screen.findByText('Não é possível criar o evento')).toBeInTheDocument();

    // O resumo do topo também diz o motivo (é a região viva; o alerta do cartão não é outra).
    expect(screen.getAllByRole('alert')).toHaveLength(1);
    expect(screen.getByRole('alert')).toHaveTextContent('Evento 1: Não é possível criar o evento: Bruno Formador');
    await waitFor(() => expect(criar()).toBeDisabled());

    fireEvent.change(screen.getByLabelText('Local do Evento'), { target: { value: 'Escola X' } });
    fireEvent.click(screen.getByTestId('cb-tipo'));
    expect(screen.getByText('Não é possível criar o evento')).toBeInTheDocument();
    expect(criar()).toBeDisabled();
    fireEvent.click(botaoDoTexto('Adicionar outro evento'));
    expect(screen.getByText('Não é possível criar o evento')).toBeInTheDocument();
    expect(botaoDoTexto('Criar 2 eventos')).toBeDisabled();
    expect(createSolicitacoesEmLoteMock).toHaveBeenCalledTimes(1);
  });

  // O evento novo não estava no envio: preencher qualquer coisa nele não muda o choque do evento 1.
  test('conflito recusado no envio: preencher um evento adicionado depois não destrava', async () => {
    createSolicitacoesEmLoteMock.mockRejectedValueOnce(RECUSA_POR_CONFLITO);
    renderComDispensa();
    await preencherEventoComFormador();
    await completarResponsavel();
    await waitFor(() => expect(criar()).not.toBeDisabled());
    fireEvent.click(criar());
    expect(await screen.findByText('Não é possível criar o evento')).toBeInTheDocument();
    await waitFor(() => expect(criar()).toBeDisabled());

    fireEvent.click(botaoDoTexto('Adicionar outro evento'));
    fireEvent.click(screen.getAllByTestId('cb-tipo')[1]);
    expect(screen.getByText('Não é possível criar o evento')).toBeInTheDocument();
    expect(botaoDoTexto('Criar 2 eventos')).toBeDisabled();
  });

  test('com tudo preenchido, Criar envia uma vez o evento da tela (campos opcionais intocados não apagam nada)', async () => {
    renderComDispensa();
    await preencherEventoComFormador();
    await completarResponsavel();
    await waitFor(() => expect(criar()).not.toBeDisabled());
    fireEvent.click(criar());

    await waitFor(() => expect(createSolicitacoesEmLoteMock).toHaveBeenCalledTimes(1));
    const payload = createSolicitacoesEmLoteMock.mock.calls[0][0][0];
    expect(payload).toMatchObject({
      municipio: 456,
      projeto: 123,
      tipo_evento: 789,
      coordenador: 7,
      coordenador_acompanha: false,
      local: '',
      is_online: false,
      extra_participants: { formador_ids: [99] },
    });
    expect(payload.inicio).toBe('2026-08-01T12:00:00Z');
    expect(payload.fim).toBe('2026-08-01T14:00:00Z');
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith('/solicitacoes/minhas'));
  });
});
