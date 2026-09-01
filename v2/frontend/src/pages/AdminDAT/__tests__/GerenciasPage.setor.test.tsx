/**
 * #1914 (parte 2): conferência/entrada-direta de `setor_canonico` na GerenciasPage.
 * O #1926 expôs o campo gravável no GerenciaSerializer; esta tela mostra-o (coluna,
 * com flag "não definido" quando vazio) e edita-o (Select fechado do vocabulário
 * setor-de-produto).
 *
 * Continuação (PR-A): (a) coluna `setor_canonico_confianca` (read-only, sinal de qualidade
 * do de-para v15 — RELAY 50) e (b) o Select passa a ser alimentado pelo endpoint de options
 * (`getRBACMeta().setores_produto`) em vez da constante FE temporária — que havia DRIFTADO do
 * canônico ("Ler Ouvir e Contar" sem vírgulas vs "Ler, Ouvir e Contar").
 *
 * RED no código antigo (sem coluna de confiança; Select vem da constante hardcoded).
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';

const { GERENCIAS, RBAC_META } = vi.hoisted(() => ({
  GERENCIAS: [
    { id: 1, nome: 'Gerência A', nome_setor: 'Comercial', setor_canonico: 'ACerta', setor_canonico_confianca: 'alta', gerente: null, gerente_nome: '', ativo: true, descricao: '', projetos_count: 2, created_at: '', updated_at: '' },
    { id: 2, nome: 'Gerência B', nome_setor: 'Operações', setor_canonico: '', setor_canonico_confianca: '', gerente: null, gerente_nome: '', ativo: true, descricao: '', projetos_count: 0, created_at: '', updated_at: '' },
  ],
  // valor canônico com VÍRGULAS: só pode vir do endpoint (a constante antiga não tinha vírgulas).
  RBAC_META: { setor_groups: [], funcao_groups: [], categories: [], setores_produto: ['ACerta', 'Ler, Ouvir e Contar', 'Vidas'] },
}));

vi.mock('../../../api/adminDAT', () => ({
  listGerencias: vi.fn().mockResolvedValue({ results: GERENCIAS, count: 2, next: null, previous: null }),
  createGerencia: vi.fn().mockResolvedValue({}),
  updateGerencia: vi.fn().mockResolvedValue({}),
  deleteGerencia: vi.fn().mockResolvedValue({}),
  getRBACMeta: vi.fn().mockResolvedValue(RBAC_META),
}));

import GerenciasPage from '../GerenciasPage';
import { updateGerencia, getRBACMeta } from '../../../api/adminDAT';

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

  test('coluna Confiança mostra o valor importado (read-only) e "—" quando ausente', async () => {
    renderPage();
    // header da coluna (AntD duplica o header quando a Table tem scroll → getAllByText)
    expect((await screen.findAllByText('Confiança', {}, { timeout: 15000 })).length).toBeGreaterThan(0);
    // gerência 1 tem confianca "alta" (sinal do de-para, célula única); gerência 2 não tem → em-dash
    expect(await screen.findByText('alta')).toBeInTheDocument();
    expect(await screen.findByText('—')).toBeInTheDocument();
  }, 20000);

  test('Select de setor_canonico é alimentado pelo endpoint de options (canônico com vírgulas)', async () => {
    const user = userEvent.setup();
    renderPage();
    // wiring: a página busca o vocabulário no mount
    await waitFor(() => expect(getRBACMeta).toHaveBeenCalled(), { timeout: 15000 });

    const editBtns = await screen.findAllByRole('button', { name: /editar/i }, { timeout: 15000 });
    await user.click(editBtns[0]);
    const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });
    // abre o Select (único combobox do form)
    await user.click(within(dialog).getByRole('combobox'));
    // opção canônica com vírgulas prova consumo do endpoint (constante antiga não tinha vírgulas) → drift-guard
    // (AntD renderiza a opção em >1 nó: label + title) → findAllByText
    expect((await screen.findAllByText('Ler, Ouvir e Contar', {}, { timeout: 10000 })).length).toBeGreaterThan(0);
  }, 30000);

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
