/**
 * Minhas Solicitações — item 36 (19/10/2026).
 *
 * - Paginação no servidor (antes: as 100 primeiras, paginadas no cliente; da 6ª página em diante, vazio).
 * - Falha ao carregar: o motivo e "Tentar de novo", não as linhas da carga anterior.
 * - Busca: espera a pessoa parar de digitar e só a resposta mais recente vale.
 * - Excluir cita a solicitação e começa no Cancelar.
 * - Evento já no Google Agenda: a tela diz o motivo e a quem pedir, por um botão que o teclado alcança.
 * - Sem rolagem horizontal: no celular, as ações vão para "Mais ações".
 */
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router';
import Modal from 'antd/es/modal';

const { listSolicitacoesMock, deleteSolicitacaoMock } = vi.hoisted(() => ({
  listSolicitacoesMock: vi.fn(),
  deleteSolicitacaoMock: vi.fn(),
}));

vi.mock('../../../api/solicitacoes', () => ({
  listSolicitacoes: listSolicitacoesMock,
  deleteSolicitacao: deleteSolicitacaoMock,
}));

vi.mock('../../../components/MeetLink', () => ({
  MeetLink: ({ href }: { href: string | null }) => (href ? <a href={href}>Entrar na reunião</a> : null),
}));

import { definirLarguraTela } from '../../../test/larguraTela';
import MySolicitacoesPage from '../MySolicitacoesPage';
import type { Solicitacao } from '../../../types';

function renderPage() {
  return render(
    <MemoryRouter>
      <MySolicitacoesPage />
    </MemoryRouter>
  );
}

function makeSolic(overrides: Partial<Solicitacao> = {}): Solicitacao {
  return {
    id: 1,
    usuario: 1,
    municipio: 5,
    municipio_nome: 'Juazeiro do Norte',
    projeto: 10,
    projeto_nome: 'Vidas',
    tipo_evento: 2,
    tipo_evento_nome: 'Formação',
    tipo: null,
    encontro: null,
    segmento: null,
    coordenador_acompanha: false,
    coordenador: null,
    coordenador_nome: null,
    inicio: '2026-05-10T13:00:00Z',
    fim: '2026-05-10T17:00:00Z',
    status: 'pendente',
    observacoes: null,
    local: null,
    is_online: false,
    external_event_id: null,
    created_at: '2026-05-01T12:00:00Z',
    updated_at: '2026-05-01T12:00:00Z',
    participations: [],
    fluxo: 'NAO_SUPER',
    gcal_status: 'NONE',
    gcal_last_sync_at: null,
    gcal_last_error: null,
    meet_link: null,
    ...overrides,
  };
}

function pagina(itens: Solicitacao[], count = itens.length) {
  return { count, next: null, previous: null, results: itens };
}

describe('MySolicitacoesPage — item 36', { timeout: 20000 }, () => {
  beforeEach(() => {
    listSolicitacoesMock.mockReset();
    deleteSolicitacaoMock.mockReset();
  });

  test('pagina no servidor: a página 2 é pedida ao backend, com desempate por id na ordem', async () => {
    listSolicitacoesMock.mockResolvedValue(pagina([makeSolic()], 150));
    renderPage();
    await waitFor(() =>
      expect(listSolicitacoesMock).toHaveBeenCalledWith({ mine: 'true', ordering: '-inicio,id', page: 1, page_size: 20 })
    );
    fireEvent.click(await screen.findByTitle('2'));
    await waitFor(() =>
      expect(listSolicitacoesMock).toHaveBeenLastCalledWith({ mine: 'true', ordering: '-inicio,id', page: 2, page_size: 20 })
    );
  });

  test('falha ao carregar mostra o motivo e "Tentar de novo", sem as linhas antigas', async () => {
    listSolicitacoesMock
      .mockResolvedValueOnce(pagina([makeSolic({ municipio_nome: 'Crato' })]))
      .mockRejectedValueOnce(new Error('Servidor indisponível.'))
      .mockResolvedValueOnce(pagina([makeSolic({ municipio_nome: 'Sobral' })]));
    renderPage();
    expect(await screen.findByText('Crato')).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Filtrar por status' }));
    fireEvent.click(await screen.findByTitle('Reprovadas'));
    expect(await screen.findByText('Não foi possível carregar a lista.')).toBeInTheDocument();
    expect(screen.getByText('Servidor indisponível.')).toBeInTheDocument();
    expect(screen.queryByText('Crato')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }));
    expect(await screen.findByText('Sobral')).toBeInTheDocument();
  });

  test('busca: espera parar de digitar e a resposta antiga não toma o lugar da nova', async () => {
    let soltarInicial: (v: unknown) => void = () => {};
    listSolicitacoesMock
      .mockImplementationOnce(() => new Promise((resolve) => { soltarInicial = resolve; }))
      .mockResolvedValue(pagina([makeSolic({ municipio_nome: 'Crato' })]));
    renderPage();
    const busca = screen.getByRole('searchbox', { name: 'Buscar solicitações' });
    fireEvent.change(busca, { target: { value: 'Cr' } });
    fireEvent.change(busca, { target: { value: 'Crato' } });
    expect(await screen.findByText('Crato')).toBeInTheDocument();
    expect(listSolicitacoesMock).not.toHaveBeenCalledWith(expect.objectContaining({ q: 'Cr' }));
    expect(listSolicitacoesMock).toHaveBeenLastCalledWith({ mine: 'true', q: 'Crato', ordering: '-inicio,id', page: 1, page_size: 20 });

    // A carga inicial (sem busca) chega depois: não pode substituir o resultado da busca.
    await act(async () => soltarInicial(pagina([makeSolic({ municipio_nome: 'Fortaleza' })])));
    expect(screen.queryByText('Fortaleza')).not.toBeInTheDocument();
    expect(screen.getByText('Crato')).toBeInTheDocument();
  });

  test('Excluir cita a solicitação e começa no Cancelar', async () => {
    const confirmar = vi
      .spyOn(Modal, 'confirm')
      .mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn(), then: vi.fn() }) as never);
    listSolicitacoesMock.mockResolvedValue(pagina([makeSolic({ id: 7, municipio_nome: 'Crato', projeto_nome: 'Vidas' })]));
    deleteSolicitacaoMock.mockResolvedValue(undefined);
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: 'Excluir: 10/05/2026 · Crato' }));
    expect(confirmar).toHaveBeenCalledTimes(1);
    const opcoes = confirmar.mock.calls[0]![0];
    expect(opcoes).toMatchObject({ autoFocusButton: 'cancel', okText: 'Sim, excluir', cancelText: 'Cancelar' });
    expect(String(opcoes.content)).toContain('10/05/2026 10:00 · Crato · Vidas');
    await act(async () => {
      await opcoes.onOk?.();
    });
    expect(deleteSolicitacaoMock).toHaveBeenCalledWith(7);
    confirmar.mockRestore();
  });

  test('depois de excluir, o foco fica na lista mesmo com a recarga ainda em andamento', async () => {
    const confirmar = vi
      .spyOn(Modal, 'confirm')
      .mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn(), then: vi.fn() }) as never);
    listSolicitacoesMock
      .mockResolvedValueOnce(pagina([makeSolic({ id: 7, municipio_nome: 'Crato' })]))
      .mockImplementation(() => new Promise(() => {})); // rede lenta: a recarga não chega
    deleteSolicitacaoMock.mockResolvedValue(undefined);
    renderPage();
    const excluir = await screen.findByRole('button', { name: 'Excluir: 10/05/2026 · Crato' });
    const lista = screen.getByRole('region', { name: 'Lista de solicitações' });

    // Cancelar: o rc-dialog devolve o foco ao Excluir (focusTriggerAfterClose) e ele fica lá.
    excluir.focus();
    fireEvent.click(excluir);
    act(() => confirmar.mock.calls[0]![0].afterClose?.());
    expect(document.activeElement).toBe(excluir);

    // Sim, excluir: ao fim da animação de saída o rc-dialog devolve o foco ao Excluir da linha que
    // vai sair e só então chama afterClose; o foco tem de terminar na lista.
    fireEvent.click(excluir);
    const opcoes = confirmar.mock.calls[1]![0];
    await act(async () => {
      await opcoes.onOk?.();
    });
    expect(deleteSolicitacaoMock).toHaveBeenCalledWith(7);
    excluir.focus();
    act(() => opcoes.afterClose?.());
    expect(document.activeElement).toBe(lista);
    confirmar.mockRestore();
  });

  test('evento já no Google Agenda: sem Editar/Excluir, com o motivo e a quem pedir', async () => {
    const informar = vi
      .spyOn(Modal, 'info')
      .mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn(), then: vi.fn() }) as never);
    listSolicitacoesMock.mockResolvedValue(
      pagina([makeSolic({ id: 8, municipio_nome: 'Crato', status: 'aprovado', gcal_status: 'PUBLISHED' })])
    );
    renderPage();
    expect(await screen.findByText('Na agenda')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Editar:/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Excluir:/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Por que não dá para editar nem excluir: 10/05/2026 · Crato' }));
    expect(informar).toHaveBeenCalledTimes(1);
    const texto = String(informar.mock.calls[0]![0].content);
    expect(texto).toContain('já está no Google Agenda');
    expect(texto).toContain('Apoio de Coordenação');
    informar.mockRestore();
  });

  test('evento no Google Agenda pela planilha: sem Editar/Excluir, com o motivo próprio', async () => {
    const informar = vi
      .spyOn(Modal, 'info')
      .mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn(), then: vi.fn() }) as never);
    listSolicitacoesMock.mockResolvedValue(
      pagina([
        makeSolic({
          id: 10,
          municipio_nome: 'Crato',
          status: 'aprovado',
          gcal_status: 'NONE',
          publicado_fora_do_sistema: true,
        }),
      ])
    );
    renderPage();
    expect(await screen.findByText('Na agenda')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Editar:/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Excluir:/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Por que não dá para editar nem excluir: 10/05/2026 · Crato' }));
    const texto = String(informar.mock.calls[0]![0].content);
    expect(texto).toContain('já está no Google Agenda pela planilha');
    expect(texto).toContain('Apoio de Coordenação');
    // A publicação não foi feita pelo sistema: não há o que cancelar aqui.
    expect(texto).not.toMatch(/cancele a publicação/);
    informar.mockRestore();
  });

  test('SUPER aprovada no Google Agenda: o motivo não promete excluir depois de cancelar', async () => {
    const informar = vi
      .spyOn(Modal, 'info')
      .mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn(), then: vi.fn() }) as never);
    listSolicitacoesMock.mockResolvedValue(
      pagina([
        makeSolic({ id: 9, municipio_nome: 'Crato', fluxo: 'SUPER', status: 'aprovado', gcal_status: 'PUBLISHED' }),
      ])
    );
    renderPage();
    expect(await screen.findByText('Na agenda')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Por que não dá para editar nem excluir: 10/05/2026 · Crato' }));
    const texto = String(informar.mock.calls[0]![0].content);
    expect(texto).not.toMatch(/excluir aqui/);
    expect(texto).toContain('Solicitações do fluxo Superintendência só podem ser excluídas enquanto estão pendentes.');
    // A saída real, a mesma que o backend dá ao recusar a exclusão (perform_destroy).
    expect(texto).toContain('fale com a administração do sistema');
    informar.mockRestore();
  });

  test('no celular, as ações vão para "Mais ações" e o município fica junto da data', async () => {
    listSolicitacoesMock.mockResolvedValue(pagina([makeSolic({ municipio_nome: 'Crato' })]));
    renderPage();
    await screen.findByText('Crato');
    act(() => definirLarguraTela(360));
    expect(screen.getByRole('button', { name: 'Mais ações: 10/05/2026 · Crato' })).toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Município' })).not.toBeInTheDocument();
    expect(screen.getByText('Crato')).toBeInTheDocument();
  });
});

// Excluir um evento no Google tira dos dois lados (opção A do dono: sem poder novo). Quem vê Excluir
// num evento no Google é quem já pode excluir E já pode tirar do Google (`pode_tirar_do_google`).
describe('MySolicitacoesPage — Excluir sai do sistema e do Google', { timeout: 20000 }, () => {
  beforeEach(() => {
    listSolicitacoesMock.mockReset();
    deleteSolicitacaoMock.mockReset();
  });

  test.each([
    {
      caso: 'publicado, com Meet',
      row: { gcal_status: 'PUBLISHED' as const, external_event_id: 'evt-1', meet_link: 'https://meet.google.com/abc-defg-hij' },
      texto: 'Ele sai do sistema e do Google Agenda, junto com o link do Meet. Não dá para desfazer.',
    },
    {
      caso: 'publicado, presencial (sem Meet)',
      row: { gcal_status: 'PUBLISHED' as const, external_event_id: 'evt-1', meet_link: null },
      texto: 'Ele sai do sistema e do Google Agenda. Não dá para desfazer.',
    },
    {
      caso: 'erro com o evento ainda no Google',
      row: { gcal_status: 'ERROR' as const, external_event_id: 'evt-1' },
      texto: 'Ele sai do sistema e do Google Agenda, se estiver lá. Não dá para desfazer.',
    },
    {
      // A publicação que falhou pode ter criado o evento no Google sem gravar o id.
      caso: 'erro sem id',
      row: { gcal_status: 'ERROR' as const, external_event_id: null },
      texto: 'Ele sai do sistema e do Google Agenda, se estiver lá. Não dá para desfazer.',
    },
  ])('$caso, para quem pode tirar do Google: Excluir aparece e avisa que sai do Google também', async ({ row, texto }) => {
    const confirmar = vi
      .spyOn(Modal, 'confirm')
      .mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn(), then: vi.fn() }) as never);
    listSolicitacoesMock.mockResolvedValue(
      pagina([
        makeSolic({ id: 7, municipio_nome: 'Crato', projeto_nome: 'Vidas', status: 'aprovado', pode_tirar_do_google: true, ...row }),
      ])
    );
    deleteSolicitacaoMock.mockResolvedValue(undefined);
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Excluir: 10/05/2026 · Crato' }));
    const opcoes = confirmar.mock.calls[0]![0];
    expect(opcoes.title).toBe('Excluir evento?');
    expect(String(opcoes.content)).toBe(`10/05/2026 10:00 · Crato · Vidas. ${texto}`);
    expect(opcoes).toMatchObject({ autoFocusButton: 'cancel', okText: 'Sim, excluir', cancelText: 'Cancelar' });
    await act(async () => {
      await opcoes.onOk?.();
    });
    expect(deleteSolicitacaoMock).toHaveBeenCalledWith(7);
    confirmar.mockRestore();
  });

  test('publicado, para quem pode tirar do Google: sem o aviso de pedir ao Apoio', async () => {
    listSolicitacoesMock.mockResolvedValue(
      pagina([
        makeSolic({ id: 8, municipio_nome: 'Crato', status: 'aprovado', gcal_status: 'PUBLISHED', pode_tirar_do_google: true }),
      ])
    );
    renderPage();
    expect(await screen.findByRole('button', { name: 'Excluir: 10/05/2026 · Crato' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Por que não dá para editar nem excluir/ })).not.toBeInTheDocument();
    // Editar continua fechado enquanto está no Google; o motivo diz o que ela mesma pode fazer.
    const informar = vi
      .spyOn(Modal, 'info')
      .mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn(), then: vi.fn() }) as never);
    fireEvent.click(screen.getByRole('button', { name: 'Por que não dá para editar: 10/05/2026 · Crato' }));
    const texto = String(informar.mock.calls[0]![0].content);
    expect(texto).toContain('tire-o do Google antes');
    // Diz onde: Minhas Solicitações não tem a ação de tirar do Google.
    expect(texto).toContain('Publicar na agenda');
    expect(texto).not.toContain('Apoio de Coordenação');
    informar.mockRestore();
  });

  test.each([
    { caso: 'com id', external_event_id: 'evt-1' },
    { caso: 'sem id', external_event_id: null },
  ])('erro $caso, para quem não pode tirar do Google: sem Excluir, e o motivo fala de excluir', async ({ external_event_id }) => {
    listSolicitacoesMock.mockResolvedValue(
      pagina([
        makeSolic({
          id: 8,
          municipio_nome: 'Crato',
          status: 'aprovado',
          gcal_status: 'ERROR',
          external_event_id,
          pode_tirar_do_google: false,
        }),
      ])
    );
    renderPage();
    expect(await screen.findByText('Crato')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Excluir:/ })).not.toBeInTheDocument();
    // Em ERROR a edição continua aberta: o motivo explica a exclusão, não a edição.
    expect(screen.getByRole('button', { name: 'Editar: 10/05/2026 · Crato' })).toBeInTheDocument();
    const informar = vi
      .spyOn(Modal, 'info')
      .mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn(), then: vi.fn() }) as never);
    fireEvent.click(screen.getByRole('button', { name: 'Por que não dá para excluir: 10/05/2026 · Crato' }));
    const texto = String(informar.mock.calls[0]![0].content);
    expect(texto).toContain('Para excluir, peça ao Apoio de Coordenação da sua gerência ou ao Controle');
    expect(texto).not.toContain('editar');
    informar.mockRestore();
  });

  test('na planilha (não adotado): sem Excluir mesmo para quem pode tirar do Google', async () => {
    listSolicitacoesMock.mockResolvedValue(
      pagina([
        makeSolic({
          id: 10,
          municipio_nome: 'Crato',
          status: 'aprovado',
          gcal_status: 'NONE',
          publicado_fora_do_sistema: true,
          pode_tirar_do_google: true,
        }),
      ])
    );
    renderPage();
    expect(await screen.findByText('Na agenda')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Excluir:/ })).not.toBeInTheDocument();
  });

  test('fora do Google, a confirmação continua a de sempre', async () => {
    const confirmar = vi
      .spyOn(Modal, 'confirm')
      .mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn(), then: vi.fn() }) as never);
    listSolicitacoesMock.mockResolvedValue(
      pagina([makeSolic({ id: 7, municipio_nome: 'Crato', projeto_nome: 'Vidas', pode_tirar_do_google: true })])
    );
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: 'Excluir: 10/05/2026 · Crato' }));
    const opcoes = confirmar.mock.calls[0]![0];
    expect(opcoes.title).toBe('Excluir solicitação?');
    expect(String(opcoes.content)).toBe('10/05/2026 10:00 · Crato · Vidas. Esta ação não pode ser desfeita.');
    confirmar.mockRestore();
  });
});
