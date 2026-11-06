/**
 * Gerências, lote C do alinhamento (06/11/2026).
 *
 * - Cada setor tem uma gerência só (D03, D74): o 400 do servidor ("Já existe a gerência X para este setor.")
 *   aparece no campo que o define, no modal.
 * - Textos com acento (B#47): "Gerências", "Nova Gerência", "Descrição", "obrigatório", "Navegação".
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { GERENCIAS, MSG } = vi.hoisted(() => ({
  MSG: 'Já existe a gerência Vidas para este setor. Cada setor tem uma gerência só.',
  GERENCIAS: [
    {
      id: 8, nome: 'GERENCIA 8', nome_setor: 'Vidas', nome_exibicao: '', rotulo: 'Vidas', setor_canonico: 'Vidas',
      setor_canonico_confianca: '', gerente: null, gerente_nome: '', ativo: true, descricao: '',
      projetos_count: 0, created_at: '', updated_at: '',
    },
  ],
}));

vi.mock('../../../api/adminDAT', () => ({
  listGerencias: vi.fn().mockResolvedValue({ results: GERENCIAS, count: 1, next: null, previous: null }),
  createGerencia: vi.fn(),
  updateGerencia: vi.fn(),
  deleteGerencia: vi.fn(),
  getRBACMeta: vi.fn().mockResolvedValue({
    setor_groups: [], funcao_groups: [], categories: [], setores_produto: ['Vidas', 'Fluir'],
  }),
}));

import { createGerencia } from '../../../api/adminDAT';
import GerenciasPage from '../GerenciasPage';

function renderPage() {
  return render(
    <ConfigProvider locale={ptBR}>
      <MemoryRouter>
        <GerenciasPage />
      </MemoryRouter>
    </ConfigProvider>,
  );
}

async function abrirNova(user: ReturnType<typeof userEvent.setup>): Promise<HTMLElement> {
  await user.click(await screen.findByRole('button', { name: /Nova Gerência/ }, { timeout: 15000 }));
  return (await screen.findByText('Nova Gerência', { selector: '.ant-modal-title' }, { timeout: 10000 })).closest<HTMLElement>(
    '[role="dialog"]',
  )!;
}

describe('GerenciasPage — uma gerência por setor e acentos (lote C)', { timeout: 45000 }, () => {
  beforeEach(() => vi.clearAllMocks());

  test('o 400 de setor repetido aparece no campo Setor canônico', async () => {
    vi.mocked(createGerencia).mockRejectedValueOnce(
      Object.assign(new Error('Erro de validação.'), {
        response: { status: 400, data: { detail: 'Erro de validação.', errors: { setor_canonico: [MSG] } } },
      }),
    );
    const user = userEvent.setup();
    renderPage();
    const modal = await abrirNova(user);

    await user.type(within(modal).getByLabelText('Código interno'), 'GERENCIA NOVA');
    await user.type(within(modal).getByLabelText('Rótulo nas planilhas'), 'Vidas Nova');
    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));

    const aviso = await within(modal).findByText(MSG, {}, { timeout: 10000 });
    const campo = aviso.closest('.ant-form-item');
    expect(campo).not.toBeNull();
    expect(within(campo as HTMLElement).getByText(/Setor canônico/)).toBeInTheDocument();
  });

  test('textos com acento', async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('Gerências (1)'), {
      timeout: 15000,
    });
    expect(screen.getByRole('navigation', { name: 'Navegação' })).toBeInTheDocument();
    const modal = await abrirNova(user);
    expect(within(modal).getByLabelText('Descrição')).toHaveAttribute('placeholder', 'Descrição da gerência');
    expect(within(modal).getByRole('checkbox', { name: 'Gerência ativa' })).toBeInTheDocument();

    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));
    expect(await within(modal).findByText('Código interno é obrigatório', {}, { timeout: 10000 })).toBeInTheDocument();
    expect(within(modal).getByText('Rótulo nas planilhas é obrigatório')).toBeInTheDocument();
  });
});
