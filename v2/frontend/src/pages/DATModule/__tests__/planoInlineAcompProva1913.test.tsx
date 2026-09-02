/**
 * #1913: as células de Acompanhamento e Prova do PlanoFormacoes não tinham onClick — a
 * edição inline (backend pronto: updateAcompanhamentoInline/updateProvaInline) estava morta,
 * embora a célula de Formação já fosse clicável. Este teste clica na célula, exige o modal
 * de edição inline e o PATCH correspondente.
 *
 * RED no código antigo (células inertes, sem controle de edição acessível).
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';

vi.mock('../../../api/datModule', () => ({
  listPlanoFormacoes: vi.fn().mockResolvedValue({
    results: [
      {
        id: 7, municipio: 1, municipio_nome: 'Fortaleza', municipio_uf: 'CE',
        projeto: 1, projeto_nome: 'Projeto Teste', ano: 2026,
        coordenador: null, coordenador_nome: null,
        ch_estudo: 10, ch_anual: 20, observacoes: null,
        formacoes_list: [],
        acompanhamentos_list: [{ id: 11, tipo: 'primeiro', data: '2026-03-10', realizado: false }],
        provas_list: [{ id: 21, numero: 1, data: '2026-04-10', realizada: false }],
      },
    ],
    count: 1, next: null, previous: null,
  }),
  createPlanoFormacoes: vi.fn().mockResolvedValue({}),
  updatePlanoFormacoes: vi.fn().mockResolvedValue({}),
  deletePlanoFormacoes: vi.fn().mockResolvedValue({}),
  getPlanoFormacoesStats: vi.fn().mockResolvedValue({ total_planos: 1, total_formacoes: 0, total_realizadas: 0, taxa_realizacao: 0, ch_total: 20 }),
  updateFormacaoInline: vi.fn().mockResolvedValue({}),
  updateAcompanhamentoInline: vi.fn().mockResolvedValue({}),
  updateProvaInline: vi.fn().mockResolvedValue({}),
  getMunicipiosOptions: vi.fn().mockResolvedValue([]),
  getProjetosOptions: vi.fn().mockResolvedValue([]),
  getCoordenadoresOptions: vi.fn().mockResolvedValue([]),
}));

vi.mock('../../../api/availability', () => ({ getMe: vi.fn() }));

import { getMe } from '../../../api/availability';
import { updateAcompanhamentoInline, updateProvaInline } from '../../../api/datModule';
import PlanoFormacoesPage from '../PlanoFormacoesPage';

function renderPage() {
  return render(
    <MemoryRouter>
      <PlanoFormacoesPage />
    </MemoryRouter>,
  );
}

describe('#1913: edição inline de Acompanhamento e Prova', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getMe).mockResolvedValue({
      is_superuser: true, is_superintendencia: true,
      setores: ['Superintendência'], funcoes: ['Gerente'],
    } as never);
  });

  test(
    'clicar no Acompanhamento abre o modal e salva via updateAcompanhamentoInline',
    async () => {
      const user = userEvent.setup();
      renderPage();
      const cell = await screen.findByLabelText('Editar acompanhamento primeiro', {}, { timeout: 15000 });
      await user.click(cell);
      const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });
      await user.click(within(dialog).getByRole('button', { name: /salvar/i }));
      // payload EXATO: a chave gravável é `data_acompanhamento` (não `data`), senão a data é
      // descartada silenciosamente pelo DRF (partial=True). Contrato do AcompanhamentoSerializer.
      await waitFor(
        () =>
          expect(updateAcompanhamentoInline).toHaveBeenCalledWith(7, 'primeiro', {
            data_acompanhamento: '2026-03-10',
            realizado: false,
          }),
        { timeout: 10000 },
      );
    },
    25000,
  );

  test(
    'clicar na Prova abre o modal e salva via updateProvaInline',
    async () => {
      const user = userEvent.setup();
      renderPage();
      const cell = await screen.findByLabelText('Editar prova 1', {}, { timeout: 15000 });
      await user.click(cell);
      const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });
      await user.click(within(dialog).getByRole('button', { name: /salvar/i }));
      // payload EXATO: a chave gravável é `data_prova` (não `data`). Contrato do ProvaSerializer.
      await waitFor(
        () =>
          expect(updateProvaInline).toHaveBeenCalledWith(7, 1, {
            data_prova: '2026-04-10',
            realizada: false,
          }),
        { timeout: 10000 },
      );
    },
    25000,
  );
});
