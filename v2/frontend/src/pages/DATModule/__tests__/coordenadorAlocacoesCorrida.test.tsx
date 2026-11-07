/**
 * Lote D (ART-D1b): corrida no modal de Alocações. `loadAlocacoes` gravava a resposta que
 * chegasse por último: abrir o coordenador A, fechar e abrir o B, e a resposta atrasada de A
 * (chegando depois da de B) sobrescrevia a lista do modal de B com as ações de A.
 * A guarda: só a resposta do pedido mais recente grava a lista e o "carregando".
 */
import { describe, expect, test, vi } from 'vitest';
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';

const { rowA, rowB } = vi.hoisted(() => ({
  rowA: {
    id: 11, nome: 'Ana', email: '', telefone: '', area: 'DAT', cargo: '',
    data_admissao: null, ativo: true, foto_url: null, total_municipios: 1, total_projetos: 1,
  },
  rowB: {
    id: 22, nome: 'Bruno', email: '', telefone: '', area: 'DAT', cargo: '',
    data_admissao: null, ativo: true, foto_url: null, total_municipios: 1, total_projetos: 1,
  },
}));

vi.mock('../../../api/datModule', () => ({
  listCoordenadoresDAT: vi.fn().mockResolvedValue({ results: [rowA, rowB], count: 2, next: null, previous: null }),
  getCoordenadorDAT: vi.fn(),
  createCoordenadorDAT: vi.fn(),
  updateCoordenadorDAT: vi.fn(),
  deleteCoordenadorDAT: vi.fn(),
  getCoordenadorAlocacoes: vi.fn(),
  getAreasOptions: vi.fn().mockResolvedValue([]),
  getProjetosOptions: vi.fn().mockResolvedValue([]),
  getMunicipiosOptions: vi.fn().mockResolvedValue([]),
}));

import CoordenadoresPage from '../CoordenadoresPage';
import { getCoordenadorAlocacoes } from '../../../api/datModule';

type Alocacao = { id: number; projeto_nome: string; municipio_nome: string };

function adiado(): { promessa: Promise<Alocacao[]>; resolver: (v: Alocacao[]) => void } {
  let resolver!: (v: Alocacao[]) => void;
  const promessa = new Promise<Alocacao[]>((r) => {
    resolver = r;
  });
  return { promessa, resolver };
}

describe('Modal de Alocações: a resposta atrasada de outro coordenador não sobrescreve a lista', { timeout: 90000 }, () => {
  test('abre A, fecha, abre B; B responde e depois A: o modal de B não mostra as ações de A', async () => {
    const pedidoA = adiado();
    const pedidoB = adiado();
    vi.mocked(getCoordenadorAlocacoes).mockImplementation((id) =>
      Number(id) === 11 ? pedidoA.promessa : pedidoB.promessa,
    );
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <CoordenadoresPage />
      </MemoryRouter>,
    );
    await user.click(await screen.findByLabelText('Visualizar como lista', {}, { timeout: 15000 }));

    await user.click(await screen.findByRole('button', { name: 'Ver detalhes: Ana' }, { timeout: 15000 }));
    await user.click(await screen.findByRole('button', { name: 'Fechar' }));
    await user.click(screen.getByRole('button', { name: 'Ver detalhes: Bruno' }));

    await act(async () => {
      pedidoB.resolver([{ id: 2, projeto_nome: 'Projeto do Bruno', municipio_nome: 'Sobral' }]);
    });
    const modal = within(screen.getByRole('dialog'));
    expect(await modal.findByText('Projeto do Bruno')).toBeInTheDocument();

    await act(async () => {
      pedidoA.resolver([{ id: 1, projeto_nome: 'Projeto da Ana', municipio_nome: 'Fortaleza' }]);
    });

    expect(modal.getByText('Bruno')).toBeInTheDocument();
    expect(modal.getByText('Projeto do Bruno')).toBeInTheDocument();
    expect(modal.queryByText('Projeto da Ana')).toBeNull();
  });
});
