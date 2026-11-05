/**
 * Detalhe da célula da Grade Mensal (ensaio r3, 28/10/2026): a data do evento aparece como
 * dd/mm/aaaa, como no resto do sistema, e não no formato do servidor (2026-12-07). O servidor já
 * manda o dia de Fortaleza; a tela só troca o formato, sem converter fuso.
 */
import { render, screen, within } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

import DetailsDrawer from '../DetailsDrawer';

describe('DetailsDrawer', () => {
  test('mostra a data do evento como dd/mm/aaaa', () => {
    render(
      <DetailsDrawer
        open
        onClose={vi.fn()}
        person={{ id: 1, name: 'Maria' }}
        day={7}
        details={[{ id: 9, municipio: 'Crato', tipo: 'Formação', data: '2026-12-07', inicio: '08:00', fim: '12:00' }]}
      />,
    );

    expect(screen.getByText('07/12/2026')).toBeInTheDocument();
    expect(screen.queryByText('2026-12-07')).not.toBeInTheDocument();
  });

  // C4 (sem rolagem horizontal): a tabela de 5 colunas rolava dentro do painel no celular.
  test('cada evento é um cartão da lista, sem tabela nem rolagem interna', () => {
    const { container } = render(
      <DetailsDrawer
        open
        onClose={vi.fn()}
        person={{ id: 1, name: 'Maria', email: 'maria.aparecida.da.conceicao@exemplo.invalid' }}
        day={7}
        details={[
          { id: 9, municipio: 'Crato', tipo: 'Formação', data: '2026-12-07', inicio: '08:00', fim: '12:00' },
          { id: 10, municipio: 'Juazeiro do Norte', tipo: 'Acompanhamento', data: '2026-12-07', inicio: '13:00', fim: '17:00' },
        ]}
      />,
    );

    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(container.querySelector('.overflow-x-auto')).toBeNull();
    const eventos = screen.getAllByRole('listitem');
    expect(eventos).toHaveLength(2);
    expect(within(eventos[1] as HTMLElement).getByText('Juazeiro do Norte')).toBeInTheDocument();
    expect(within(eventos[1] as HTMLElement).getByText('Acompanhamento')).toBeInTheDocument();
    expect(within(eventos[1] as HTMLElement).getByText('13:00')).toBeInTheDocument();
    for (const rotulo of ['Tipo', 'Data', 'Início', 'Fim']) {
      expect(within(eventos[0] as HTMLElement).getByText(rotulo)).toBeInTheDocument();
    }
  });
});
