/**
 * B#2 (alinhamento das telas): /notificacoes-internas mostra rótulos em português no lugar dos
 * valores crus de fase, tipo e prioridade, e não abre um segundo <main> dentro do main do App.
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

import type { NotificacaoInterna } from '../../../types/acoesNotificacao';

const notificacao: NotificacaoInterna = {
  id: 1,
  acao_instancia: 10,
  acao_ordem: 1,
  acao_nome: 'Enviar kit',
  titulo: '[D0] Ação 01 - Enviar kit',
  mensagem: 'Mensagem',
  tipo: 'VENCIMENTO',
  nivel: 'RESPONSAVEL',
  prioridade: 'CRITICA',
  fase_disparo: 'D0',
  referencia_data: '2026-03-10',
  lida: false,
  lida_em: null,
  created_at: '2026-03-10T12:00:00Z',
};

vi.mock('../../../api/acoesNotificacao', () => ({
  listNotificacoesInternas: vi.fn(() =>
    Promise.resolve({ count: 1, next: null, previous: null, results: [notificacao] }),
  ),
  marcarNotificacaoLida: vi.fn(),
  marcarTodasNotificacoesLidas: vi.fn(),
}));

import NotificacoesInternasPage from '../NotificacoesInternasPage';

describe('NotificacoesInternasPage — rótulos em português (B#2)', { timeout: 20000 }, () => {
  it('mostra fase, tipo, prioridade e data de referência legíveis', async () => {
    render(<NotificacoesInternasPage />);
    expect(await screen.findByText('Crítica')).toBeInTheDocument();
    // G30: o Tipo só entra na linha a partir de 1600 px; até lá, na linha expandida.
    fireEvent.click(screen.getByRole('button', { name: /^Expandir linha de / }));
    expect(screen.getByText('Vencimento')).toBeInTheDocument();
    expect(screen.getByText('No vencimento')).toBeInTheDocument();
    expect(screen.getByText('10/03/2026')).toBeInTheDocument();
    expect(screen.queryByText('CRITICA')).not.toBeInTheDocument();
    expect(screen.queryByText('VENCIMENTO')).not.toBeInTheDocument();
  });

  it('subtítulo sem "Inbox in-app" e seção nomeada no lugar de um segundo <main>', async () => {
    const { container } = render(<NotificacoesInternasPage />);
    expect(await screen.findByText('Lembretes e escalonamentos das ações.')).toBeInTheDocument();
    expect(screen.queryByText(/Inbox in-app/)).not.toBeInTheDocument();
    expect(container.querySelector('main')).toBeNull();
    expect(screen.getByRole('region', { name: 'Notificações Internas' })).toBeInTheDocument();
  });
});
