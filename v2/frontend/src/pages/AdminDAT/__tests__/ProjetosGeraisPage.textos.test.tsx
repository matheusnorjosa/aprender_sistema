/**
 * Coleções (B#51): o formulário de Coleção fala de coleção ("Coleção ativa"), não de projeto.
 */
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

vi.mock('../../../api/adminDAT', () => ({
  listProjetosGerais: vi.fn(),
  createProjetoGeral: vi.fn(),
  updateProjetoGeral: vi.fn(),
  deleteProjetoGeral: vi.fn(),
}));

import { listProjetosGerais } from '../../../api/adminDAT';
import ProjetosGeraisPage from '../ProjetosGeraisPage';

describe('ProjetosGeraisPage: textos do formulário', { timeout: 20000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listProjetosGerais).mockResolvedValue({ results: [], count: 0, next: null, previous: null });
  });

  test('o check de situação diz "Coleção ativa"', async () => {
    const user = userEvent.setup();
    render(
      <ConfigProvider locale={ptBR}>
        <MemoryRouter>
          <ProjetosGeraisPage />
        </MemoryRouter>
      </ConfigProvider>,
    );
    await user.click(await screen.findByRole('button', { name: /Nova Coleção/ }));
    const modal = (await screen.findByText('Nova Coleção', { selector: '.ant-modal-title' })).closest<HTMLElement>(
      '[role="dialog"]',
    )!;

    expect(within(modal).getByRole('checkbox', { name: 'Coleção ativa' })).toBeChecked();
    expect(within(modal).queryByText('Projeto ativo')).not.toBeInTheDocument();
  });
});
