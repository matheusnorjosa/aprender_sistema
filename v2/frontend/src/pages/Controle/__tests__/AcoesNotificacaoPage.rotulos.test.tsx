/**
 * B#36/B#37 (alinhamento das telas): /acoes-notificacao mostra o estado da ação em português,
 * datas DD/MM/AAAA e busca o ciclo no servidor (projeto e município), não só nos 100 primeiros.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

import type { AcaoInstancia, CicloAcoes } from '../../../types/acoesNotificacao';
import { listCiclosAcoes } from '../../../api/acoesNotificacao';

const ciclo: CicloAcoes = {
  id: 7,
  projeto: 1,
  municipio: 2,
  projeto_nome: 'Vidas',
  municipio_nome: 'Fortaleza',
  semestre: '1S',
  ano: 2026,
  status: 'EM_ANDAMENTO',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const acao: AcaoInstancia = {
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
  data_realizacao: null,
  observacao_conclusao: '',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

vi.mock('../../../api/acoesNotificacao', () => ({
  listCiclosAcoes: vi.fn(() => Promise.resolve({ count: 1, next: null, previous: null, results: [ciclo] })),
  listAcoesByCiclo: vi.fn(() => Promise.resolve([acao])),
  registrarAncora: vi.fn(),
  concluirAcao: vi.fn(),
}));

import AcoesNotificacaoPage from '../AcoesNotificacaoPage';

describe('AcoesNotificacaoPage — rótulos e busca de ciclo', { timeout: 20000 }, () => {
  it('mostra o estado em português e a data DD/MM/AAAA (B#36)', async () => {
    render(<AcoesNotificacaoPage />);
    expect(await screen.findByText('Aguardando âncora')).toBeInTheDocument();
    expect(screen.getByText('10/03/2026')).toBeInTheDocument();
    expect(screen.queryByText('AGUARDANDO_ANCORA')).not.toBeInTheDocument();
    expect(screen.queryByText('2026-03-10')).not.toBeInTheDocument();
  });

  it('digitar no seletor busca o ciclo no servidor (B#37)', async () => {
    render(<AcoesNotificacaoPage />);
    await screen.findByText('Aguardando âncora');
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'Caucaia' } });
    await waitFor(() =>
      expect(vi.mocked(listCiclosAcoes)).toHaveBeenCalledWith(expect.objectContaining({ search: 'Caucaia' })),
    );
  });
});
