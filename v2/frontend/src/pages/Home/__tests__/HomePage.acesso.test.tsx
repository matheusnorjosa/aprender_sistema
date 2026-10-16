/**
 * Página Inicial — linha de base persona × cartão (PR 7 das permissões).
 *
 * Os 10 atores de `src/test/atoresRbac.ts` mais um Gerente do setor "Gerência" (o único
 * que via "Desempenho da Equipe" pela regra antiga). Commitada verde com o código antigo;
 * no PR 7 só mudaram as exceções aprovadas pelo dono em 15/10, anotadas linha a linha:
 *
 * - E1: "Enviar Solicitação" e "Minhas Solicitações" seguem `create_solicitation` (o mesmo
 *   gate da rota). O DAT perde o atalho que dava "Recurso indisponível"; os Gerentes ganham.
 * - E2: "Desempenho da Equipe" segue `view_team_dashboard` (o gate de /dashboards/equipe).
 *   Diretoria e DAT ganham; o Gerente do setor Gerência perde o link que não abria.
 * - E3: o bloco Acesso Administrativo continua só do superusuário.
 */
import { MemoryRouter } from 'react-router';
import { render, screen } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

import { ATORES_RBAC, usuarioDeTeste, type AtorRbac } from '../../../test/atoresRbac';
import { ComAcesso } from '../../../test/comAcesso';
import HomePage from '../HomePage';

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
  policies: ['access_monthly_availability', 'create_solicitation'], // o que o backend devolve
};

const ESPERADO: Record<string, readonly Cartao[]> = {
  Superuser: [
    'Gerenciamento de Usuários',
    'Análises',
    'Solicitações de Aprovação',
    'Desempenho da Equipe', // E2: ganha (view_team_dashboard)
    'Meu Painel',
    'Enviar Solicitação',
    'Minhas Solicitações',
  ],
  // E1: perde Enviar/Minhas (sem create_solicitation: a rota negava). E2: ganha Desempenho.
  // PR 10: o DAT aprova e cria (pacote final do administrador operacional).
  DAT: ['Solicitações de Aprovação', 'Desempenho da Equipe', 'Meu Painel', 'Enviar Solicitação', 'Minhas Solicitações'],
  Controle: ['Meu Painel'],
  Diretoria: ['Desempenho da Equipe', 'Meu Painel'], // E2: ganha
  // E1: ganha Enviar/Minhas (create_solicitation).
  'Gerente da Superintendência': ['Solicitações de Aprovação', 'Meu Painel', 'Enviar Solicitação', 'Minhas Solicitações'],
  'Gerente pedagógico (Vidas)': ['Meu Painel', 'Enviar Solicitação', 'Minhas Solicitações'], // E1: ganha
  Coordenador: ['Meu Painel', 'Enviar Solicitação', 'Minhas Solicitações'],
  'Apoio de Coordenação': ['Meu Painel', 'Enviar Solicitação', 'Minhas Solicitações'],
  Formador: ['Meu Painel'],
  'Assistente Administrativo Controle': ['Solicitações de Aprovação', 'Meu Painel'],
  // E2: perde Desempenho (sem view_team_dashboard: a rota negava). E1: ganha Enviar/Minhas.
  'Gerente do setor Gerência': ['Meu Painel', 'Enviar Solicitação', 'Minhas Solicitações'],
};

const PESSOAS: readonly Pessoa[] = [...ATORES_RBAC, GERENTE_DO_SETOR_GERENCIA];

async function cartoesVisiveis(pessoa: Pessoa): Promise<Cartao[]> {
  render(
    <MemoryRouter>
      <ComAcesso policies={pessoa.policies} superusuario={pessoa.user.is_superuser}>
        <HomePage />
      </ComAcesso>
    </MemoryRouter>,
  );
  await screen.findByRole('heading', { name: 'Acesso Geral' });
  return CARTOES.filter((c) => screen.queryByRole('heading', { name: c, level: 5 }) !== null);
}

describe('Página Inicial — cartões por pessoa', () => {
  test('todas as pessoas têm linha esperada', () => {
    expect(PESSOAS.map((p) => p.ator).sort()).toEqual(Object.keys(ESPERADO).sort());
  });

  test.each(PESSOAS)('$ator', async (pessoa) => {
    expect(await cartoesVisiveis(pessoa)).toEqual(ESPERADO[pessoa.ator]);
  });

  test('o KPI "Minhas Solicitações" segue o cartão (create_solicitation)', async () => {
    await cartoesVisiveis({ ator: 'só create_solicitation', user: usuarioDeTeste({}), policies: ['create_solicitation'] });
    expect(screen.getByText('Minhas Solicitações', { selector: '.ant-statistic-title' })).toBeInTheDocument();
  });
});
