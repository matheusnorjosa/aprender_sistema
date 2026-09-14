/**
 * M18-05 / #1654: editar coordenador alimentava o form com a LINHA DA LISTA. O list serializer
 * (DATCoordenadorListSerializer) NÃO expõe `observacoes`/`email_alternativo`/`telefone_alternativo`,
 * e o `handleEdit` fazia `setFieldsValue({...record})` sem GET de detalhe e sem `resetFields()`.
 * Como `setFieldsValue` é aditivo, esses 3 campos vazavam do registro anterior e o PATCH os
 * sobrescrevia. Fix: `handleEdit` faz `resetFields()` + `getCoordenadorDAT(id)` antes de abrir o
 * modal — espelha AcoesPage/CadastrosPage (M17-02, editFetchesDetail) e ComprasPage (#1636).
 *
 * RED no código antigo: `getCoordenadorDAT` não existe e o handleEdit usa a linha da lista.
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';

const { rowA, rowB } = vi.hoisted(() => ({
  // Linhas da LISTA — fiéis ao list serializer: SEM observacoes/email_alternativo/telefone_alternativo.
  rowA: {
    id: 11, nome: 'Ana', email: 'a@x.com', telefone: '', area: 'DAT', cargo: '',
    data_admissao: '2026-01-10', ativo: true, foto_url: null, total_municipios: 1, total_projetos: 2,
  },
  rowB: {
    id: 22, nome: 'Bruno', email: 'b@x.com', telefone: '', area: 'DAT', cargo: '',
    data_admissao: '2026-02-20', ativo: true, foto_url: null, total_municipios: 0, total_projetos: 0,
  },
}));

vi.mock('../../../api/datModule', () => ({
  listCoordenadoresDAT: vi.fn().mockResolvedValue({ results: [rowA, rowB], count: 2, next: null, previous: null }),
  getCoordenadorDAT: vi.fn((id: number) =>
    Promise.resolve(
      id === 11
        ? { ...rowA, observacoes: 'OBS_DETALHE_A', email_alternativo: 'alt-a@x.com', telefone_alternativo: '' }
        : { ...rowB, observacoes: '', email_alternativo: '', telefone_alternativo: '' },
    ),
  ),
  createCoordenadorDAT: vi.fn(),
  updateCoordenadorDAT: vi.fn().mockResolvedValue({}),
  deleteCoordenadorDAT: vi.fn(),
  getCoordenadorAlocacoes: vi.fn().mockResolvedValue([]),
  getAreasOptions: vi.fn().mockResolvedValue([]),
  getProjetosOptions: vi.fn().mockResolvedValue([]),
  getMunicipiosOptions: vi.fn().mockResolvedValue([]),
}));

import CoordenadoresPage from '../CoordenadoresPage';
import { getCoordenadorDAT } from '../../../api/datModule';

// A view padrão é CARDS (ícones sem aria-label estável); a tabela expõe "Editar coordenador".
async function switchToTable(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  const tableBtn = await screen.findByLabelText('Visualizar como lista', {}, { timeout: 15000 });
  await user.click(tableBtn);
}

describe('M18-05 (#1654): editar coordenador busca o DETAIL (não a linha da lista)', () => {
  beforeEach(() => vi.clearAllMocks());

  // Timeouts folgados: render da página inteira (Table + useTableFilters + stats) em jsdom
  // sob carga do CI passa dos 5s default. O comportamento testado é rápido; o render é lento.
  test(
    'clicar em Editar dispara getCoordenadorDAT(id) e carrega Observações do detail',
    async () => {
      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <CoordenadoresPage />
        </MemoryRouter>,
      );
      await switchToTable(user);
      const editBtns = await screen.findAllByLabelText('Editar coordenador', {}, { timeout: 15000 });
      await user.click(editBtns[0]); // Ana (id 11)
      await waitFor(() => expect(getCoordenadorDAT).toHaveBeenCalledWith(11), { timeout: 10000 });
      const obs = await screen.findByLabelText('Observações', {}, { timeout: 10000 });
      await waitFor(() => expect(obs).toHaveValue('OBS_DETALHE_A'), { timeout: 10000 });
    },
    30000,
  );

  test(
    'Observações não vaza entre registros: digitar em A, cancelar, editar B mostra vazio',
    async () => {
      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <CoordenadoresPage />
        </MemoryRouter>,
      );
      await switchToTable(user);
      const editBtns = await screen.findAllByLabelText('Editar coordenador', {}, { timeout: 15000 });
      await user.click(editBtns[0]); // A
      const obs = await screen.findByLabelText('Observações', {}, { timeout: 10000 });
      await waitFor(() => expect(obs).toHaveValue('OBS_DETALHE_A'), { timeout: 10000 });
      // delay:null digita de uma vez (sem re-render por char) — evita timeout no CI.
      await user.clear(obs);
      await user.type(obs, 'SENTINELA_A', { delay: null });
      expect(obs).toHaveValue('SENTINELA_A');

      // cancela — o onCancel só esconde o modal
      await user.click(screen.getByRole('button', { name: /cancelar/i }));

      // reabre a edição, agora em B (detail de B tem observacoes vazia)
      const editBtns2 = await screen.findAllByLabelText('Editar coordenador', {}, { timeout: 10000 });
      await user.click(editBtns2[1]); // B
      const obsB = await screen.findByLabelText('Observações', {}, { timeout: 10000 });
      await waitFor(() => expect(obsB).toHaveValue(''), { timeout: 10000 }); // RED sem resetFields (retém SENTINELA_A)
    },
    45000,
  );
});
