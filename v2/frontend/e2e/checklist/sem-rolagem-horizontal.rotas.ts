/**
 * Rotas medidas pelo spec `sem-rolagem-horizontal.spec.ts` (Programa C, C0).
 *
 * Dados puros, sem import do Playwright: o teste de cobertura do Vitest
 * (`src/components/__tests__/AppRoutes.semRolagemHorizontal.test.ts`) importa
 * este arquivo e compara com os `path` de `AppRoutes.tsx`. Rota nova no
 * AppRoutes sem entrada aqui reprova o Vitest.
 */

/** Larguras de tela medidas (px). 1024 = notebook de 1366 px com escala de 125%. */
export const LARGURAS = [360, 768, 1024, 1280] as const;
export type Largura = (typeof LARGURAS)[number];

/**
 * Perfis usados na medição. Todos vêm de `seed_frontend_contract_data`
 * (o seed que o job `[required] checklist tests` roda), senha `testpass123`.
 */
export const PERFIS = {
  coordenador: 'coord_vidas@test.com',
  controle: 'controle_e2e@test.com',
  dat: 'dat_matrix@test.com',
  aprovador: 'super_e2e@test.com',
  // Único jeito de abrir as rotas cuja policy não tem grupo no seed
  // (manage_internal_actions só o superuser tem; view_overview_dashboard e
  // view_map_metrics são da Diretoria, sem usuário no seed E2E).
  superusuario: 'admin_matrix@test.com',
} as const;
export type Perfil = keyof typeof PERFIS;
export const SENHA_PERFIS = 'testpass123';

export interface RotaMedida {
  /** O `path` exatamente como está em AppRoutes.tsx. */
  path: string;
  /** Perfil que consegue abrir a rota (e que vê linhas nas tabelas dela). */
  perfil: Perfil;
  /** Rota com parâmetro: o spec descobre o id pela API antes de navegar. */
  parametro?: 'solicitacaoEditavel';
}

export const ROTAS_MEDIDAS: readonly RotaMedida[] = [
  { path: '/', perfil: 'controle' },
  { path: '/dashboards', perfil: 'superusuario' },
  { path: '/dashboards/compras', perfil: 'dat' },
  { path: '/dashboards/equipe', perfil: 'dat' },
  { path: '/dashboards/gcal', perfil: 'controle' },
  { path: '/mapa-brasil', perfil: 'superusuario' },
  { path: '/solicitacoes/minhas', perfil: 'coordenador' },
  { path: '/solicitacoes/nova', perfil: 'coordenador' },
  { path: '/solicitacoes/publicacao', perfil: 'superusuario' },
  { path: '/solicitacoes/:id/editar', perfil: 'coordenador', parametro: 'solicitacaoEditavel' },
  { path: '/solicitacoes/aprovacoes', perfil: 'aprovador' },
  { path: '/solicitacoes/disponibilidade', perfil: 'controle' },
  { path: '/solicitacoes/bloqueios', perfil: 'coordenador' },
  { path: '/solicitacoes/deslocamentos', perfil: 'controle' },
  { path: '/solicitacoes/meus-eventos', perfil: 'coordenador' },
  { path: '/perfil', perfil: 'coordenador' },
  { path: '/politica-privacidade', perfil: 'coordenador' },
  { path: '/controle', perfil: 'controle' },
  { path: '/controle/acoes', perfil: 'controle' },
  { path: '/controle/compras', perfil: 'controle' },
  { path: '/controle/coordenadores', perfil: 'controle' },
  { path: '/controle/plano-formacoes', perfil: 'controle' },
  { path: '/controle/pre-agenda', perfil: 'controle' },
  { path: '/acoes-notificacao', perfil: 'superusuario' },
  { path: '/acoes-notificacao/timeline', perfil: 'superusuario' },
  { path: '/notificacoes-internas', perfil: 'superusuario' },
  { path: '/dat/admin', perfil: 'dat' },
  { path: '/dat/admin/usuarios', perfil: 'dat' },
  { path: '/dat/admin/municipios', perfil: 'dat' },
  { path: '/dat/admin/projetos', perfil: 'dat' },
  { path: '/dat/admin/grupos', perfil: 'dat' },
  { path: '/dat/admin/setores', perfil: 'dat' },
  { path: '/dat/admin/funcoes', perfil: 'dat' },
  { path: '/dat/admin/gerencias', perfil: 'dat' },
  { path: '/dat/admin/produtos', perfil: 'dat' },
  { path: '/dat/admin/projetos-gerais', perfil: 'dat' },
  { path: '/dat/admin/configuracoes', perfil: 'dat' },
  { path: '/dat/admin/colecoes', perfil: 'dat' },
  { path: '/dat/admin/equipe-gerencia', perfil: 'dat' },
  { path: '/dat/cadastros', perfil: 'dat' },
  { path: '/dat/importacoes', perfil: 'dat' },
  { path: '/dat/registros', perfil: 'dat' },
];

/**
 * Paths do AppRoutes que NÃO são medidos, com o destino que cobre cada um.
 * - `redirect`: `<Navigate to=...>`; a tela medida é a do destino.
 * - `alias`: renderiza o MESMO componente de página do destino, com o mesmo
 *   gate e sem ler a URL; medir de novo só dobraria o custo.
 * O teste de cobertura confere as duas afirmações no código do AppRoutes.
 */
export const ROTAS_NAO_MEDIDAS: Readonly<Record<string, { tipo: 'redirect' | 'alias'; destino: string }>> = {
  '/home': { tipo: 'alias', destino: '/' },
  '/compras-materiais': { tipo: 'alias', destino: '/controle/compras' },
  '/dat/compras-materiais': { tipo: 'alias', destino: '/controle/compras' },
  '/pre-agenda': { tipo: 'alias', destino: '/controle/pre-agenda' },
  '/dat/coordenadores': { tipo: 'alias', destino: '/controle/coordenadores' },
  '/aprovacoes': { tipo: 'redirect', destino: '/solicitacoes/aprovacoes' },
  '/disponibilidade': { tipo: 'redirect', destino: '/solicitacoes/disponibilidade' },
  '/bloqueios': { tipo: 'redirect', destino: '/solicitacoes/bloqueios' },
  '/deslocamentos': { tipo: 'redirect', destino: '/solicitacoes/deslocamentos' },
  '/meus-eventos': { tipo: 'redirect', destino: '/solicitacoes/meus-eventos' },
  '/dat/importacao': { tipo: 'redirect', destino: '/dat/importacoes' },
};

/** A tela de login não é rota do AppRoutes (aparece em qualquer URL sem sessão), mas também é medida. */
export const TELA_LOGIN = 'login';

/**
 * DÍVIDA MEDIDA: rota × largura que TEM rolagem horizontal hoje.
 * Chave = `path` de ROTAS_MEDIDAS (ou TELA_LOGIN).
 *
 * Cada combinação listada roda com `test.fail`: o teste passa enquanto a tela
 * ainda rola. Quando um PR do Programa C (C1..C7) conserta a tela, o teste
 * passa a falhar com "Expected to fail, but passed" e obriga a tirar a
 * combinação daqui. A lista só encolhe; o C7 a zera.
 *
 * Medida em 2026-09-29 (main a56d9027, seed com textos longos): 112 combinações
 * em 30 rotas (das 42 medidas). A 1280 px ainda rolam 23; as outras 7 só abaixo disso.
 */
export const PENDENTES: Readonly<Record<string, readonly Largura[]>> = {
  '/dashboards': [360, 768, 1024],
  '/dashboards/compras': [360, 768, 1024, 1280],
  '/dashboards/equipe': [360, 768, 1024, 1280],
  '/dashboards/gcal': [360, 768, 1024],
  '/mapa-brasil': [360, 768, 1024, 1280],
  '/solicitacoes/minhas': [360, 768, 1024, 1280],
  '/solicitacoes/publicacao': [360, 768, 1024, 1280],
  '/solicitacoes/:id/editar': [360, 768],
  '/solicitacoes/aprovacoes': [360, 768, 1024, 1280],
  '/solicitacoes/disponibilidade': [360, 768, 1024],
  '/solicitacoes/bloqueios': [360, 768, 1024, 1280],
  '/solicitacoes/deslocamentos': [360, 768, 1024, 1280],
  '/solicitacoes/meus-eventos': [360, 768, 1024, 1280],
  '/controle/acoes': [360, 768, 1024, 1280],
  '/controle/compras': [360, 768, 1024, 1280],
  '/controle/plano-formacoes': [360, 768, 1024, 1280],
  '/controle/pre-agenda': [360, 768, 1024, 1280],
  '/acoes-notificacao': [360, 768, 1024, 1280],
  '/notificacoes-internas': [360, 768, 1024],
  '/dat/admin/usuarios': [360, 768, 1024, 1280],
  '/dat/admin/municipios': [360, 768, 1024, 1280],
  '/dat/admin/projetos': [360, 768, 1024],
  '/dat/admin/grupos': [360, 768, 1024, 1280],
  '/dat/admin/setores': [360, 768, 1024, 1280],
  '/dat/admin/funcoes': [360, 768, 1024, 1280],
  '/dat/admin/gerencias': [360, 768, 1024, 1280],
  '/dat/admin/produtos': [360, 768, 1024, 1280],
  '/dat/admin/projetos-gerais': [360, 768, 1024],
  '/dat/cadastros': [360, 768, 1024, 1280],
  '/dat/registros': [360, 768, 1024, 1280],
};
