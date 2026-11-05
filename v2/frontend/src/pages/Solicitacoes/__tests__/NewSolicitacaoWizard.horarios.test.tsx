/**
 * Nova Solicitação — "+ horário" no cartão (decisão do dono, 03/11/2026).
 *
 * Projeto, tipo, município, nº da formação e "Mais detalhes" se preenchem uma vez por cartão. Cada
 * horário tem o seu dia, início, fim, formadores e coordenador, e vira um evento separado no lote
 * (como a planilha faz com manhã e tarde). A agenda de cada pessoa é conferida só no horário dela.
 * O teto de 10 conta eventos, isto é, horários.
 */
import { useEffect } from 'react';
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import message from 'antd/es/message';
import { renderNoRoteador } from '../../../test/comRoteador';
import { buildSolicitacaoPayload } from '../NewSolicitacaoWizard';
import {
  blocoDoHorario,
  botaoAdicionarEvento,
  botaoDoTexto,
  cartao,
  grupoDaPergunta,
  PERGUNTA_ACOMPANHA,
  titulo,
} from './localizadores';

const {
  createSolicitacoesEmLoteMock,
  checkAvailabilityManyMock,
  horario,
  formadores,
  projeto,
  coordenadoresDoMock,
} = vi.hoisted(() => ({
  createSolicitacoesEmLoteMock: vi.fn(),
  checkAvailabilityManyMock: vi.fn(),
  horario: { atual: { date: '2026-08-01', start: '09:00', end: '11:00' } },
  formadores: { atual: [{ id: 99, label: 'Bruno Formador', avaliavel: false }] },
  projeto: { atual: {} },
  coordenadoresDoMock: { atual: [{ id: 7, label: 'Carla Coordenadora' }] as Array<{ id: number; label: string }> },
}));

vi.mock('../../../api/solicitacoes', () => ({ createSolicitacoesEmLote: createSolicitacoesEmLoteMock }));
vi.mock('../../../api/availability', () => ({
  getMe: vi.fn().mockResolvedValue({ id: 1, name: 'Ana Coordenadora', username: 'ana', is_superuser: false }),
  checkAvailabilityMany: checkAvailabilityManyMock,
}));
vi.mock('../../../api/lookup', () => ({
  lookupMunicipiosWithFilters: vi.fn().mockResolvedValue([]),
  lookupProjetos: vi.fn().mockResolvedValue([]),
  lookupTiposEvento: vi.fn().mockResolvedValue([]),
  lookupUsuarios: vi.fn().mockResolvedValue([]),
}));
// O campo Data leva o id do prefixo, como o de verdade (`<prefixo>date-picker`): é ele que recebe o foco.
vi.mock('../../../components/DateTimeRange', () => ({
  default: ({ onChange, erro, idPrefix = '' }: { onChange?: (v: unknown) => void; erro?: string | null; idPrefix?: string }) => (
    <div>
      <button type="button" id={`${idPrefix}date-picker`} data-testid="set-date" onClick={() => onChange?.(horario.atual)}>
        set-date
      </button>
      <input data-testid="campo-horario" data-campo-horario aria-invalid={erro ? 'true' : undefined} readOnly />
      {erro ? <p data-testid="erro-horario">{erro}</p> : null}
    </div>
  ),
}));
// Mostra quantos formadores o Form do horário guarda (o `value` que o Form.Item injeta).
vi.mock('../../../components/FormadoresPicker', () => ({
  default: ({ onChange, value }: { onChange?: (v: unknown) => void; value?: unknown[] }) => (
    <div>
      <button type="button" data-testid="pick-formador" onClick={() => onChange?.(formadores.atual)}>
        pick-formador
      </button>
      <span data-testid="qtd-formadores">{value?.length ?? 0}</span>
    </div>
  ),
}));

// A caixa "Coordenador(es)" (03/11/2026): escolhe a Carla, que é a 1ª e por isso a responsável.
vi.mock('../../../components/CoordenadoresPicker', () => ({
  default: ({
    onChange,
    id,
    'aria-invalid': invalido,
  }: {
    onChange?: (v: unknown) => void;
    id?: string;
    'aria-invalid'?: boolean | 'true' | 'false';
  }) => (
    <button
      type="button"
      id={id}
      aria-invalid={invalido}
      data-testid="cb-responsavel"
      onClick={() => onChange?.(coordenadoresDoMock.atual)}
    >
      cb-responsavel
    </button>
  ),
}));

function MockComboBox({
  placeholder = '',
  lookupFunction,
  onChange,
  id,
  'aria-invalid': invalido,
}: {
  placeholder?: string;
  lookupFunction: (q: string) => Promise<unknown[]>;
  onChange?: (item: unknown) => void;
  id?: string;
  'aria-invalid'?: boolean | 'true' | 'false';
}) {
  useEffect(() => {
    void lookupFunction('');
  }, [lookupFunction]);
  const testid = placeholder.includes('munic')
    ? 'cb-municipio'
    : placeholder.includes('projeto')
      ? 'cb-projeto'
      : 'cb-tipo';
  return (
    <button
      type="button"
      id={id}
      aria-invalid={invalido}
      data-testid={testid}
      onClick={() => {
        if (testid === 'cb-projeto') onChange?.(projeto.atual);
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

const ESPERA = { timeout: 5000 };
const PROJETO_1 = { id: 101, label: 'Projeto 1', fluxo: 'NAO_SUPER', responsavel_padrao: true };
const PERGUNTA_AVALIAR = 'Você pretende avaliar o formador nesse evento?';

function abrir() {
  return renderNoRoteador(<NewSolicitacaoWizard />, { em: '/solicitacoes/nova', antes: ['/solicitacoes/minhas'] });
}

const botaoCriar = (): HTMLElement => botaoDoTexto(/^Criar /);
/** "+ horário" do cartão: o nome acessível diz de qual evento (o texto à vista é "Adicionar horário"). */
const maisHorario = (n: number): HTMLElement => within(cartao(n)).getByLabelText(`Adicionar horário ao evento ${n}`);

/** Os campos do evento, que valem para todos os horários do cartão. */
function preencherEvento(c: HTMLElement): void {
  fireEvent.click(within(c).getByTestId('cb-projeto'));
  fireEvent.click(within(c).getByTestId('cb-tipo'));
  fireEvent.click(within(c).getByTestId('cb-municipio'));
}

/** Os campos de um horário (o bloco dele, ou o cartão quando só há um). */
async function preencherHorario(bloco: HTMLElement, acompanha: 'Sim' | 'Não' = 'Não'): Promise<void> {
  fireEvent.click(within(bloco).getByTestId('set-date'));
  fireEvent.click(within(bloco).getByTestId('pick-formador'));
  fireEvent.click(within(grupoDaPergunta(PERGUNTA_ACOMPANHA, bloco)).getByLabelText(acompanha));
  await waitFor(() => expect(within(bloco).queryByText(/Verificando disponibilidade/)).not.toBeInTheDocument(), ESPERA);
}

function recusaDoLote(itens: unknown[], detail: string) {
  return { status: 400, response: { status: 400, data: { detail, code: 'lote_invalido', errors: { itens } } } };
}

describe('NewSolicitacaoWizard — "+ horário" (03/11/2026)', { timeout: 60000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(message, 'success').mockImplementation(vi.fn()).mockClear();
    horario.atual = { date: '2026-08-01', start: '09:00', end: '11:00' };
    formadores.atual = [{ id: 99, label: 'Bruno Formador', avaliavel: false }];
    projeto.atual = PROJETO_1;
    coordenadoresDoMock.atual = [{ id: 7, label: 'Carla Coordenadora' }];
    checkAvailabilityManyMock.mockResolvedValue({ ok: true, results: [] });
    createSolicitacoesEmLoteMock.mockResolvedValue({
      eventos: [
        { indice: 0, id: 11, status: 'aprovado' },
        { indice: 1, id: 12, status: 'aprovado' },
      ],
    });
  });

  test('com 1 horário, a tela é a de sempre; "+ horário" põe o Horário 2 em branco e leva o foco à Data dele', async () => {
    abrir();
    await waitFor(() => cartao(1));
    const c1 = cartao(1);
    // Um horário só: sem subtítulo, sem grupo e sem "Remover horário".
    expect(c1.querySelectorAll('h4')).toHaveLength(0);
    expect(within(c1).queryAllByRole('group', { name: /^Horário/ })).toHaveLength(0);
    expect(within(c1).queryByText('Remover horário')).not.toBeInTheDocument();
    expect(maisHorario(1)).toHaveTextContent('Adicionar horário');

    fireEvent.click(maisHorario(1));

    const h2 = blocoDoHorario(cartao(1), 2);
    await waitFor(() => expect(within(h2).getByTestId('set-date')).toHaveFocus());
    expect(blocoDoHorario(cartao(1), 1)).not.toContainElement(within(h2).getByTestId('set-date'));
    // Em branco: o horário novo não traz pessoas nem erro; o campo do evento (projeto) continua um só.
    expect(within(h2).queryByTestId('erro-horario')).not.toBeInTheDocument();
    expect(within(cartao(1)).getAllByTestId('cb-projeto')).toHaveLength(1);
    expect(within(cartao(1)).getAllByTestId('set-date')).toHaveLength(2);
    // Só o 2º horário tem "Remover", e o nome diz qual.
    expect(within(blocoDoHorario(cartao(1), 1)).queryByText('Remover horário')).not.toBeInTheDocument();
    expect(within(h2).getByLabelText('Remover horário 2 do evento 1')).toHaveTextContent('Remover horário');
    // A região viva única diz o que aconteceu; o botão final conta eventos (horários).
    expect(screen.getAllByRole('alert')).toHaveLength(1);
    expect(screen.getByRole('alert')).toHaveTextContent('Horário 2 adicionado ao evento 1');
    expect(botaoCriar()).toHaveTextContent('Criar 2 eventos');
  });

  test('"Remover horário" em branco sai direto: volta a tela de 1 horário e o foco vai ao título do evento', async () => {
    abrir();
    await waitFor(() => cartao(1));
    fireEvent.click(maisHorario(1));
    fireEvent.click(within(blocoDoHorario(cartao(1), 2)).getByLabelText('Remover horário 2 do evento 1'));

    await waitFor(() => expect(titulo(1)).toHaveFocus());
    expect(cartao(1).querySelectorAll('h4')).toHaveLength(0);
    expect(within(cartao(1)).getAllByTestId('set-date')).toHaveLength(1);
    expect(screen.getByRole('alert')).toHaveTextContent('Horário 2 do evento 1 removido');
    expect(botaoCriar()).toHaveTextContent('Criar solicitação');
  });

  test('"Remover horário" preenchido pergunta antes, começando no Cancelar, e cita o horário', async () => {
    abrir();
    await waitFor(() => cartao(1));
    fireEvent.click(maisHorario(1));
    fireEvent.click(within(blocoDoHorario(cartao(1), 2)).getByTestId('pick-formador'));
    fireEvent.click(within(blocoDoHorario(cartao(1), 2)).getByLabelText('Remover horário 2 do evento 1'));

    const dialogo = await screen.findByRole('dialog', { name: 'Remover o horário 2 do evento 1?' });
    const cancelar = within(dialogo).getByRole('button', { name: 'Cancelar' });
    await waitFor(() => expect(cancelar).toHaveFocus());
    expect(cancelar).toHaveAccessibleDescription('O que você preencheu nele será perdido.');
    fireEvent.click(cancelar);
    expect(blocoDoHorario(cartao(1), 2)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());

    fireEvent.click(within(blocoDoHorario(cartao(1), 2)).getByLabelText('Remover horário 2 do evento 1'));
    fireEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Remover' }));
    await waitFor(() => expect(within(cartao(1)).getAllByTestId('set-date')).toHaveLength(1));
  });

  test('com 2 horários, o envio manda 2 eventos: o do cartão repetido e o dia, as pessoas e a resposta de cada horário', async () => {
    abrir();
    await waitFor(() => cartao(1));
    preencherEvento(cartao(1));
    fireEvent.change(within(cartao(1)).getByLabelText('Nº da formação'), { target: { value: '4' } });
    await preencherHorario(cartao(1));
    fireEvent.click(maisHorario(1));
    horario.atual = { date: '2026-08-01', start: '14:00', end: '16:00' };
    formadores.atual = [{ id: 98, label: 'Dora Formadora', avaliavel: false }];
    // Dois coordenadores só no Horário 2: a Carla (responsável) e a Dora (03/11/2026).
    coordenadoresDoMock.atual = [{ id: 7, label: 'Carla Coordenadora' }, { id: 8, label: 'Dora Coordenadora' }];
    const h2 = blocoDoHorario(cartao(1), 2);
    fireEvent.click(within(h2).getByTestId('cb-responsavel'));
    await preencherHorario(h2, 'Sim');

    // A agenda do Horário 2 confere só as pessoas dele (a formadora, a responsável que acompanha e a
    // outra coordenadora, que ocupa sempre).
    await waitFor(() =>
      expect(checkAvailabilityManyMock.mock.calls.map(([arg]) => (arg as { usuarios_ids: number[] }).usuarios_ids)).toContainEqual([7, 98, 8]),
    );
    expect(checkAvailabilityManyMock.mock.calls.map(([arg]) => (arg as { usuarios_ids: number[] }).usuarios_ids)).not.toContainEqual(
      expect.arrayContaining([99, 98]),
    );

    fireEvent.click(botaoCriar());

    await waitFor(() => expect(createSolicitacoesEmLoteMock).toHaveBeenCalledTimes(1), ESPERA);
    const [eventos] = createSolicitacoesEmLoteMock.mock.calls[0] as [Record<string, unknown>[]];
    const doCartao = {
      projetoId: 101,
      municipioId: 456,
      tipoEventoId: 789,
      tipo: '',
      encontro: '4',
      segmento: '',
      observacoes: '',
      local: '',
      isOnline: false,
      avaliar: null,
    };
    expect(eventos).toEqual([
      buildSolicitacaoPayload({
        ...doCartao,
        inicio: '2026-08-01T12:00:00Z',
        fim: '2026-08-01T14:00:00Z',
        formadorIds: [99],
        coordenadorResponsavelId: null,
        coordenadorExtraIds: [],
        coordenadorAcompanha: false,
      }),
      buildSolicitacaoPayload({
        ...doCartao,
        inicio: '2026-08-01T17:00:00Z',
        fim: '2026-08-01T19:00:00Z',
        formadorIds: [98],
        coordenadorResponsavelId: 7,
        coordenadorExtraIds: [8],
        coordenadorAcompanha: true,
      }),
    ]);
    await waitFor(() => expect(message.success).toHaveBeenCalledWith('2 eventos criados'));
  });

  test('campo faltando no 2º horário: o resumo diz "Evento 1, horário 2" e o foco vai ao campo daquele horário', async () => {
    abrir();
    await waitFor(() => cartao(1));
    preencherEvento(cartao(1));
    await preencherHorario(cartao(1));
    fireEvent.click(maisHorario(1));
    const h2 = blocoDoHorario(cartao(1), 2);
    // Sem a data no Horário 2.
    fireEvent.click(within(h2).getByTestId('pick-formador'));
    fireEvent.click(within(grupoDaPergunta(PERGUNTA_ACOMPANHA, h2)).getByLabelText('Não'));

    fireEvent.click(botaoCriar());

    const resumo = await screen.findByRole('alert');
    await waitFor(
      () => expect(resumo).toHaveTextContent('Evento 1, horário 2: Escolha a data e os horários de início e de fim do evento.'),
      ESPERA,
    );
    expect(createSolicitacoesEmLoteMock).not.toHaveBeenCalled();
    expect(within(h2).getByTestId('erro-horario')).toBeInTheDocument();
    expect(within(blocoDoHorario(cartao(1), 1)).queryByTestId('erro-horario')).not.toBeInTheDocument();
    await waitFor(() => expect(within(h2).getByTestId('campo-horario')).toHaveFocus());

    // A linha do resumo leva ao subtítulo do horário.
    fireEvent.click(within(resumo).getByRole('button', { name: /^Evento 1, horário 2:/ }));
    expect(within(h2).getByRole('heading', { level: 4, name: 'Horário 2' })).toHaveFocus();
  });

  test('o erro do servidor no índice 1 do lote volta ao Horário 2: o do horário no horário, o do evento no campo do cartão (uma vez só)', async () => {
    abrir();
    await waitFor(() => cartao(1));
    preencherEvento(cartao(1));
    await preencherHorario(cartao(1));
    fireEvent.click(maisHorario(1));
    horario.atual = { date: '2026-08-01', start: '14:00', end: '16:00' };
    await preencherHorario(blocoDoHorario(cartao(1), 2));

    createSolicitacoesEmLoteMock.mockRejectedValueOnce(
      recusaDoLote(
        [
          {
            indice: 0,
            code: 'VALIDATION_ERROR',
            detail: 'x',
            errors: { municipio: ['Não há compra que libere este projeto neste município.'] },
          },
          {
            indice: 1,
            code: 'VALIDATION_ERROR',
            detail: 'x',
            errors: {
              extra_participants: { formador_ids: ['Formador inválido.'] },
              fim: ['O fim precisa ser depois do início.'],
              municipio: ['Não há compra que libere este projeto neste município.'],
              non_field_errors: ['Recusado por outro motivo.'],
            },
          },
        ],
        '2 de 2 eventos têm problema. Nada foi criado.',
      ),
    );
    fireEvent.click(botaoCriar());

    const resumo = (await screen.findByText('2 de 2 eventos têm problema. Nada foi criado.', undefined, ESPERA)).closest<HTMLElement>(
      '[role="alert"]',
    )!;
    const linhas = within(resumo).getAllByRole('button').map((b) => b.textContent);
    expect(linhas).toContain('Evento 1, horário 2: Formador inválido.');
    // O campo do evento (município) é do cartão: uma linha só, sem horário, mesmo vindo dos 2 itens.
    expect(linhas.filter((l) => l?.includes('Não há compra'))).toEqual(['Evento 1: Não há compra que libere este projeto neste município.']);
    const h1 = blocoDoHorario(cartao(1), 1);
    const h2 = blocoDoHorario(cartao(1), 2);
    expect(await within(h2).findByText('Formador inválido.')).toBeInTheDocument();
    expect(within(h2).getByTestId('erro-horario')).toHaveTextContent('O fim precisa ser depois do início.');
    expect(within(h1).queryByText('Formador inválido.')).not.toBeInTheDocument();
    expect(within(h1).queryByTestId('erro-horario')).not.toBeInTheDocument();
    // O município é do evento: o erro vai ao campo do cartão (fora dos horários).
    expect(within(cartao(1)).getByTestId('cb-municipio')).toHaveAttribute('aria-invalid', 'true');
    expect(within(cartao(1)).getByText('Não há compra que libere este projeto neste município.')).toBeInTheDocument();
    // O que não é de um campo vai ao topo do cartão, dizendo de qual horário.
    expect(within(cartao(1)).getByText('Horário 2: Recusado por outro motivo.')).toBeInTheDocument();
    expect(cartao(1)).toHaveAccessibleName('Evento 1 com problema');
    // O primeiro problema é do evento (o município): o foco vai ao título do cartão.
    await waitFor(() => expect(titulo(1)).toHaveFocus());
  });

  test('conflito de agenda no índice 1 fica no Horário 2 e trava o Criar apontando para ele', async () => {
    abrir();
    await waitFor(() => cartao(1));
    preencherEvento(cartao(1));
    await preencherHorario(cartao(1));
    fireEvent.click(maisHorario(1));
    await preencherHorario(blocoDoHorario(cartao(1), 2));
    createSolicitacoesEmLoteMock.mockRejectedValueOnce(
      recusaDoLote(
        [
          {
            indice: 1,
            code: 'availability_conflict',
            detail: 'Não é possível criar o evento: Bruno Formador tem outro evento neste horário.',
            blocked_participants: [
              {
                usuario_id: 99,
                usuario_nome: 'Bruno Formador',
                conflicts: [{ code: 'X', title: 'Sobreposição', detail: 'Choca com o evento 1 desta lista (09:00–11:00)' }],
              },
            ],
          },
        ],
        '1 de 2 eventos tem problema. Nada foi criado.',
      ),
    );
    fireEvent.click(botaoCriar());

    const h2 = blocoDoHorario(cartao(1), 2);
    // O "evento 1" do servidor é o item 1 do lote: na tela, o Horário 1 do Evento 1.
    expect(
      await within(h2).findByText('Choca com o evento 1, horário 1, desta lista (09:00–11:00)', undefined, ESPERA),
    ).toBeInTheDocument();
    expect(within(blocoDoHorario(cartao(1), 1)).queryByText(/Choca com/)).not.toBeInTheDocument();
    await waitFor(() => expect(botaoCriar()).toBeDisabled());
    const motivo = document.getElementById(botaoCriar().getAttribute('aria-describedby') ?? '');
    expect(h2).toContainElement(motivo);
    expect(screen.getAllByRole('alert')).toHaveLength(1);
    // O problema é do horário: o foco vai ao subtítulo dele.
    await waitFor(() => expect(within(h2).getByRole('heading', { level: 4, name: 'Horário 2' })).toHaveFocus());
  });

  test('2 cartões, o 1º com 2 horários: a recusa no índice 2 cai no cartão 2, e "o evento N desta lista" diz o evento e o horário da tela', async () => {
    abrir();
    await waitFor(() => cartao(1));
    preencherEvento(cartao(1));
    await preencherHorario(cartao(1));
    fireEvent.click(maisHorario(1));
    horario.atual = { date: '2026-08-01', start: '14:00', end: '16:00' };
    await preencherHorario(blocoDoHorario(cartao(1), 2));
    fireEvent.click(botaoAdicionarEvento());
    horario.atual = { date: '2026-08-01', start: '09:00', end: '11:00' };
    preencherEvento(cartao(2));
    await preencherHorario(cartao(2));

    // O servidor numera pela posição no lote (3 itens); na tela são 2 eventos, o 1º com 2 horários.
    const bloqueado = (detail: string) => [
      { usuario_id: 99, usuario_nome: 'Bruno Formador', conflicts: [{ code: 'X', title: 'Sobreposição', detail }] },
    ];
    const motivo = 'Não é possível criar o evento: Bruno Formador tem outro evento desta lista neste horário.';
    createSolicitacoesEmLoteMock.mockRejectedValueOnce(
      recusaDoLote(
        [
          { indice: 0, code: 'availability_conflict', detail: motivo, blocked_participants: bloqueado('Choca com o evento 3 desta lista (09:00–11:00)') },
          { indice: 2, code: 'availability_conflict', detail: motivo, blocked_participants: bloqueado('Choca com o evento 1 desta lista (09:00–11:00)') },
        ],
        '2 de 3 eventos têm problema. Nada foi criado.',
      ),
    );
    fireEvent.click(botaoCriar());

    expect(
      await within(cartao(2)).findByText('Choca com o evento 1, horário 1, desta lista (09:00–11:00)', undefined, ESPERA),
    ).toBeInTheDocument();
    expect(within(blocoDoHorario(cartao(1), 1)).getByText('Choca com o evento 2 desta lista (09:00–11:00)')).toBeInTheDocument();
    expect(within(blocoDoHorario(cartao(1), 2)).queryByText(/Choca/)).not.toBeInTheDocument();
    expect(screen.queryByText(/evento 3/)).not.toBeInTheDocument();
    expect(cartao(1)).toHaveAccessibleName('Evento 1 com problema');
    expect(cartao(2)).toHaveAccessibleName('Evento 2 com problema');
    const linhas = within(screen.getByRole('alert')).getAllByRole('button').map((b) => b.textContent);
    expect(linhas).toEqual([`Evento 1, horário 1: ${motivo}`, `Evento 2: ${motivo}`]);
    await waitFor(() => expect(botaoCriar()).toBeDisabled());

    // O choque depende dos itens 1 e 3 do lote: mudar o Horário 2 do evento 1 (fora dele) não o tira.
    horario.atual = { date: '2026-08-03', start: '14:00', end: '16:00' };
    fireEvent.click(within(blocoDoHorario(cartao(1), 2)).getByTestId('set-date'));
    await waitFor(
      () => expect(within(blocoDoHorario(cartao(1), 2)).queryByText(/Verificando disponibilidade/)).not.toBeInTheDocument(),
      ESPERA,
    );
    expect(within(cartao(2)).getByText('Choca com o evento 1, horário 1, desta lista (09:00–11:00)')).toBeInTheDocument();
    expect(botaoCriar()).toBeDisabled();

    // Mudar o parceiro (o evento 2) tira o choque dos dois.
    fireEvent.click(within(cartao(2)).getByTestId('set-date'));
    await waitFor(() => expect(within(cartao(1)).queryByText(/Choca/)).not.toBeInTheDocument());
    expect(within(cartao(2)).queryByText(/Choca/)).not.toBeInTheDocument();
  });

  test('remover o horário do meio (preenchido, pelo diálogo): o 3º vira o Horário 2 com as respostas dele, e o envio leva o 1º e o 3º', async () => {
    abrir();
    await waitFor(() => cartao(1));
    preencherEvento(cartao(1));
    await preencherHorario(cartao(1));
    fireEvent.click(maisHorario(1));
    horario.atual = { date: '2026-08-01', start: '14:00', end: '16:00' };
    formadores.atual = [{ id: 98, label: 'Dora Formadora', avaliavel: false }];
    await preencherHorario(blocoDoHorario(cartao(1), 2));
    fireEvent.click(maisHorario(1));
    horario.atual = { date: '2026-08-02', start: '08:00', end: '10:00' };
    formadores.atual = [{ id: 97, label: 'Eva Formadora', avaliavel: false }];
    fireEvent.click(within(blocoDoHorario(cartao(1), 3)).getByTestId('cb-responsavel'));
    await preencherHorario(blocoDoHorario(cartao(1), 3), 'Sim');

    fireEvent.click(within(blocoDoHorario(cartao(1), 2)).getByLabelText('Remover horário 2 do evento 1'));
    const dialogo = await screen.findByRole('dialog', { name: 'Remover o horário 2 do evento 1?' });
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Remover' }));

    await waitFor(() => expect(within(cartao(1)).getAllByTestId('set-date')).toHaveLength(2));
    await waitFor(() => expect(within(blocoDoHorario(cartao(1), 1)).getByRole('heading', { level: 4, name: 'Horário 1' })).toHaveFocus());
    const novo2 = blocoDoHorario(cartao(1), 2);
    expect(within(grupoDaPergunta(PERGUNTA_ACOMPANHA, novo2)).getByLabelText('Sim')).toBeChecked();
    expect(within(grupoDaPergunta(PERGUNTA_ACOMPANHA, blocoDoHorario(cartao(1), 1))).getByLabelText('Não')).toBeChecked();
    expect(within(novo2).getByTestId('qtd-formadores')).toHaveTextContent('1');
    expect(within(novo2).getByLabelText('Remover horário 2 do evento 1')).toBeInTheDocument();
    expect(botaoCriar()).toHaveTextContent('Criar 2 eventos');

    fireEvent.click(botaoCriar());
    await waitFor(() => expect(createSolicitacoesEmLoteMock).toHaveBeenCalledTimes(1), ESPERA);
    const [eventos] = createSolicitacoesEmLoteMock.mock.calls[0] as [Record<string, unknown>[]];
    const doCartao = {
      projetoId: 101,
      municipioId: 456,
      tipoEventoId: 789,
      tipo: '',
      encontro: '',
      segmento: '',
      observacoes: '',
      local: '',
      isOnline: false,
      avaliar: null,
    };
    expect(eventos).toEqual([
      buildSolicitacaoPayload({
        ...doCartao,
        inicio: '2026-08-01T12:00:00Z',
        fim: '2026-08-01T14:00:00Z',
        formadorIds: [99],
        coordenadorResponsavelId: null,
        coordenadorExtraIds: [],
        coordenadorAcompanha: false,
      }),
      buildSolicitacaoPayload({
        ...doCartao,
        inicio: '2026-08-02T11:00:00Z',
        fim: '2026-08-02T13:00:00Z',
        formadorIds: [97],
        coordenadorResponsavelId: 7,
        coordenadorExtraIds: [],
        coordenadorAcompanha: true,
      }),
    ]);
  });

  test('trocar o projeto com 2 horários limpa os formadores e a resposta de avaliar dos dois', async () => {
    projeto.atual = { ...PROJETO_1, pergunta_avaliar_formador: true };
    formadores.atual = [{ id: 99, label: 'Bruno Formador', avaliavel: true }];
    abrir();
    await waitFor(() => cartao(1));
    preencherEvento(cartao(1));
    await preencherHorario(cartao(1));
    fireEvent.click(maisHorario(1));
    await preencherHorario(blocoDoHorario(cartao(1), 2));
    for (const n of [1, 2]) {
      const bloco = blocoDoHorario(cartao(1), n);
      expect(within(bloco).getByTestId('qtd-formadores')).toHaveTextContent('1');
      fireEvent.click(within(grupoDaPergunta(PERGUNTA_AVALIAR, bloco)).getByLabelText('Não'));
    }

    projeto.atual = { id: 202, label: 'Projeto 2', fluxo: 'NAO_SUPER', responsavel_padrao: true, pergunta_avaliar_formador: true };
    fireEvent.click(within(cartao(1)).getByTestId('cb-projeto'));

    for (const n of [1, 2]) {
      const bloco = blocoDoHorario(cartao(1), n);
      await waitFor(() => expect(within(bloco).getByTestId('qtd-formadores')).toHaveTextContent('0'));
      expect(within(bloco).queryByText(PERGUNTA_AVALIAR)).not.toBeInTheDocument();
    }
    // Escolhido de novo, o formador traz a pergunta de volta, sem a resposta de antes.
    for (const n of [1, 2]) {
      const bloco = blocoDoHorario(cartao(1), n);
      fireEvent.click(within(bloco).getByTestId('pick-formador'));
      const grupo = await waitFor(() => grupoDaPergunta(PERGUNTA_AVALIAR, blocoDoHorario(cartao(1), n)));
      expect(within(grupo).getByLabelText('Sim')).not.toBeChecked();
      expect(within(grupo).getByLabelText('Não')).not.toBeChecked();
    }
  });

  test('o teto de 10 conta os horários: "+ horário" e "+ evento" desabilitam juntos com o texto do limite', async () => {
    abrir();
    await waitFor(() => cartao(1));
    for (let i = 0; i < 5; i += 1) fireEvent.click(maisHorario(1));
    for (let i = 0; i < 3; i += 1) fireEvent.click(botaoAdicionarEvento());
    // 6 horários no evento 1 + 3 eventos = 9: ainda cabe um.
    expect(botaoCriar()).toHaveTextContent('Criar 9 eventos');
    expect(botaoAdicionarEvento()).not.toBeDisabled();
    fireEvent.click(maisHorario(2));

    expect(botaoCriar()).toHaveTextContent('Criar 10 eventos');
    expect(botaoAdicionarEvento()).toBeDisabled();
    expect(botaoAdicionarEvento()).toHaveTextContent('Limite de 10 eventos por vez');
    for (const n of [1, 2, 3, 4]) {
      const botao = within(cartao(n)).getByText('Limite de 10 eventos por vez').closest('button');
      expect(botao).toBeDisabled();
      // O nome continua dizendo de qual evento (e contém o texto à vista).
      expect(botao).toHaveAttribute('aria-label', `Adicionar horário ao evento ${n}: limite de 10 eventos por vez`);
    }
    expect(within(cartao(1)).queryByText('Adicionar horário')).not.toBeInTheDocument();
    // O localizador do POM do e2e (`btnAdicionarEvento`) continua achando um botão só, em modo estrito.
    expect(screen.getAllByRole('button', { name: /Adicionar outro evento|Limite de 10 eventos por vez/ })).toHaveLength(1);

    // Tirar um horário libera de novo.
    fireEvent.click(within(blocoDoHorario(cartao(1), 6)).getByLabelText('Remover horário 6 do evento 1'));
    await waitFor(() => expect(botaoAdicionarEvento()).not.toBeDisabled());
    expect(maisHorario(1)).not.toBeDisabled();
  });
});
