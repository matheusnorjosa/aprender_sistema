/**
 * #1914 (parte 2): conferência/entrada-direta de `setor_canonico` na GerenciasPage.
 * O #1926 expôs o campo gravável no GerenciaSerializer; esta tela passa a mostrá-lo (coluna,
 * com flag "não definido" quando vazio) e a editá-lo (Select fechado do vocabulário
 * setor-de-produto). A coluna de `confianca` NÃO faz parte deste PR (espera persistência no BE).
 *
 * RED no código antigo (GerenciasPage não mostra nem grava setor_canonico).
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';

const { GERENCIAS } = vi.hoisted(() => ({
  GERENCIAS: [
    { id: 1, nome: 'Gerência A', nome_setor: 'Comercial', setor_canonico: 'ACerta', gerente: null, gerente_nome: '', ativo: true, descricao: '', projetos_count: 2, created_at: '', updated_at: '' },
    { id: 2, nome: 'Gerência B', nome_setor: 'Operações', setor_canonico: '', gerente: null, gerente_nome: '', ativo: true, descricao: '', projetos_count: 0, created_at: '', updated_at: '' },
  ],
}));

vi.mock('../../../api/adminDAT', () => ({
  listGerencias: vi.fn().mockResolvedValue({ results: GERENCIAS, count: 2, next: null, previous: null }),
  createGerencia: vi.fn().mockResolvedValue({}),
  updateGerencia: vi.fn().mockResolvedValue({}),
  deleteGerencia: vi.fn().mockResolvedValue({}),
}));

import GerenciasPage from '../GerenciasPage';
import { updateGerencia } from '../../../api/adminDAT';

function renderPage() {
  return render(
    <MemoryRouter>
      <GerenciasPage />
    </MemoryRouter>,
  );
}

describe('GerenciasPage — conferência de setor_canonico (#1914)', () => {
  beforeEach(() => vi.clearAllMocks());

  test('coluna mostra o setor_canonico e sinaliza "não definido" quando vazio', async () => {
    renderPage();
    // valor canônico distinto do nome_setor (Comercial) → só pode vir da coluna setor_canonico
    expect(await screen.findByText('ACerta', {}, { timeout: 15000 })).toBeInTheDocument();
    // gerência 2 tem setor_canonico vazio → flag
    expect(await screen.findByText('não definido')).toBeInTheDocument();
  }, 20000);

  test('editar preserva/grava setor_canonico (round-trip → updateGerencia)', async () => {
    const user = userEvent.setup();
    renderPage();
    const editBtns = await screen.findAllByRole('button', { name: /editar/i }, { timeout: 15000 });
    await user.click(editBtns[0]);
    await screen.findByRole('dialog', {}, { timeout: 10000 });
    await user.click(screen.getByRole('button', { name: /salvar/i }));
    await waitFor(
      () => expect(updateGerencia).toHaveBeenCalledWith(1, expect.objectContaining({ setor_canonico: 'ACerta' })),
      { timeout: 10000 },
    );
  }, 30000);
});
