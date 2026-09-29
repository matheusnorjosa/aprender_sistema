/**
 * FiltersBar — escolha de gerência da Grade Mensal (PR A, PLANOS_LIBERACAO_2026-09-29 §2).
 *
 * - Quem tem a policy `view_all_availability` vê "Participantes de projetos SUPER"
 *   (a antiga "Todas", decisão 3 do dono) mais as gerências ATIVAS.
 * - Os demais veem só `me.gerencias` (vínculo EquipeGerencia vigente), nunca o grupo de
 *   setor; a primeira é selecionada sozinha quando `gerenciaId` é null.
 * - Sem vínculo e sem policy: select desabilitado com "Sem gerência vinculada".
 * - O rótulo é `rotulo` (nome de tela), nunca o `nome` técnico ("GERENCIA 4").
 */

import { render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import type { CurrentUser, Gerencia } from '../../../types';

const { getGerenciasMock, getMeMock, getMyPoliciesMock } = vi.hoisted(() => ({
  getGerenciasMock: vi.fn(),
  getMeMock: vi.fn(),
  getMyPoliciesMock: vi.fn(),
}));

vi.mock('../../../api/availability', () => ({
  getGerencias: getGerenciasMock,
  getMe: getMeMock,
}));
vi.mock('../../../api/me', () => ({
  getMyPolicies: getMyPoliciesMock,
}));

import FiltersBar from '../FiltersBar';

const ATIVAS: Gerencia[] = [
  { id: 2, nome: 'GERENCIA 2', nome_setor: 'Vidas', nome_exibicao: '', rotulo: 'Vidas', ativo: true },
  { id: 3, nome: 'GERENCIA 3', nome_setor: 'Fluir', nome_exibicao: '', rotulo: 'Fluir', ativo: true },
  { id: 4, nome: 'GERENCIA 4', nome_setor: 'ACerta', nome_exibicao: 'Superativar', rotulo: 'Superativar', ativo: true },
];

function makeMe(overrides: Partial<CurrentUser> = {}): CurrentUser {
  return {
    id: 1,
    username: 'coord',
    email: 'coord@example.invalid',
    first_name: 'Coord',
    last_name: 'Teste',
    name: 'Coord Teste',
    groups: [],
    setores: [],
    funcoes: [],
    gerencias: [],
    is_superuser: false,
    is_superintendencia: false,
    can_approve_super: false,
    permissions: [],
    ...overrides,
  };
}

function renderBar(gerenciaId: number | null = null) {
  const onChange = vi.fn();
  render(<FiltersBar year={2026} month={9} gerenciaId={gerenciaId} sector="" q="" onChange={onChange} />);
  return onChange;
}

async function opcoes(): Promise<string[]> {
  const select = screen.getByLabelText('Gerência');
  await waitFor(() => expect(select).not.toBeDisabled());
  return within(select).getAllByRole('option').map((o) => o.textContent ?? '');
}

describe('FiltersBar — gerência pelo vínculo + policy', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getGerenciasMock.mockResolvedValue(ATIVAS);
    getMyPoliciesMock.mockResolvedValue([]);
  });

  test('só vínculo: a única opção é a gerência dele, sem "todas", e já vem selecionada', async () => {
    getMeMock.mockResolvedValue(
      makeMe({ gerencias: [{ id: 4, rotulo: 'Superativar', papeis: ['COORDENADOR'] }] }),
    );
    const onChange = renderBar();

    expect(await opcoes()).toEqual(['Superativar']);
    expect(onChange).toHaveBeenCalledWith({ gerenciaId: 4 });
  });

  test('dois vínculos: a primeira é auto-selecionada', async () => {
    getMeMock.mockResolvedValue(
      makeMe({
        gerencias: [
          { id: 3, rotulo: 'Fluir', papeis: ['COORDENADOR'] },
          { id: 2, rotulo: 'Vidas', papeis: ['GERENTE'] },
        ],
      }),
    );
    const onChange = renderBar();

    expect(await opcoes()).toEqual(['Fluir', 'Vidas']);
    expect(onChange).toHaveBeenCalledWith({ gerenciaId: 3 });
  });

  test('com a policy: "Participantes de projetos SUPER" mais as ativas, sem auto-seleção', async () => {
    getMeMock.mockResolvedValue(makeMe({ setores: ['Controle'] }));
    getMyPoliciesMock.mockResolvedValue(['view_all_availability']);
    const onChange = renderBar();

    expect(await opcoes()).toEqual(['Participantes de projetos SUPER', 'Fluir', 'Superativar', 'Vidas']);
    expect(onChange).not.toHaveBeenCalled();
  });

  test('pede só as gerências ativas (inativa não aparece)', async () => {
    getMeMock.mockResolvedValue(makeMe());
    getMyPoliciesMock.mockResolvedValue(['view_all_availability']);
    renderBar();

    await opcoes();
    expect(getGerenciasMock).toHaveBeenCalledWith({ ativo: true });
  });

  test('grupo Vidas com vínculo em Fluir: só aparece Fluir', async () => {
    getMeMock.mockResolvedValue(
      makeMe({ setores: ['Vidas'], gerencias: [{ id: 3, rotulo: 'Fluir', papeis: ['COORDENADOR'] }] }),
    );
    renderBar();

    expect(await opcoes()).toEqual(['Fluir']);
  });

  test('nenhuma opção mostra o código interno ("GERENCIA N")', async () => {
    getMeMock.mockResolvedValue(makeMe({ is_superuser: true }));
    getMyPoliciesMock.mockResolvedValue(['view_all_availability']);
    renderBar();

    const textos = await opcoes();
    expect(textos.length).toBeGreaterThan(1);
    expect(textos.some((t) => /GERENCIA/.test(t))).toBe(false);
  });

  test('sem vínculo e sem policy: select desabilitado com a mensagem', async () => {
    getMeMock.mockResolvedValue(makeMe({ setores: ['Superintendência'], is_superintendencia: true }));
    const onChange = renderBar();

    expect(await screen.findByRole('option', { name: 'Sem gerência vinculada' })).toBeInTheDocument();
    await waitFor(() => expect(getMyPoliciesMock).toHaveBeenCalled());
    expect(screen.getByLabelText('Gerência')).toBeDisabled();
    expect(onChange).not.toHaveBeenCalled();
  });

  test('gerenciaId já definido não é sobrescrito', async () => {
    getMeMock.mockResolvedValue(
      makeMe({
        gerencias: [
          { id: 3, rotulo: 'Fluir', papeis: ['COORDENADOR'] },
          { id: 2, rotulo: 'Vidas', papeis: ['COORDENADOR'] },
        ],
      }),
    );
    const onChange = renderBar(2);

    expect(await opcoes()).toEqual(['Fluir', 'Vidas']);
    expect(onChange).not.toHaveBeenCalled();
  });

  test('o filtro de texto se chama "Projeto" (filtra pelo nome do projeto)', async () => {
    getMeMock.mockResolvedValue(makeMe());
    renderBar();

    expect(screen.getByLabelText('Projeto')).toBeInTheDocument();
    await waitFor(() => expect(getMeMock).toHaveBeenCalled());
  });
});
