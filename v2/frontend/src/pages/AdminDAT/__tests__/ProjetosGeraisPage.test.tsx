/**
 * #1914: ProjetoGeral tinha ViewSet (CRUD em /api/projetos-gerais/) mas nenhuma tela no
 * frontend — só podia ser escolhido em dropdowns, nunca gerenciado. Esta é a página de CRUD
 * de admin, espelhando o padrão AdminDAT (ProjetosPage). A "conferência de setor_canonico"
 * NÃO faz parte deste PR (costura de backend #1914-BE: setor_canonico não é serializado).
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';

const { ITEMS } = vi.hoisted(() => ({
  ITEMS: [
    { id: 1, nome: 'PROJETO AMMA', usa_avaliar: true, tipo_calculo_codigos: 'por_professor', divisor_aluno: 20, multiplicador_professor: '1.10', ativo: true, descricao: '', projetos_count: 3, created_at: '', updated_at: '' },
    { id: 2, nome: 'PROJETO VIDAS', usa_avaliar: false, tipo_calculo_codigos: 'por_aluno', divisor_aluno: 20, multiplicador_professor: '1.10', ativo: true, descricao: '', projetos_count: 1, created_at: '', updated_at: '' },
  ],
}));

vi.mock('../../../api/adminDAT', () => ({
  listProjetosGerais: vi.fn().mockResolvedValue({ results: ITEMS, count: 2, next: null, previous: null }),
  createProjetoGeral: vi.fn().mockResolvedValue({ id: 3 }),
  updateProjetoGeral: vi.fn().mockResolvedValue({}),
  deleteProjetoGeral: vi.fn().mockResolvedValue({}),
}));

import ProjetosGeraisPage from '../ProjetosGeraisPage';
import { createProjetoGeral } from '../../../api/adminDAT';

function renderPage() {
  return render(
    <MemoryRouter>
      <ProjetosGeraisPage />
    </MemoryRouter>,
  );
}

describe('ProjetosGeraisPage (#1914 — CRUD admin)', () => {
  beforeEach(() => vi.clearAllMocks());

  test('lista os projetos gerais retornados pela API', async () => {
    renderPage();
    expect(await screen.findByText('PROJETO AMMA', {}, { timeout: 15000 })).toBeInTheDocument();
    expect(await screen.findByText('PROJETO VIDAS')).toBeInTheDocument();
  });

  test('o botão "Novo" abre o modal e cria via createProjetoGeral', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: /novo projeto geral/i }, { timeout: 15000 }));
    const nome = await screen.findByLabelText('Nome', {}, { timeout: 10000 });
    await user.type(nome, 'PROJETO NOVO');
    await user.click(screen.getByRole('button', { name: /salvar/i }));
    await waitFor(
      () => expect(createProjetoGeral).toHaveBeenCalledWith(expect.objectContaining({ nome: 'PROJETO NOVO' })),
      { timeout: 10000 },
    );
  });
});
