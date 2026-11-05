/**
 * Municípios: as 27 UFs e o vazio que não manda importar quem não pode.
 *
 * - P#47: o filtro e o cadastro só tinham as 9 UFs do Nordeste; há municípios em operação fora
 *   dele (MG, PR). O servidor aceita qualquer UF, então a tela também.
 * - A#50/B#53: a lista vazia mandava "importe uma planilha abaixo", mas só o superusuário vê a
 *   importação.
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

vi.mock('../../../api/auth', () => ({ checkAuth: vi.fn() }));
vi.mock('../../../api/ops', () => ({ importMunicipios: vi.fn() }));
vi.mock('../../../api/adminDAT', () => ({
  listMunicipios: vi.fn(),
  createMunicipio: vi.fn(),
  updateMunicipio: vi.fn(),
  deleteMunicipio: vi.fn(),
  autocompleteMunicipiosAdmin: vi.fn().mockResolvedValue([]),
}));

import { checkAuth } from '../../../api/auth';
import { listMunicipios } from '../../../api/adminDAT';
import MunicipiosPage from '../MunicipiosPage';

function renderPage() {
  return render(
    <ConfigProvider locale={ptBR}>
      <MemoryRouter>
        <MunicipiosPage />
      </MemoryRouter>
    </ConfigProvider>,
  );
}

/**
 * UFs que o seletor oferece. A lista do dropdown é virtual (só desenha as que cabem): rola até o
 * fim e junta as que apareceram no caminho.
 */
async function ufsDoSeletor(combobox: HTMLElement): Promise<string[]> {
  fireEvent.mouseDown(combobox);
  const listbox = await screen.findByRole('listbox', {}, { timeout: 10000 });
  const dropdown = listbox.closest<HTMLElement>('.ant-select-dropdown')!;
  const holder = dropdown.querySelector<HTMLElement>('.rc-virtual-list-holder')!;
  const vistas = new Set<string>();
  for (let topo = 0; topo <= 27 * 32; topo += 96) {
    holder.scrollTop = topo;
    fireEvent.scroll(holder, { target: { scrollTop: topo } });
    dropdown.querySelectorAll('.ant-select-item-option').forEach((o) => vistas.add(o.getAttribute('title') ?? ''));
  }
  return [...vistas];
}

describe('MunicipiosPage: UFs e textos', { timeout: 20000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(checkAuth).mockResolvedValue({ authenticated: true, user: { is_superuser: false } } as never);
    vi.mocked(listMunicipios).mockResolvedValue({ results: [], count: 0, next: null, previous: null });
  });

  test('filtro por UF oferece UFs fora do Nordeste (MG, PR, SC)', async () => {
    renderPage();
    const ufs = await ufsDoSeletor(await screen.findByRole('combobox', { name: 'Filtrar por UF' }));

    expect(ufs).toEqual(expect.arrayContaining(['MG', 'PR', 'SC']));
    expect(ufs).toHaveLength(27);
  });

  test('cadastro aceita UF fora do Nordeste (MG, PR, SC)', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: /Novo Município/ }));
    const modal = (await screen.findByText('Novo Município', { selector: '.ant-modal-title' })).closest<HTMLElement>(
      '[role="dialog"]',
    )!;
    const ufs = await ufsDoSeletor(within(modal).getByRole('combobox', { name: 'UF' }));

    expect(ufs).toEqual(expect.arrayContaining(['MG', 'PR', 'SC']));
    expect(ufs).toHaveLength(27);
  });

  test('lista vazia para quem não importa: não manda importar planilha', async () => {
    renderPage();
    expect(await screen.findByText(/Nenhum município cadastrado/)).toHaveTextContent(
      'Nenhum município cadastrado. Use "Novo Município".',
    );
    expect(screen.queryByText(/importe uma planilha/)).not.toBeInTheDocument();
  });

  test('lista vazia para o superusuário: aponta a importação', async () => {
    vi.mocked(checkAuth).mockResolvedValue({ authenticated: true, user: { is_superuser: true } } as never);
    renderPage();
    await screen.findByText('Importação de Municípios');

    await waitFor(() =>
      expect(screen.getByText(/Nenhum município cadastrado/)).toHaveTextContent(
        'Nenhum município cadastrado. Use "Novo Município" ou importe uma planilha abaixo.',
      ),
    );
  });
});
