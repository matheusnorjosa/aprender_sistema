import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import DatImportsCentralizedBanner, {
  DAT_IMPORTS_CENTRALIZED_MESSAGE,
} from '../DatImportsCentralizedBanner';
import { getMe } from '../../api/availability';
import type { CurrentUser } from '../../types';

vi.mock('../../api/availability', () => ({
  getMe: vi.fn(),
}));

const baseUser: CurrentUser = {
  id: 1,
  username: 'user',
  email: 'user@example.com',
  first_name: 'User',
  last_name: 'Test',
  name: 'User Test',
  groups: [],
  setores: [],
  funcoes: [],
  is_superuser: false,
  is_superintendencia: false,
  can_approve_super: false,
  permissions: [],
};

describe('DatImportsCentralizedBanner', () => {
  beforeEach(() => {
    vi.mocked(getMe).mockReset();
  });

  test('exibe link para DAT > Importações quando usuário pode acessar DAT', async () => {
    vi.mocked(getMe).mockResolvedValue({
      ...baseUser,
      setores: ['DAT'],
    });

    render(
      <MemoryRouter>
        <DatImportsCentralizedBanner />
      </MemoryRouter>,
    );

    const link = await screen.findByRole('link', { name: 'DAT > Importações' });
    expect(link).toHaveAttribute('href', '/dat/importacoes');
  });

  test('exibe apenas texto informativo para usuário sem acesso ao DAT', async () => {
    vi.mocked(getMe).mockResolvedValue({
      ...baseUser,
      setores: ['Controle'],
    });

    render(
      <MemoryRouter>
        <DatImportsCentralizedBanner />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByLabelText(DAT_IMPORTS_CENTRALIZED_MESSAGE)).toBeInTheDocument();
    });

    expect(screen.queryByRole('link', { name: 'DAT > Importações' })).not.toBeInTheDocument();
    expect(screen.getByText(DAT_IMPORTS_CENTRALIZED_MESSAGE)).toBeInTheDocument();
  });

  test('não expõe link quando /api/me falha', async () => {
    vi.mocked(getMe).mockRejectedValue(new Error('unauthorized'));

    render(
      <MemoryRouter>
        <DatImportsCentralizedBanner />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(DAT_IMPORTS_CENTRALIZED_MESSAGE)).toBeInTheDocument();
    });

    expect(screen.queryByRole('link', { name: 'DAT > Importações' })).not.toBeInTheDocument();
  });
});
