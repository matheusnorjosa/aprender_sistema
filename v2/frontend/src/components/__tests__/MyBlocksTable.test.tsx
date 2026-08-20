import { render, screen } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

import MyBlocksTable, { type BlockRecord } from '../MyBlocksTable';

function makeBlock(overrides: Partial<BlockRecord> = {}): BlockRecord {
  return {
    id: 1,
    inicio: '2026-09-15T12:00:00Z',
    fim: '2026-09-15T18:00:00Z',
    tipo: 'T',
    status: 'aprovado',
    ...overrides,
  };
}

describe('MyBlocksTable', () => {
  // RD-06 (#1719): início/fim do bloqueio exibidos fixando America/Fortaleza,
  // independente do fuso do navegador. 12:00Z/18:00Z → 09:00/15:00 (UTC-3).
  test('exibe início e fim do bloqueio em America/Fortaleza, não em UTC', () => {
    render(<MyBlocksTable blocks={[makeBlock()]} onDelete={vi.fn()} loading={false} />);

    // horários no fuso de Fortaleza...
    expect(screen.getByText('15/09/2026 09:00')).toBeInTheDocument();
    expect(screen.getByText('15/09/2026 15:00')).toBeInTheDocument();
    // ...e nunca os horários UTC crus (regressão RD-06)
    expect(screen.queryByText('15/09/2026 12:00')).not.toBeInTheDocument();
    expect(screen.queryByText('15/09/2026 18:00')).not.toBeInTheDocument();
  });
});
