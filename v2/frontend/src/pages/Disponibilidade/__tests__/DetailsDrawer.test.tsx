/**
 * Detalhe da célula da Grade Mensal (ensaio r3, 28/10/2026): a data do evento aparece como
 * dd/mm/aaaa, como no resto do sistema, e não no formato do servidor (2026-12-07). O servidor já
 * manda o dia de Fortaleza; a tela só troca o formato, sem converter fuso.
 */
import { render, screen } from '@testing-library/react';
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

    expect(screen.getByRole('cell', { name: '07/12/2026' })).toBeInTheDocument();
    expect(screen.queryByText('2026-12-07')).not.toBeInTheDocument();
  });
});
