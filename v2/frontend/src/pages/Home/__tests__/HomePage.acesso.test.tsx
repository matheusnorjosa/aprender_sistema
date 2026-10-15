/**
 * Página Inicial — linha de base persona × cartão (PR 7 das permissões).
 *
 * Os 10 atores de `src/test/atoresRbac.ts` mais um Gerente do setor "Gerência" (o único
 * que via "Desempenho da Equipe" pela regra antiga). Commitada verde com o código antigo;
 * no PR 7 só mudam as exceções aprovadas pelo dono em 15/10 (E1, E2), anotadas linha a linha.
 */
import { MemoryRouter } from 'react-router';
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { getMe } from '../../../api/availability';
import { getMyPolicies } from '../../../api/me';
import { ATORES_RBAC, usuarioDeTeste, type AtorRbac } from '../../../test/atoresRbac';
import HomePage from '../HomePage';

vi.mock('../../../api/availability', () => ({ getMe: vi.fn() }));
vi.mock('../../../api/me', () => ({ getMyPolicies: vi.fn() }));
vi.mock('../../../api/stats', () => ({
  getHomeStats: vi.fn().mockResolvedValue({ pending_approvals: 0, my_requests: 0, upcoming_events: 0 }),
}));

const CARTOES = [
  'Gerenciamento de Usuários',
  'Análises',
  'Solicitações de Aprovação',
  'Desempenho da Equipe',
  'Meu Painel',
  'Enviar Solicitação',
  'Minhas Solicitações',
] as const;

type Cartao = (typeof CARTOES)[number];

type Pessoa = Pick<AtorRbac, 'user' | 'policies'> & { ator: string };

const GERENTE_DO_SETOR_GERENCIA: Pessoa = {
  ator: 'Gerente do setor Gerência',
  user: usuarioDeTeste({ setores: ['Gerência'], funcoes: ['Gerente'] }),
  policies: ['create_solicitation'],
};

const ESPERADO: Record<string, readonly Cartao[]> = {
  Superuser: [
    'Gerenciamento de Usuários',
    'Análises',
    'Solicitações de Aprovação',
    'Meu Painel',
    'Enviar Solicitação',
    'Minhas Solicitações',
  ],
  DAT: ['Meu Painel', 'Enviar Solicitação', 'Minhas Solicitações'],
  Controle: ['Meu Painel'],
  Diretoria: ['Meu Painel'],
  'Gerente da Superintendência': ['Solicitações de Aprovação', 'Meu Painel'],
  'Gerente pedagógico (Vidas)': ['Meu Painel'],
  Coordenador: ['Meu Painel', 'Enviar Solicitação', 'Minhas Solicitações'],
  'Apoio de Coordenação': ['Meu Painel', 'Enviar Solicitação', 'Minhas Solicitações'],
  Formador: ['Meu Painel'],
  'Assistente Administrativo Controle': ['Solicitações de Aprovação', 'Meu Painel'],
  'Gerente do setor Gerência': ['Desempenho da Equipe', 'Meu Painel'],
};

const PESSOAS: readonly Pessoa[] = [
  ...ATORES_RBAC,
  GERENTE_DO_SETOR_GERENCIA,
];

async function cartoesVisiveis(pessoa: Pick<AtorRbac, 'user' | 'policies'>): Promise<Cartao[]> {
  vi.mocked(getMe).mockResolvedValue(pessoa.user);
  vi.mocked(getMyPolicies).mockResolvedValue([...pessoa.policies]);
  render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  );
  await screen.findByRole('heading', { name: 'Acesso Geral' });
  return CARTOES.filter((c) => screen.queryByRole('heading', { name: c, level: 5 }) !== null);
}

describe('Página Inicial — cartões por pessoa', () => {
  beforeEach(() => vi.clearAllMocks());

  test('todas as pessoas têm linha esperada', () => {
    expect(PESSOAS.map((p) => p.ator).sort()).toEqual(Object.keys(ESPERADO).sort());
  });

  test.each(PESSOAS)('$ator', async (pessoa) => {
    expect(await cartoesVisiveis(pessoa)).toEqual(ESPERADO[pessoa.ator]);
  });
});
