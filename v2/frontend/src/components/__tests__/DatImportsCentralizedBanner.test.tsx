import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
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
  gerencias: [],
  is_superuser: false,
  is_superintendencia: false,
  can_approve_super: false,
  permissions: [],
};

describe('DatImportsCentralizedBanner', () => {
  beforeEach(() => {
    vi.mocked(getMe).mockReset();
  });

  test('exibe link para DAT > Importações para o superusuário', async () => {
    vi.mocked(getMe).mockResolvedValue({
      ...baseUser,
      is_superuser: true,
    });

    render(
      <MemoryRouter>
        <DatImportsCentralizedBanner />
      </MemoryRouter>,
    );

    const link = await screen.findByRole('link', { name: 'DAT > Importações' });
    expect(link).toHaveAttribute('href', '/dat/importacoes');
    expect(screen.getByLabelText(DAT_IMPORTS_CENTRALIZED_MESSAGE)).toBeInTheDocument();
  });

  // Quem não é superusuário não tem a tela DAT > Importações (02/10/2026): o aviso apontaria
  // para um lugar que a pessoa não alcança, então não aparece.
  test.each([
    ['DAT', { ...baseUser, setores: ['DAT'] }],
    ['Controle', { ...baseUser, setores: ['Controle'] }],
  ])('%s não é superusuário: o aviso não aparece', async (_perfil, usuario) => {
    vi.mocked(getMe).mockResolvedValue(usuario);

    const { container } = render(
      <MemoryRouter>
        <DatImportsCentralizedBanner />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(getMe).toHaveBeenCalled();
    });
    expect(screen.queryByText(DAT_IMPORTS_CENTRALIZED_MESSAGE)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(DAT_IMPORTS_CENTRALIZED_MESSAGE)).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'DAT > Importações' })).not.toBeInTheDocument();
    expect(container).toBeEmptyDOMElement();
  });

  test('o aviso não aparece quando /api/me falha', async () => {
    vi.mocked(getMe).mockRejectedValue(new Error('unauthorized'));

    const { container } = render(
      <MemoryRouter>
        <DatImportsCentralizedBanner />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(getMe).toHaveBeenCalled();
    });
    expect(screen.queryByRole('link', { name: 'DAT > Importações' })).not.toBeInTheDocument();
    expect(container).toBeEmptyDOMElement();
  });
});
