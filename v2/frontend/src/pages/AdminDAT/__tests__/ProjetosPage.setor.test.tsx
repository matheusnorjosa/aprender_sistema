/**
 * #1914: conferência de `Projeto.setor` na ProjetosPage.
 * Split anti-M17 no ProjetoSerializer: `setor` é GRAVÁVEL (raw); `setor_efetivo` é derivado
 * read-only (= setor || gerencia.nome_setor). A GRADE exibe `setor_efetivo`; o form de
 * conferência liga no RAW `setor` (Select fechado via /rbac/meta/). Semear o derivado no form
 * contaminaria o raw ao salvar (M17) — por isso o handleEdit semeia `projeto.setor`.
 *
 * RED no código antigo (ProjetosPage não tem setor: nem coluna, nem Select, nem no payload).
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';

const { PROJETOS, RBAC_META } = vi.hoisted(() => ({
  PROJETOS: [
    // raw preenchido; efetivo == raw; gerência com nome de tela diferente do catálogo (PR A)
    { id: 1, nome: 'Projeto Raw', codigo: 'PR', fluxo: 'NAO_SUPER', ativo: true, setor: 'Fluir', setor_efetivo: 'Fluir', gerencia_nome: 'Superativar' },
    // raw VAZIO, efetivo DERIVADO da gerência ('Vidas') → caso anti-M17
    { id: 2, nome: 'Projeto Derivado', codigo: 'PD', fluxo: 'NAO_SUPER', ativo: true, setor: '', setor_efetivo: 'Vidas', gerencia_nome: 'Vidas' },
  ],
  RBAC_META: { setor_groups: [], funcao_groups: [], categories: [], setores_produto: ['Fluir', 'Sou da Paz', 'Vidas'] },
}));

vi.mock('../../../api/adminDAT', () => ({
  listProjetos: vi.fn().mockResolvedValue({ results: PROJETOS, count: 2, next: null, previous: null }),
  createProjeto: vi.fn().mockResolvedValue({}),
  updateProjeto: vi.fn().mockResolvedValue({}),
  deleteProjeto: vi.fn().mockResolvedValue({}),
  getRBACMeta: vi.fn().mockResolvedValue(RBAC_META),
  listGerencias: vi.fn().mockResolvedValue({ results: [], count: 0, next: null, previous: null }),
}));

import ProjetosPage from '../ProjetosPage';
import { updateProjeto, getRBACMeta } from '../../../api/adminDAT';

function renderPage() {
  return render(
    <MemoryRouter>
      <ProjetosPage />
    </MemoryRouter>,
  );
}

describe('ProjetosPage — conferência de Projeto.setor (#1914)', () => {
  beforeEach(() => vi.clearAllMocks());

  test('PR A: "Setor" mostra o rótulo da gerência; o setor do catálogo aparece só quando difere', async () => {
    renderPage();
    // Projeto 1: gerência "Superativar", catálogo "Fluir" → os dois, sem coluna nova (sem rolagem)
    expect(await screen.findByText('Superativar', {}, { timeout: 15000 })).toBeInTheDocument();
    expect(screen.getByText('catálogo: Fluir')).toBeInTheDocument();
    // Projeto 2: gerência == catálogo derivado ("Vidas") → só a tag
    expect(screen.getByText('Vidas')).toBeInTheDocument();
    expect(screen.queryByText('catálogo: Vidas')).not.toBeInTheDocument();
  }, 20000);

  test('anti-M17: editar+salvar mantém o RAW setor (não grava o derivado)', async () => {
    const user = userEvent.setup();
    renderPage();
    const editBtns = await screen.findAllByRole('button', { name: /editar/i }, { timeout: 15000 });
    await user.click(editBtns[1]); // Projeto 2 (raw='', efetivo='Vidas')
    await screen.findByRole('dialog', {}, { timeout: 10000 });
    // salva sem tocar no setor: o form foi semeado com o RAW ('') — NÃO com 'Vidas'
    await user.click(screen.getByRole('button', { name: /salvar/i }));
    await waitFor(
      () => expect(updateProjeto).toHaveBeenCalledWith(2, expect.objectContaining({ setor: '' })),
      { timeout: 10000 },
    );
    // guarda explícita: jamais grava o derivado no raw
    expect(updateProjeto).not.toHaveBeenCalledWith(2, expect.objectContaining({ setor: 'Vidas' }));
  }, 30000);

  test('Select de setor é alimentado pelo endpoint de options (/rbac/meta/)', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(getRBACMeta).toHaveBeenCalled(), { timeout: 15000 });
    const editBtns = await screen.findAllByRole('button', { name: /editar/i }, { timeout: 15000 });
    await user.click(editBtns[0]);
    const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });
    await user.click(within(dialog).getByRole('combobox', { name: /setor canônico/i }));
    // 'Sou da Paz' só existe no endpoint (não é setor de nenhuma linha) → prova consumo do endpoint
    expect((await screen.findAllByText('Sou da Paz', {}, { timeout: 10000 })).length).toBeGreaterThan(0);
  }, 30000);
});
