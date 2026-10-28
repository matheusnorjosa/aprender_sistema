/**
 * Nova Solicitação — vários eventos de uma vez (PR 5, decisões do dono de 28/10/2026).
 *
 * - A tela começa com 1 evento; "+ Adicionar outro evento" acrescenta um em branco (foco no título
 *   dele e anúncio na região viva única); cada evento extra tem "Remover".
 * - Limite de 10; o botão final diz "Criar N eventos" (com 1, "Criar solicitação").
 * - O envio é SEMPRE o lote (tudo ou nada): no 400 `lote_invalido`, cada item volta ao cartão que
 *   estava naquela posição no envio, e nada é criado.
 */
import { useEffect } from 'react';
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import message from 'antd/es/message';
import Modal from 'antd/es/modal';
import { enderecoAtual, renderNoRoteador } from '../../../test/comRoteador';
import { buildSolicitacaoPayload } from '../NewSolicitacaoWizard';

const {
  createSolicitacoesEmLoteMock,
  getMeMock,
  checkAvailabilityManyMock,
  lookupMunicipiosWithFiltersMock,
  lookupProjetosMock,
  lookupTiposEventoMock,
  horario,
} = vi.hoisted(() => ({
  createSolicitacoesEmLoteMock: vi.fn(),
  getMeMock: vi.fn(),
  checkAvailabilityManyMock: vi.fn(),
  lookupMunicipiosWithFiltersMock: vi.fn(),
  lookupProjetosMock: vi.fn(),
  lookupTiposEventoMock: vi.fn(),
  horario: { atual: { date: '2026-08-01', start: '09:00', end: '11:00' } },
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

/** O id que o Form do cartão dá ao campo (`evento-<chave>_<campo>`) diz de qual cartão ele é. */
function chaveDoId(id: string | undefined): number {
  return Number(/^evento-(\d+)_/.exec(id ?? '')?.[1] ?? 0);
}

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
      aria-invalid={invalido}
      data-testid={testid}
      onClick={() => {
        // Cada cartão tem o seu projeto: o do cartão de chave N é o projeto 100+N.
        const chave = chaveDoId(id);
        if (testid === 'cb-projeto') {
          onChange?.({ id: 100 + chave, label: `Projeto ${chave}`, fluxo: chave % 2 === 0 ? 'SUPER' : 'NAO_SUPER', responsavel_padrao: true });
        } else if (testid === 'cb-tipo') onChange?.({ id: 789, label: 'Formação' });
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

const NOVA = '/solicitacoes/nova';
const ESPERA = { timeout: 5000 };

function abrir() {
  return renderNoRoteador(<NewSolicitacaoWizard />, { em: NOVA, antes: ['/solicitacoes/minhas'] });
}

/*
 * Localizadores. Com o CSS do antd na página, cada `getByRole(..., { name })` custa de centenas de ms a
 * segundos no jsdom: ele calcula o estilo de cada candidato e dos ancestrais (está visível? qual é o
 * nome?), e o cache de estilo cai a cada mudança no DOM. Com 3 a 10 cartões, isso estourava 30 s na CI.
 * Estes atalhos acham o MESMO elemento pela mesma fonte do nome acessível (o texto, o aria-label ou o
 * aria-labelledby), conferem a tag do papel e que nenhum atributo o esconde. O nome acessível calculado
 * segue conferido onde ele é o assunto do teste (toHaveAccessibleName, contagem de regiões, diálogo).
 */
function semEsconder<T extends HTMLElement>(el: T | null, tag: string): T {
  expect(el?.tagName).toBe(tag);
  expect(el!.closest('[hidden], [aria-hidden="true"]')).toBeNull();
  return el!;
}
/** Botão cujo nome acessível é o próprio texto (nenhum aria-label nem aria-labelledby por cima). */
function botaoDoTexto(texto: RegExp): HTMLElement {
  const botao = semEsconder(screen.getByText(texto).closest('button'), 'BUTTON');
  expect(botao).not.toHaveAttribute('aria-label');
  expect(botao).not.toHaveAttribute('aria-labelledby');
  return botao;
}
/** Texto do elemento que dá nome via aria-labelledby. */
const rotuloDe = (el: Element): string => document.getElementById(el.getAttribute('aria-labelledby') ?? '')?.textContent ?? '';

function cartao(n: number): HTMLElement {
  const nome = new RegExp(`^Evento ${n}\\b`);
  const achados = [...document.querySelectorAll<HTMLElement>('section[aria-labelledby]')].filter((s) => nome.test(rotuloDe(s)));
  expect(achados).toHaveLength(1);
  return semEsconder(achados[0]!, 'SECTION');
}
function titulo(n: number): HTMLElement {
  const h3 = cartao(n).querySelectorAll<HTMLElement>('h3');
  expect(h3).toHaveLength(1);
  return h3[0]!;
}
const adicionar = (): HTMLElement => botaoDoTexto(/Adicionar outro evento|Limite de 10 eventos/);
const botaoCriar = (): HTMLElement => botaoDoTexto(/^Criar /);
const botaoRemover = (n: number): HTMLElement => {
  const botao = semEsconder(within(cartao(n)).getByLabelText(`Remover evento ${n}`), 'BUTTON');
  expect(botao).not.toHaveAttribute('aria-labelledby');
  return botao;
};
/** O radiogroup "vai acompanhar o evento?" do cartão (nomeado pela pergunta, via aria-labelledby). */
function grupoAcompanha(c: HTMLElement): HTMLElement {
  const pergunta = within(c).getByText('O coordenador responsável vai acompanhar o evento?');
  return semEsconder(c.querySelector<HTMLElement>(`[role="radiogroup"][aria-labelledby="${pergunta.id}"]`), 'DIV');
}

async function preencher(n: number): Promise<void> {
  const c = cartao(n);
  fireEvent.click(within(c).getByTestId('cb-projeto'));
  fireEvent.click(within(c).getByTestId('cb-tipo'));
  fireEvent.click(within(c).getByTestId('cb-municipio'));
  fireEvent.click(within(c).getByTestId('set-date'));
  fireEvent.click(within(c).getByTestId('pick-formador'));
  fireEvent.click(within(grupoAcompanha(c)).getByLabelText('Não'));
  await waitFor(() => expect(within(c).queryByText(/Verificando disponibilidade/)).not.toBeInTheDocument(), ESPERA);
}

/** 400 do lote, como o servidor responde (`errors.itens[]`, índice a partir de 0). */
function recusaDoLote(itens: unknown[], detail = `${itens.length} de 2 eventos têm problema. Nada foi criado.`) {
  return { status: 400, response: { status: 400, data: { detail, code: 'lote_invalido', errors: { itens } } } };
}

describe('NewSolicitacaoWizard — vários eventos (PR 5)', { timeout: 30000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(message, 'error').mockImplementation(vi.fn()).mockClear();
    vi.spyOn(message, 'success').mockImplementation(vi.fn()).mockClear();
    horario.atual = { date: '2026-08-01', start: '09:00', end: '11:00' };
    lookupProjetosMock.mockResolvedValue([]);
    lookupTiposEventoMock.mockResolvedValue([]);
    lookupMunicipiosWithFiltersMock.mockResolvedValue([]);
    getMeMock.mockResolvedValue({ id: 1, name: 'Ana Coordenadora', username: 'ana', is_superuser: false });
    checkAvailabilityManyMock.mockResolvedValue({ ok: true, results: [] });
    createSolicitacoesEmLoteMock.mockResolvedValue({ eventos: [{ indice: 0, id: 1, status: 'aprovado' }] });
  });

  test('começa com 1 evento, sem "Remover", e o botão diz "Criar solicitação"', async () => {
    abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    expect(screen.getAllByRole('region', { name: /^Evento \d/ })).toHaveLength(1);
    expect(screen.queryByRole('button', { name: /^Remover evento/ })).not.toBeInTheDocument();
    expect(botaoCriar()).toHaveTextContent('Criar solicitação');
  });

  test('"+ Adicionar outro evento" põe um evento em branco, leva o foco ao título dele e anuncia na região viva única', async () => {
    abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    fireEvent.click(adicionar());

    await waitFor(() => expect(titulo(2)).toHaveFocus());
    expect(titulo(2)).toHaveTextContent('Evento 2');
    // Em branco: nada do evento 1 foi copiado (nada é comum entre os eventos).
    expect(within(cartao(2)).queryByTestId('erro-horario')).not.toBeInTheDocument();
    const regioes = screen.getAllByRole('alert');
    expect(regioes).toHaveLength(1);
    expect(regioes[0]).toHaveTextContent('Evento 2 adicionado');
    expect(botaoRemover(2)).toHaveTextContent('Remover');
    expect(botaoCriar()).toHaveTextContent('Criar 2 eventos');
  });

  test('limite de 10: o botão de adicionar desabilita e diz o porquê', async () => {
    abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    const botao = adicionar();
    for (let i = 0; i < 9; i += 1) fireEvent.click(botao);
    expect(document.querySelectorAll('section[aria-labelledby^="evento-"]')).toHaveLength(10);
    expect(adicionar()).toBeDisabled();
    expect(adicionar()).toHaveTextContent('Limite de 10 eventos por vez');
    expect(botaoCriar()).toHaveTextContent('Criar 10 eventos');
  });

  test('"Remover" num evento em branco remove direto; o foco vai ao título do anterior e os números seguem a posição', async () => {
    abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    fireEvent.click(adicionar());
    fireEvent.click(adicionar());
    // Preenche o 3º para ver que ele vira o "Evento 2".
    fireEvent.click(within(cartao(3)).getByTestId('cb-projeto'));

    fireEvent.click(botaoRemover(2));

    expect(screen.getAllByRole('region', { name: /^Evento \d/ })).toHaveLength(2);
    await waitFor(() => expect(titulo(1)).toHaveFocus());
    expect(screen.getByRole('alert')).toHaveTextContent('Evento 2 removido');
    // O antigo 3º (com projeto) agora é o "Evento 2".
    expect(botaoRemover(2)).toBeInTheDocument();
    expect(botaoCriar()).toHaveTextContent('Criar 2 eventos');
  });

  test('"Remover" num evento preenchido pergunta num diálogo, começando no Cancelar; Cancelar mantém, Remover tira', async () => {
    abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    fireEvent.click(adicionar());
    fireEvent.click(within(cartao(2)).getByTestId('cb-projeto'));

    fireEvent.click(botaoRemover(2));
    // Diálogo de verdade (role=dialog, foco preso, Esc em qualquer ponto), não um balão role=tooltip:
    // pelo Tab, o foco não sai da pergunta aberta.
    const dialogo = await screen.findByRole('dialog', { name: 'Remover o evento 2?' });
    expect(dialogo).toHaveAttribute('aria-modal', 'true');
    const cancelar = within(dialogo).getByRole('button', { name: 'Cancelar' });
    await waitFor(() => expect(cancelar).toHaveFocus());
    // Com o foco no Cancelar, o leitor de tela lê também o que se perde.
    expect(cancelar).toHaveAccessibleDescription('O que você preencheu nele será perdido.');
    fireEvent.click(cancelar);
    expect(screen.getAllByRole('region', { name: /^Evento \d/ })).toHaveLength(2);
    const remover = botaoRemover(2);
    await waitFor(() => expect(remover).toHaveFocus());
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());

    // Esc também fecha e devolve o foco ao "Remover".
    fireEvent.click(remover);
    const cancelarDeNovo = within(await screen.findByRole('dialog')).getByRole('button', { name: 'Cancelar' });
    await waitFor(() => expect(cancelarDeNovo).toHaveFocus());
    fireEvent.keyDown(cancelarDeNovo, { key: 'Escape', keyCode: 27 });
    await waitFor(() => expect(remover).toHaveFocus());
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());

    fireEvent.click(botaoRemover(2));
    fireEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Remover' }));
    await waitFor(() => expect(screen.getAllByRole('region', { name: /^Evento \d/ })).toHaveLength(1));
    await waitFor(() => expect(titulo(1)).toHaveFocus());
  });

  test('campo faltando em 2 eventos: nada é enviado, o resumo tem uma linha por problema e cada linha leva ao evento', async () => {
    abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    fireEvent.click(adicionar());
    // O evento 1 só sem o município; o 2 sem nada.
    const c1 = cartao(1);
    fireEvent.click(within(c1).getByTestId('cb-projeto'));
    fireEvent.click(within(c1).getByTestId('cb-tipo'));
    fireEvent.click(within(c1).getByTestId('set-date'));
    fireEvent.click(within(c1).getByTestId('pick-formador'));
    fireEvent.click(within(grupoAcompanha(c1)).getByLabelText('Não'));

    fireEvent.click(botaoCriar());

    const resumo = await screen.findByRole('alert');
    await waitFor(() => expect(resumo).toHaveTextContent('Evento 2: Por favor selecione um projeto'), ESPERA);
    // A região viva é atômica (role=alert): o "Evento 2 adicionado" de antes não é relido com o resumo.
    expect(resumo).not.toHaveTextContent('adicionado');
    const linhas = within(resumo).getAllByRole('button');
    expect(linhas[0]).toHaveTextContent('Evento 1: Por favor selecione um município');
    expect(linhas.filter((l) => l.textContent.startsWith('Evento 2:')).length).toBeGreaterThan(1);
    expect(createSolicitacoesEmLoteMock).not.toHaveBeenCalled();
    // Os dois ficam marcados com texto (a cor não é o único sinal).
    expect(cartao(1)).toHaveAccessibleName('Evento 1 com problema');
    expect(cartao(2)).toHaveAccessibleName('Evento 2 com problema');

    fireEvent.click(linhas.at(-1)!);
    expect(titulo(2)).toHaveFocus();
  });

  test('sucesso: um envio com o payload de cada evento, mensagem com quantos vão para aprovação e vai para Minhas Solicitações', async () => {
    createSolicitacoesEmLoteMock.mockResolvedValue({
      eventos: [
        { indice: 0, id: 11, status: 'aprovado' },
        { indice: 1, id: 12, status: 'pendente' },
      ],
    });
    const { router } = abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    await preencher(1);
    fireEvent.click(adicionar());
    horario.atual = { date: '2026-08-02', start: '14:00', end: '16:00' };
    await preencher(2);

    fireEvent.click(botaoCriar());

    await waitFor(() => expect(createSolicitacoesEmLoteMock).toHaveBeenCalledTimes(1), ESPERA);
    const [eventos] = createSolicitacoesEmLoteMock.mock.calls[0] as [Record<string, unknown>[]];
    // O payload de cada evento é o de sempre (buildSolicitacaoPayload), cada um com o seu projeto.
    const base = {
      municipioId: 456,
      tipoEventoId: 789,
      tipo: '',
      encontro: '',
      segmento: '',
      observacoes: '',
      local: '',
      isOnline: false,
      formadorIds: [99],
      coordenadorResponsavelId: null,
      coordenadorAcompanha: false,
      avaliar: null,
    };
    expect(eventos).toEqual([
      buildSolicitacaoPayload({ ...base, projetoId: 101, inicio: '2026-08-01T12:00:00Z', fim: '2026-08-01T14:00:00Z' }),
      buildSolicitacaoPayload({ ...base, projetoId: 102, inicio: '2026-08-02T17:00:00Z', fim: '2026-08-02T19:00:00Z' }),
    ]);
    await waitFor(() => expect(message.success).toHaveBeenCalledWith('2 eventos criados (1 vai para aprovação)'));
    await waitFor(() => expect(enderecoAtual(router)).toBe('/solicitacoes/minhas'));
  });

  test('sucesso com 1 evento: mensagem no singular, pelo mesmo lote', async () => {
    createSolicitacoesEmLoteMock.mockResolvedValue({ eventos: [{ indice: 0, id: 11, status: 'pendente' }] });
    abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    await preencher(1);
    fireEvent.click(botaoCriar());
    await waitFor(() => expect(message.success).toHaveBeenCalledWith('1 evento criado (1 vai para aprovação)'), ESPERA);
    expect(createSolicitacoesEmLoteMock.mock.calls[0]![0]).toHaveLength(1);
  });

  test('400 do lote volta só aos eventos certos, mesmo com um evento removido antes do envio', async () => {
    abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    fireEvent.click(adicionar());
    fireEvent.click(adicionar());
    // Remove o do meio (em branco): o antigo 3º vira o "Evento 2" e vai na posição 1 do envio.
    fireEvent.click(botaoRemover(2));
    await preencher(1);
    await preencher(2);

    createSolicitacoesEmLoteMock.mockRejectedValueOnce(
      recusaDoLote([
        {
          indice: 1,
          code: 'VALIDATION_ERROR',
          detail: 'Não há compra que libere este projeto neste município.; Tipo inválido.',
          errors: {
            municipio: ['Não há compra que libere este projeto neste município.'],
            tipo_evento: ['Tipo inválido.'],
            non_field_errors: ['Responsável fora da gerência do projeto.'],
          },
        },
      ], '1 de 2 eventos tem problema. Nada foi criado.')
    );
    fireEvent.click(botaoCriar());

    const resumo = await screen.findByText('1 de 2 eventos tem problema. Nada foi criado.', undefined, ESPERA);
    expect(resumo.closest('[role="alert"]')).toHaveTextContent('Evento 2: Não há compra que libere este projeto neste município.');
    const c2 = cartao(2);
    expect(c2).toHaveAccessibleName('Evento 2 com problema');
    // Erro de campo no campo (nome igual e o mapa backend → Form); o resto no topo do cartão.
    expect(await within(c2).findByText('Não há compra que libere este projeto neste município.')).toBeInTheDocument();
    expect(within(c2).getByText('Tipo inválido.')).toBeInTheDocument();
    expect(within(c2).getByText('Responsável fora da gerência do projeto.')).toBeInTheDocument();
    expect(within(c2).getByTestId('cb-tipo')).toHaveAttribute('aria-invalid', 'true');
    // O evento 1 não tem nada.
    expect(cartao(1)).toHaveAccessibleName('Evento 1');
    expect(within(cartao(1)).queryByText(/Não há compra/)).not.toBeInTheDocument();
    // Sem toast de erro (o motivo está no evento).
    expect(message.error).not.toHaveBeenCalled();
    // O foco vai ao evento com problema.
    await waitFor(() => expect(titulo(2)).toHaveFocus());
  });

  test('mapa backend → Form: responsável, formadores, horário e o que não casa vai para o topo do evento', async () => {
    abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    await preencher(1);
    createSolicitacoesEmLoteMock.mockRejectedValueOnce(
      recusaDoLote([
        {
          indice: 0,
          code: 'VALIDATION_ERROR',
          detail: '…',
          errors: {
            coordenador: ['Coordenador fora da gerência.'],
            extra_participants: { formador_ids: ['Formador inválido.'] },
            fim: ['O fim precisa ser depois do início.'],
            campo_que_a_tela_nao_tem: ['Recusado por outro motivo.'],
          },
        },
      ], '1 de 1 eventos tem problema. Nada foi criado.')
    );
    fireEvent.click(botaoCriar());

    const c1 = cartao(1);
    await within(c1).findByText('Coordenador fora da gerência.', undefined, ESPERA);
    expect(within(c1).getByTestId('cb-responsavel')).toHaveAttribute('aria-invalid', 'true');
    expect(within(c1).getByText('Formador inválido.')).toBeInTheDocument();
    expect(within(c1).getByTestId('erro-horario')).toHaveTextContent('O fim precisa ser depois do início.');
    expect(within(c1).getByText('Recusado por outro motivo.')).toBeInTheDocument();
  });

  test('conflito no lote: os dois eventos ficam vermelhos com quem choca, o Criar trava e mudar o horário de qualquer evento limpa', async () => {
    abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    await preencher(1);
    fireEvent.click(adicionar());
    await preencher(2);
    const bloqueado = (outro: number) => ({
      usuario_id: 99,
      usuario_nome: 'Bruno Formador',
      conflicts: [{ code: 'X', title: 'Sobreposição de evento', detail: `Choca com o evento ${outro} desta lista (09:00–11:00)` }],
    });
    createSolicitacoesEmLoteMock.mockRejectedValueOnce(
      recusaDoLote([
        { indice: 0, code: 'availability_conflict', detail: 'Não é possível criar o evento: Bruno Formador tem outro evento neste horário.', blocked_participants: [bloqueado(2)] },
        { indice: 1, code: 'availability_conflict', detail: 'Não é possível criar o evento: Bruno Formador tem outro evento neste horário.', blocked_participants: [bloqueado(1)] },
      ])
    );
    fireEvent.click(botaoCriar());

    expect(await within(cartao(1)).findByText('Choca com o evento 2 desta lista (09:00–11:00)', undefined, ESPERA)).toBeInTheDocument();
    expect(within(cartao(2)).getByText('Choca com o evento 1 desta lista (09:00–11:00)')).toBeInTheDocument();
    expect(cartao(1)).toHaveAccessibleName('Evento 1 com problema');
    expect(cartao(2)).toHaveAccessibleName('Evento 2 com problema');
    // Uma só região viva: o resumo. O alerta do cartão não é outra.
    expect(screen.getAllByRole('alert')).toHaveLength(1);
    await waitFor(() => expect(botaoCriar()).toBeDisabled());
    expect(message.error).not.toHaveBeenCalled();

    // Trocar o horário do evento 2 limpa o erro dos DOIS (o choque depende do outro).
    horario.atual = { date: '2026-08-01', start: '14:00', end: '16:00' };
    fireEvent.click(within(cartao(2)).getByTestId('set-date'));
    await waitFor(() => expect(within(cartao(1)).queryByText(/Choca com o evento 2/)).not.toBeInTheDocument());
    expect(cartao(1)).toHaveAccessibleName('Evento 1');
    await waitFor(() => expect(botaoCriar()).not.toBeDisabled());
  });

  test('adicionar um evento também limpa os erros do lote', async () => {
    abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    await preencher(1);
    createSolicitacoesEmLoteMock.mockRejectedValueOnce(
      recusaDoLote([{ indice: 0, code: 'VALIDATION_ERROR', detail: 'x', errors: { non_field_errors: ['Recusado.'] } }])
    );
    fireEvent.click(botaoCriar());
    await within(cartao(1)).findByText('Recusado.', undefined, ESPERA);
    fireEvent.click(adicionar());
    await waitFor(() => expect(within(cartao(1)).queryByText('Recusado.')).not.toBeInTheDocument());
  });

  test('sem resposta: o aviso fica no resumo do topo (não some) e manda conferir antes de enviar de novo', async () => {
    createSolicitacoesEmLoteMock.mockRejectedValueOnce(new TypeError('Sem conexão com o servidor.'));
    abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    await preencher(1);
    fireEvent.click(adicionar());
    await preencher(2);
    fireEvent.click(botaoCriar());
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(
        'Não houve resposta, e não dá para saber se os 2 eventos foram criados. Confira em Minhas Solicitações antes de enviar de novo.'
      ), ESPERA
    );
    expect(message.error).not.toHaveBeenCalled();
  });

  test('depois de um envio sem resposta, o próximo Criar pergunta antes de mandar de novo (mesmo depois de mudar um evento)', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    createSolicitacoesEmLoteMock.mockRejectedValueOnce(new TypeError('Sem conexão com o servidor.'));
    abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    await preencher(1);
    fireEvent.click(adicionar());
    await preencher(2);
    fireEvent.click(botaoCriar());
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Não houve resposta'), ESPERA);

    // Mudar um evento tira o resumo, mas não o risco: o lote pode ter sido gravado.
    fireEvent.click(within(cartao(1)).getByTestId('cb-tipo'));
    fireEvent.click(botaoCriar());
    await waitFor(() => expect(confirmar).toHaveBeenCalledTimes(1), ESPERA);
    const opcoes = confirmar.mock.calls[0]![0];
    expect(opcoes.title).toBe('Enviar de novo?');
    expect(opcoes.autoFocusButton).toBe('cancel');
    expect(createSolicitacoesEmLoteMock).toHaveBeenCalledTimes(1);

    // Cancelar não envia.
    await act(async () => { opcoes.onCancel?.(); });
    await waitFor(() => expect(botaoCriar()).toHaveTextContent('Criar 2 eventos'));
    expect(createSolicitacoesEmLoteMock).toHaveBeenCalledTimes(1);

    // Confirmar envia; com resposta, o próximo envio não pergunta mais.
    createSolicitacoesEmLoteMock.mockRejectedValueOnce(
      recusaDoLote([{ indice: 0, code: 'VALIDATION_ERROR', detail: 'x', errors: { non_field_errors: ['Recusado.'] } }])
    );
    fireEvent.click(botaoCriar());
    await waitFor(() => expect(confirmar).toHaveBeenCalledTimes(2), ESPERA);
    await act(async () => { confirmar.mock.calls[1]![0].onOk?.(); });
    await waitFor(() => expect(createSolicitacoesEmLoteMock).toHaveBeenCalledTimes(2), ESPERA);
    await within(cartao(1)).findByText('Recusado.', undefined, ESPERA);
    fireEvent.click(botaoCriar());
    await waitFor(() => expect(createSolicitacoesEmLoteMock).toHaveBeenCalledTimes(3), ESPERA);
    expect(confirmar).toHaveBeenCalledTimes(2);
    confirmar.mockRestore();
  });

  test('com o lote em voo, sair da página não descarta: o aviso diz que o envio segue e a página espera a resposta', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const destruir = vi.fn();
    const informar = vi.spyOn(Modal, 'info').mockImplementation(() => ({ destroy: destruir, update: vi.fn() }));
    let resolver: (valor: unknown) => void = () => undefined;
    createSolicitacoesEmLoteMock.mockImplementationOnce(() => new Promise((resolve) => { resolver = resolve; }));
    const { router } = abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    await preencher(1);
    fireEvent.click(botaoCriar());
    await waitFor(() => expect(createSolicitacoesEmLoteMock).toHaveBeenCalledTimes(1), ESPERA);

    fireEvent.click(botaoDoTexto(/Voltar para Minhas Solicitações/));
    await waitFor(() => expect(informar).toHaveBeenCalledTimes(1));
    expect(confirmar).not.toHaveBeenCalled();
    const opcoes = informar.mock.calls[0]![0];
    expect(String(opcoes.title)).toMatch(/sendo criad/);
    expect(String(opcoes.content)).toMatch(/não cancela/);
    // Fechar o aviso fica na página; o envio segue.
    act(() => void opcoes.onOk?.());
    expect(enderecoAtual(router)).toBe(NOVA);

    // Outra tentativa de sair e a resposta chega com o aviso aberto: ele fecha e vai a Minhas Solicitações.
    fireEvent.click(botaoDoTexto(/Voltar para Minhas Solicitações/));
    await waitFor(() => expect(informar).toHaveBeenCalledTimes(2));
    act(() => resolver({ eventos: [{ indice: 0, id: 5, status: 'aprovado' }] }));
    await waitFor(() => expect(enderecoAtual(router)).toBe('/solicitacoes/minhas'), ESPERA);
    expect(destruir).toHaveBeenCalled();
    expect(message.success).toHaveBeenCalledWith('1 evento criado');
    expect(confirmar).not.toHaveBeenCalled();
    confirmar.mockRestore();
    informar.mockRestore();
  });

  test('conflito com evento aprovado (fora da lista) continua valendo quando outro evento muda ou sai', async () => {
    abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    await preencher(1);
    fireEvent.click(adicionar());
    horario.atual = { date: '2026-08-02', start: '14:00', end: '16:00' };
    await preencher(2);
    createSolicitacoesEmLoteMock.mockRejectedValueOnce(
      recusaDoLote([
        {
          indice: 0,
          code: 'availability_conflict',
          detail: 'Não é possível criar o evento: Bruno Formador tem outro evento aprovado neste horário.',
          blocked_participants: [
            {
              usuario_id: 99,
              usuario_nome: 'Bruno Formador',
              conflicts: [{ code: 'X', title: 'Sobreposição', detail: 'Conflita com evento aprovado #5 (09:00–11:00)', ref_id: 5 }],
            },
          ],
        },
      ], '1 de 2 eventos tem problema. Nada foi criado.')
    );
    fireEvent.click(botaoCriar());
    await within(cartao(1)).findByText('Conflita com evento aprovado #5 (09:00–11:00)', undefined, ESPERA);
    await waitFor(() => expect(botaoCriar()).toBeDisabled());

    // Mudar o horário do evento 2 não mexe no choque do evento 1 com o banco.
    horario.atual = { date: '2026-08-03', start: '14:00', end: '16:00' };
    fireEvent.click(within(cartao(2)).getByTestId('set-date'));
    await waitFor(() => expect(within(cartao(2)).queryByText(/Verificando disponibilidade/)).not.toBeInTheDocument(), ESPERA);
    expect(within(cartao(1)).getByText('Conflita com evento aprovado #5 (09:00–11:00)')).toBeInTheDocument();
    expect(botaoCriar()).toBeDisabled();

    // Nem tirar o evento 2.
    fireEvent.click(botaoRemover(2));
    fireEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Remover' }));
    await waitFor(() => expect(screen.getAllByRole('region', { name: /^Evento \d/ })).toHaveLength(1));
    expect(within(cartao(1)).getByText('Conflita com evento aprovado #5 (09:00–11:00)')).toBeInTheDocument();
    expect(botaoCriar()).toBeDisabled();
  });

  test('conflito entre dois eventos da lista continua valendo quando um terceiro evento, fora do choque, muda', async () => {
    abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    await preencher(1);
    fireEvent.click(adicionar());
    await preencher(2);
    fireEvent.click(adicionar());
    horario.atual = { date: '2026-08-02', start: '14:00', end: '16:00' };
    await preencher(3);
    const bloqueado = (outro: number) => ({
      usuario_id: 99,
      usuario_nome: 'Bruno Formador',
      conflicts: [{ code: 'X', title: 'Sobreposição', detail: `Conflita com o evento ${outro} desta lista (09:00–11:00)` }],
    });
    createSolicitacoesEmLoteMock.mockRejectedValueOnce(
      recusaDoLote([
        { indice: 0, code: 'availability_conflict', detail: 'Não é possível criar o evento: Bruno Formador tem outro evento desta lista neste horário.', blocked_participants: [bloqueado(2)] },
        { indice: 1, code: 'availability_conflict', detail: 'Não é possível criar o evento: Bruno Formador tem outro evento desta lista neste horário.', blocked_participants: [bloqueado(1)] },
      ], '2 de 3 eventos têm problema. Nada foi criado.')
    );
    fireEvent.click(botaoCriar());
    await within(cartao(1)).findByText('Conflita com o evento 2 desta lista (09:00–11:00)', undefined, ESPERA);
    await waitFor(() => expect(botaoCriar()).toBeDisabled());

    // Mudar a agenda do evento 3 não mexe no choque entre o 1 e o 2.
    horario.atual = { date: '2026-08-03', start: '14:00', end: '16:00' };
    fireEvent.click(within(cartao(3)).getByTestId('set-date'));
    await waitFor(() => expect(within(cartao(3)).queryByText(/Verificando disponibilidade/)).not.toBeInTheDocument(), ESPERA);
    expect(within(cartao(1)).getByText('Conflita com o evento 2 desta lista (09:00–11:00)')).toBeInTheDocument();
    expect(within(cartao(2)).getByText('Conflita com o evento 1 desta lista (09:00–11:00)')).toBeInTheDocument();
    expect(cartao(1)).toHaveAccessibleName('Evento 1 com problema');
    expect(botaoCriar()).toBeDisabled();

    // Tirar o evento 3 também não.
    fireEvent.click(botaoRemover(3));
    fireEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Remover' }));
    await waitFor(() => expect(screen.getAllByRole('region', { name: /^Evento \d/ })).toHaveLength(2));
    expect(within(cartao(1)).getByText('Conflita com o evento 2 desta lista (09:00–11:00)')).toBeInTheDocument();
    expect(botaoCriar()).toBeDisabled();

    // Mudar o parceiro do choque (o evento 2) derruba o conflito dos dois.
    fireEvent.click(within(cartao(2)).getByTestId('set-date'));
    await waitFor(() => expect(within(cartao(1)).queryByText(/Conflita com o evento 2/)).not.toBeInTheDocument());
    expect(within(cartao(2)).queryByText(/Conflita com o evento 1/)).not.toBeInTheDocument();
  });

  test('com o conflito ainda valendo, mudar outra coisa mantém o evento vermelho e "com problema"', async () => {
    abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    await preencher(1);
    fireEvent.click(adicionar());
    await preencher(2);
    const bloqueado = (outro: number) => ({
      usuario_id: 99,
      usuario_nome: 'Bruno Formador',
      conflicts: [{ code: 'X', title: 'Sobreposição', detail: `Conflita com o evento ${outro} desta lista (09:00–11:00)` }],
    });
    createSolicitacoesEmLoteMock.mockRejectedValueOnce(
      recusaDoLote([
        { indice: 0, code: 'availability_conflict', detail: 'Não é possível criar o evento: Bruno Formador tem outro evento desta lista neste horário.', blocked_participants: [bloqueado(2)] },
        { indice: 1, code: 'availability_conflict', detail: 'Não é possível criar o evento: Bruno Formador tem outro evento desta lista neste horário.', blocked_participants: [bloqueado(1)] },
      ])
    );
    fireEvent.click(botaoCriar());
    await within(cartao(1)).findByText('Conflita com o evento 2 desta lista (09:00–11:00)', undefined, ESPERA);
    expect(cartao(1)).toHaveAccessibleName('Evento 1 com problema');

    // Mudar o tipo (fora da agenda) tira o resumo, mas o conflito segue e o cartão segue marcado.
    fireEvent.click(within(cartao(1)).getByTestId('cb-tipo'));
    await waitFor(() => expect(screen.queryByText('2 de 2 eventos têm problema. Nada foi criado.')).not.toBeInTheDocument());
    expect(within(cartao(1)).getByText('Conflita com o evento 2 desta lista (09:00–11:00)')).toBeInTheDocument();
    expect(cartao(1)).toHaveAccessibleName('Evento 1 com problema');
    expect(cartao(2)).toHaveAccessibleName('Evento 2 com problema');
    expect(botaoCriar()).toBeDisabled();
  });

  test('com o envio em andamento, os eventos e o "Adicionar" ficam travados; nada se perde nem é criado à revelia', async () => {
    let recusar: (erro: unknown) => void = () => undefined;
    createSolicitacoesEmLoteMock.mockImplementationOnce(() => new Promise((_resolve, reject) => { recusar = reject; }));
    abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    await preencher(1);
    fireEvent.click(adicionar());
    await preencher(2);
    fireEvent.click(botaoCriar());
    await waitFor(() => expect(createSolicitacoesEmLoteMock).toHaveBeenCalledTimes(1), ESPERA);

    // O jsdom não implementa `inert` (no navegador ele barra clique, teclado e foco): confere o atributo.
    const inerte = (el: Element): boolean => el.closest('[inert]') !== null;
    await waitFor(() => expect(inerte(cartao(1))).toBe(true));
    expect(inerte(cartao(2))).toBe(true);
    expect(inerte(adicionar())).toBe(true);
    expect(inerte(botaoRemover(2))).toBe(true);
    expect(inerte(botaoDoTexto(/Criar 2 eventos/))).toBe(false);

    // A recusa destrava a página e leva o foco ao evento com problema.
    act(() => recusar(recusaDoLote([{ indice: 1, code: 'VALIDATION_ERROR', detail: 'x', errors: { non_field_errors: ['Recusado.'] } }])));
    await within(cartao(2)).findByText('Recusado.', undefined, ESPERA);
    expect(inerte(cartao(1))).toBe(false);
    expect(inerte(adicionar())).toBe(false);
    await waitFor(() => expect(titulo(2)).toHaveFocus());
  });

  test('resposta que chega depois de o horário mudar: o conflito do horário antigo não aparece nem trava o Criar', async () => {
    let recusar: (erro: unknown) => void = () => undefined;
    createSolicitacoesEmLoteMock.mockImplementationOnce(() => new Promise((_resolve, reject) => { recusar = reject; }));
    abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    await preencher(1);
    fireEvent.click(botaoCriar());
    await waitFor(() => expect(createSolicitacoesEmLoteMock).toHaveBeenCalledTimes(1), ESPERA);

    // No navegador o cartão está inerte; aqui o clique passa e prova a segunda defesa.
    horario.atual = { date: '2026-08-01', start: '14:00', end: '16:00' };
    fireEvent.click(within(cartao(1)).getByTestId('set-date'));
    act(() =>
      recusar(
        recusaDoLote([
          {
            indice: 0,
            code: 'availability_conflict',
            detail: 'Não é possível criar o evento: Bruno Formador tem outro evento neste horário.',
            blocked_participants: [
              { usuario_id: 99, usuario_nome: 'Bruno Formador', conflicts: [{ code: 'X', title: 'Sobreposição', detail: 'Choca 09:00-11:00' }] },
            ],
          },
        ], '1 de 1 eventos tem problema. Nada foi criado.')
      )
    );
    // Com 1 evento, o título não fala em "1 de 1 eventos" (o texto do servidor é para a lista).
    await screen.findByText('Não foi possível criar a solicitação. Nada foi criado.', undefined, ESPERA);
    expect(screen.queryByText(/1 de 1/)).not.toBeInTheDocument();
    expect(screen.queryByText('Choca 09:00-11:00')).not.toBeInTheDocument();
    await waitFor(() => expect(botaoCriar()).not.toBeDisabled());
  });

  test('um evento extra em branco não conta como preenchido: sair não pergunta', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm');
    const { router } = abrir();
    await screen.findByRole('region', { name: /^Evento 1/ });
    fireEvent.click(adicionar());
    act(() => {
      void router.navigate('/solicitacoes/minhas');
    });
    await waitFor(() => expect(enderecoAtual(router)).toBe('/solicitacoes/minhas'));
    expect(confirmar).not.toHaveBeenCalled();
    confirmar.mockRestore();
  });
});
