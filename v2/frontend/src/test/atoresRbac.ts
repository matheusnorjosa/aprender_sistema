/**
 * Os 10 atores de `apps/core/rbac/matrix.py`, como o front os recebe: o payload de `/api/me/`
 * e a lista de `/api/me/policies/`. Fonte única das linhas de base persona × tela (menu,
 * rotas e Página Inicial).
 *
 * - Grupos e vínculos espelham `_make_user_for_actor` (test_rbac_matrix_living.py): Gerente,
 *   Gerente da Superintendência, Coordenador e Apoio têm vínculo vigente de gestão.
 * - `policies` foi medida no backend para esses mesmos usuários (`resolve_public_policies`,
 *   seed do RBAC, 15/10/2026). Mudou o seed ou uma policy? Meça de novo e atualize aqui.
 *
 * Sem dado pessoal: nomes e e-mails são de teste.
 */
import type { CurrentUser, GerenciaVinculo } from '../types';

export type NomeDoAtor =
  | 'Superuser'
  | 'DAT'
  | 'Controle'
  | 'Diretoria'
  | 'Gerente da Superintendência'
  | 'Gerente pedagógico (Vidas)'
  | 'Coordenador'
  | 'Apoio de Coordenação'
  | 'Formador'
  | 'Assistente Administrativo Controle';

export interface AtorRbac {
  ator: NomeDoAtor;
  user: CurrentUser;
  policies: readonly string[];
}

const USUARIO_BASE: CurrentUser = {
  id: 1,
  username: 'ator-teste',
  email: 'ator-teste@example.invalid',
  first_name: 'Ator',
  last_name: 'Teste',
  name: 'Ator Teste',
  groups: [],
  setores: [],
  funcoes: [],
  gerencias: [],
  is_superuser: false,
  is_superintendencia: false,
  can_approve_super: false,
  permissions: [],
};

/** Payload de `/api/me/` a partir dos grupos (setor/função) e dos vínculos de gestão. */
export function usuarioDeTeste(opcoes: {
  setores?: string[];
  funcoes?: string[];
  gerencias?: GerenciaVinculo[];
  superusuario?: boolean;
  aprovador?: boolean;
}): CurrentUser {
  const setores = opcoes.setores ?? [];
  const funcoes = opcoes.funcoes ?? [];
  const superusuario = opcoes.superusuario === true;
  return {
    ...USUARIO_BASE,
    groups: [...setores, ...funcoes],
    setores,
    funcoes,
    gerencias: opcoes.gerencias ?? [],
    is_superuser: superusuario,
    is_superintendencia: superusuario || setores.includes('Superintendência'),
    can_approve_super: superusuario || opcoes.aprovador === true,
  };
}

const vinculo = (papel: string, rotulo = 'Gerência de teste'): GerenciaVinculo[] => [{ id: 4, rotulo, papeis: [papel] }];

export const ATORES_RBAC: readonly AtorRbac[] = [
  {
    ator: 'Superuser',
    user: usuarioDeTeste({ superusuario: true }),
    // O backend dá ao superusuário todas as PUBLIC_POLICY_KEYS.
    policies: [
      'access_audit_logs',
      'access_controle_section',
      'access_solicitation_approvals',
      'create_solicitation',
      'import_availability_blocks',
      'import_compras',
      'import_generic_spreadsheet',
      'manage_admin_registries',
      'manage_internal_actions',
      'manage_purchases_and_materials',
      'manage_solicitacao_status',
      'publish_setor_solicitacao',
      'use_gcal',
      'view_all_availability',
      'view_compras_dashboard',
      'view_compras_pendencias',
      'view_compras_stats',
      'view_gcal_dashboard',
      'view_map_metrics',
      'view_overview_dashboard',
      'view_reports',
      'view_team_dashboard',
    ],
  },
  {
    ator: 'DAT',
    user: usuarioDeTeste({ setores: ['DAT'] }),
    policies: [
      'access_audit_logs',
      'import_availability_blocks',
      'import_compras',
      'import_generic_spreadsheet',
      'manage_admin_registries',
      'manage_purchases_and_materials',
      'view_all_availability',
      'view_compras_dashboard',
      'view_compras_pendencias',
      'view_compras_stats',
      'view_gcal_dashboard',
      'view_map_metrics',
      'view_reports',
      'view_team_dashboard',
    ],
  },
  {
    ator: 'Controle',
    user: usuarioDeTeste({ setores: ['Controle'] }),
    policies: [
      'access_audit_logs',
      'access_controle_section',
      'import_availability_blocks',
      'import_compras',
      'import_generic_spreadsheet',
      'manage_purchases_and_materials',
      'manage_solicitacao_status',
      'use_gcal',
      'view_all_availability',
      'view_compras_pendencias',
      'view_compras_stats',
      'view_gcal_dashboard',
      'view_reports',
    ],
  },
  {
    ator: 'Diretoria',
    user: usuarioDeTeste({ setores: ['Diretoria'] }),
    policies: [
      'view_compras_dashboard',
      'view_compras_pendencias',
      'view_gcal_dashboard',
      'view_map_metrics',
      'view_overview_dashboard',
      'view_team_dashboard',
    ],
  },
  {
    ator: 'Gerente da Superintendência',
    user: usuarioDeTeste({
      setores: ['Superintendência'],
      funcoes: ['Gerente'],
      gerencias: vinculo('GERENTE', 'Superintendência'),
      aprovador: true,
    }),
    policies: [
      'access_solicitation_approvals',
      'create_solicitation',
      'manage_solicitacao_status',
      'use_gcal',
      'view_reports',
    ],
  },
  {
    ator: 'Gerente pedagógico (Vidas)',
    user: usuarioDeTeste({ funcoes: ['Gerente'], gerencias: vinculo('GERENTE') }),
    policies: ['create_solicitation'],
  },
  {
    ator: 'Coordenador',
    user: usuarioDeTeste({ funcoes: ['Coordenador'], gerencias: vinculo('COORDENADOR') }),
    policies: ['create_solicitation'],
  },
  {
    ator: 'Apoio de Coordenação',
    user: usuarioDeTeste({ funcoes: ['Apoio de Coordenação'], gerencias: vinculo('APOIO') }),
    policies: ['create_solicitation', 'publish_setor_solicitacao'],
  },
  {
    ator: 'Formador',
    user: usuarioDeTeste({ funcoes: ['Formador'] }),
    policies: [],
  },
  {
    ator: 'Assistente Administrativo Controle',
    user: usuarioDeTeste({ setores: ['Controle'], funcoes: ['Assistente Administrativo'], aprovador: true }),
    policies: [
      'access_audit_logs',
      'access_controle_section',
      'access_solicitation_approvals',
      'import_availability_blocks',
      'import_compras',
      'import_generic_spreadsheet',
      'manage_purchases_and_materials',
      'manage_solicitacao_status',
      'use_gcal',
      'view_all_availability',
      'view_compras_pendencias',
      'view_compras_stats',
      'view_gcal_dashboard',
      'view_reports',
    ],
  },
];

export function atorRbac(nome: NomeDoAtor): AtorRbac {
  const encontrado = ATORES_RBAC.find((a) => a.ator === nome);
  if (!encontrado) throw new Error(`Ator desconhecido: ${nome}`);
  return encontrado;
}
