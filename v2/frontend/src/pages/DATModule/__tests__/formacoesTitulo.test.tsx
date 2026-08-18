/**
 * #1739: o formulário de Nova Formação não coletava o campo `titulo`, que é obrigatório
 * no serializer (DATFormacao.titulo é CharField NOT NULL) → todo create tomava 400
 * "titulo: este campo é obrigatório". O fix adiciona o Form.Item name="titulo".
 *
 * RED no código antigo: o modal de criação não tinha o campo Título da Formação.
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';

vi.mock('../../../api/datModule', () => ({
  listFormacoes: vi.fn().mockResolvedValue({ results: [], count: 0, next: null, previous: null }),
  createFormacao: vi.fn().mockResolvedValue({}),
  updateFormacao: vi.fn().mockResolvedValue({}),
  deleteFormacao: vi.fn().mockResolvedValue({}),
  getFormacoesStats: vi.fn().mockResolvedValue({ total: 0, este_mes: 0, realizadas: 0 }),
  getFormacoesCalendario: vi.fn().mockResolvedValue({ results: [] }),
  getMunicipiosOptions: vi.fn().mockResolvedValue({ results: [] }),
  getProjetosOptions: vi.fn().mockResolvedValue({ results: [] }),
  getCoordenadoresOptions: vi.fn().mockResolvedValue({ results: [] }),
}));

import FormacoesPage from '../FormacoesPage';

describe('#1739: Nova Formação coleta o Título obrigatório', () => {
  beforeEach(() => vi.clearAllMocks());

  // Timeouts folgados: renderizar a página inteira (Table + filtros + options) em jsdom
  // é lento; o comportamento testado (o campo existe no modal) é rápido.
  test(
    'abrir "Nova Formação" mostra o campo Título da Formação',
    async () => {
      render(
        <MemoryRouter>
          <FormacoesPage />
        </MemoryRouter>,
      );
      const novaBtn = await screen.findByRole('button', { name: /Nova Formação/i }, { timeout: 15000 });
      await userEvent.click(novaBtn);
      const titulo = await screen.findByLabelText(/Título da Formação/i, {}, { timeout: 10000 });
      expect(titulo).toBeTruthy();
    },
    20000,
  );
});
