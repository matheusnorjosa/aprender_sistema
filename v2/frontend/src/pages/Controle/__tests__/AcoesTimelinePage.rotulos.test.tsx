/**
 * B#36/B#37 (alinhamento das telas): a linha do tempo das ações mostra o estado em português,
 * datas DD/MM/AAAA e busca o ciclo no servidor (projeto e município).
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
  estado: 'EM_ANDAMENTO',
  template: 3,
  template_nome: 'Enviar kit',
  projeto_nome: 'Vidas',
  municipio_nome: 'Fortaleza',
  data_ancora: '2026-03-02',
  data_vencimento: '2026-03-10',
  data_realizacao: null,
  observacao_conclusao: '',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

vi.mock('../../../api/acoesNotificacao', () => ({
  listCiclosAcoes: vi.fn(() => Promise.resolve({ count: 1, next: null, previous: null, results: [ciclo] })),
  listAcoesByCiclo: vi.fn(() => Promise.resolve([acao])),
}));

import AcoesTimelinePage from '../AcoesTimelinePage';

describe('AcoesTimelinePage — rótulos e busca de ciclo', { timeout: 20000 }, () => {
  it('mostra o estado em português e datas DD/MM/AAAA (B#36)', async () => {
    render(<AcoesTimelinePage />);
    expect(await screen.findByText('Estado: Em andamento')).toBeInTheDocument();
    expect(screen.getByText('Âncora: 02/03/2026')).toBeInTheDocument();
    expect(screen.getByText('Vencimento: 10/03/2026')).toBeInTheDocument();
  });

  it('digitar no seletor busca o ciclo no servidor (B#37)', async () => {
    render(<AcoesTimelinePage />);
    await screen.findByText('Estado: Em andamento');
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'Caucaia' } });
    await waitFor(() =>
      expect(vi.mocked(listCiclosAcoes)).toHaveBeenCalledWith(expect.objectContaining({ search: 'Caucaia' })),
    );
  });
});
