/**
 * G30 (Programa C) — Notificações Internas e Ações Internas sem rolagem horizontal.
 *
 * As duas tabelas tinham `scroll.x` (760 e 1200). Agora são o ResponsiveTable: a identidade (título
 * da notificação, nome da ação), o estado e as ações (AcoesLinha: "Marcar lida"; "Registrar âncora" e
 * "Concluir"; no celular, o menu "Mais ações") ficam sempre na linha; o resto sobe por largura e o que
 * some vai para a linha expandida. A mensagem da notificação, que já abria na linha expandida, continua
 * lá (coluna só do detalhe).
 */
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

import { definirLarguraTela } from '../../../test/larguraTela';
import type { AcaoInstancia, NotificacaoInterna } from '../../../types/acoesNotificacao';

const { NOTIFICACAO, ACAO, marcarLida, CICLO } = vi.hoisted(() => ({
  NOTIFICACAO: {
    id: 1,
    acao_instancia: 10,
    acao_ordem: 1,
    acao_nome: 'Enviar kit',
    titulo: '[D0] Ação 01 - Enviar kit',
    mensagem: 'Mensagem da notificação',
    tipo: 'VENCIMENTO',
    nivel: 'RESPONSAVEL',
    prioridade: 'CRITICA',
    fase_disparo: 'D0',
    referencia_data: '2026-03-10',
    lida: false,
    lida_em: null,
    created_at: '2026-03-10T12:00:00Z',
  } satisfies NotificacaoInterna,
  ACAO: {
    id: 11,
    ciclo: 7,
    ordem: 1,
    estado: 'AGUARDANDO_ANCORA',
    template: 3,
    template_nome: 'Enviar kit',
    projeto_nome: 'Vidas',
    municipio_nome: 'Fortaleza',
    data_ancora: null,
    data_vencimento: '2026-03-10',
    data_realizacao: '2026-03-12',
    observacao_conclusao: '',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  } satisfies AcaoInstancia,
  marcarLida: vi.fn().mockResolvedValue({}),
  CICLO: {
    id: 7, projeto: 1, municipio: 2, projeto_nome: 'Vidas', municipio_nome: 'Fortaleza', semestre: '1S', ano: 2026,
    status: 'EM_ANDAMENTO', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
  },
}));

vi.mock('../../../api/acoesNotificacao', () => ({
  listNotificacoesInternas: vi.fn(() => Promise.resolve({ count: 1, next: null, previous: null, results: [NOTIFICACAO] })),
  marcarNotificacaoLida: marcarLida,
  marcarTodasNotificacoesLidas: vi.fn(),
  listCiclosAcoes: vi.fn(() => Promise.resolve({ count: 1, next: null, previous: null, results: [CICLO] })),
  listAcoesByCiclo: vi.fn(() => Promise.resolve([ACAO])),
  registrarAncora: vi.fn(),
  concluirAcao: vi.fn(),
}));

import NotificacoesInternasPage from '../NotificacoesInternasPage';
import AcoesNotificacaoPage from '../AcoesNotificacaoPage';

vi.setConfig({ testTimeout: 30_000 });

const ACAO_NOME = '1. Enviar kit';

function cabecalhos(): string[] {
  return screen
    .getAllByRole('columnheader')
    .filter((th) => !th.classList.contains('ant-table-row-expand-icon-cell'))
    .map((th) => th.textContent?.trim() ?? '')
    .filter(Boolean);
}

async function linhaPelaAcao(nome: string): Promise<HTMLElement> {
  const botao = await screen.findByRole('button', { name: nome }, { timeout: 15000 });
  const linha = botao.closest('tr');
  if (!linha) throw new Error('o botão não está numa linha da tabela');
  return linha;
}

function semLarguraForcada(container: HTMLElement): void {
  expect(container.querySelector('.ant-table-cell-fix-right, .ant-table-cell-fix-left')).toBeNull();
  expect(container.querySelector('.ant-table-content')?.getAttribute('style') ?? '').not.toMatch(/overflow/);
  expect(container.querySelector('table')?.style.width ?? '').toBe('');
}

function expandida(): ReturnType<typeof within> {
  return within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
}

describe('Notificações Internas sem rolagem horizontal (G30)', { timeout: 20000 }, () => {
  test('a 1280 px: colunas por prioridade e "Marcar lida" pelo título; a mensagem na linha expandida', async () => {
    const { container } = render(<NotificacoesInternasPage />);
    const linha = await linhaPelaAcao(`Marcar lida: ${NOTIFICACAO.titulo}`);

    expect(cabecalhos()).toEqual(['Status', 'Título', 'Fase', 'Prioridade', 'Referência', 'Ações']);
    semLarguraForcada(container);
    fireEvent.click(within(linha).getByRole('button', { name: `Expandir linha de ${NOTIFICACAO.titulo}` }));
    expect(expandida().getByText('Mensagem da notificação')).toBeInTheDocument();
    expect(expandida().getByText('Vencimento')).toBeInTheDocument();
  });

  test('a 360 px: status, título e o menu de ações; "Marcar lida" está no menu e marca', async () => {
    definirLarguraTela(360);
    render(<NotificacoesInternasPage />);
    const linha = await linhaPelaAcao(`Mais ações: ${NOTIFICACAO.titulo}`);

    expect(cabecalhos()).toEqual(['Status', 'Título', 'Ações']);
    fireEvent.click(within(linha).getByRole('button', { name: `Mais ações: ${NOTIFICACAO.titulo}` }));
    fireEvent.click(await screen.findByRole('menuitem', { name: 'Marcar lida' }));
    await waitFor(() => expect(marcarLida).toHaveBeenCalledWith(1));
  });

  test('notificação já lida não oferece "Marcar lida"', async () => {
    const { listNotificacoesInternas } = await import('../../../api/acoesNotificacao');
    vi.mocked(listNotificacoesInternas).mockResolvedValueOnce({
      count: 1, next: null, previous: null, results: [{ ...NOTIFICACAO, lida: true }],
    });
    render(<NotificacoesInternasPage />);
    await screen.findByText('Lida', {}, { timeout: 15000 });

    expect(screen.queryByRole('button', { name: /^Marcar lida:/ })).not.toBeInTheDocument();
  });
});

describe('Ações Internas sem rolagem horizontal (G30)', { timeout: 20000 }, () => {
  test('a 1280 px: todas as colunas, sem largura forçada; Registrar âncora e Concluir pelo nome da ação', async () => {
    const { container } = render(<AcoesNotificacaoPage />);
    const linha = await linhaPelaAcao(`Concluir: ${ACAO_NOME}`);

    expect(cabecalhos()).toEqual(['Ordem', 'Ação', 'Estado', 'Âncora', 'Vencimento', 'Realização', 'Ações']);
    expect(within(linha).getByRole('button', { name: `Registrar âncora: ${ACAO_NOME}` })).toBeInTheDocument();
    semLarguraForcada(container);

    fireEvent.click(within(linha).getByRole('button', { name: `Concluir: ${ACAO_NOME}` }));
    expect(await screen.findByText('Concluir ação')).toBeInTheDocument();
  });

  test('a 360 px: a ação com o estado e o menu; datas na linha expandida', async () => {
    definirLarguraTela(360);
    render(<AcoesNotificacaoPage />);
    const linha = await linhaPelaAcao(`Mais ações: ${ACAO_NOME}`);

    expect(cabecalhos()).toEqual(['Ação', 'Ações']);
    expect(within(linha).getByText('Aguardando âncora')).toBeInTheDocument();
    fireEvent.click(within(linha).getByRole('button', { name: `Expandir linha de ${ACAO_NOME}` }));
    for (const texto of ['Vencimento', '10/03/2026', 'Realização', '12/03/2026']) {
      expect(expandida().getByText(texto)).toBeInTheDocument();
    }
  });

  test('ação concluída não oferece "Concluir"', async () => {
    const { listAcoesByCiclo } = await import('../../../api/acoesNotificacao');
    vi.mocked(listAcoesByCiclo).mockResolvedValueOnce([{ ...ACAO, estado: 'CONCLUIDA' }]);
    render(<AcoesNotificacaoPage />);
    await linhaPelaAcao(`Registrar âncora: ${ACAO_NOME}`);

    expect(screen.queryByRole('button', { name: `Concluir: ${ACAO_NOME}` })).not.toBeInTheDocument();
  });

  test('mudar a largura reorganiza as colunas', async () => {
    render(<AcoesNotificacaoPage />);
    await linhaPelaAcao(`Concluir: ${ACAO_NOME}`);

    act(() => definirLarguraTela(768));
    expect(cabecalhos()).toEqual(['Ordem', 'Ação', 'Estado', 'Vencimento', 'Ações']);
  });
});
