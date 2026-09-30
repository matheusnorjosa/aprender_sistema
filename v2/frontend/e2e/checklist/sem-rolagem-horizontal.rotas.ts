/**
 * Rotas medidas pelos specs `sem-rolagem-horizontal.spec.ts` (360 e 768 px) e
 * `sem-rolagem-horizontal.desktop.spec.ts` (1024 e 1280 px) (Programa C, C0).
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

/**
 * Textos semeados por `seed_frontend_contract_data` (backend) que as telas têm de mostrar.
 * O Vitest confere que cada um existe no seed, para a medição não depender de um texto
 * que o backend deixou de criar.
 */
export const TEXTOS_DO_SEED = {
  municipio: 'Aaa São Sebastião dos Campos Gerais',
  pessoa: 'Aaa Maria Aparecida da Conceição',
  projeto: 'Aaa Alfabetização e Letramento',
  projetoGeral: 'Aaa Alfabetização na Idade Certa',
  produto: 'Aaa Kit Pedagógico de Alfabetização',
  gerencia: 'Aaa Gerência de Formação Continuada',
  grupo: 'Aaa Grupo de Teste de Largura',
  coordenadorDat: 'Aaa Coordenadora Regional Josefa',
  acao: 'Aaa Enviar à secretaria municipal',
  notificacao: 'Prazo da ação se aproxima',
  motivoBloqueio: 'Participação no seminário estadual',
} as const;
const T = TEXTOS_DO_SEED;

/** Prova de que a tela carregou dados: `texto` visível dentro de `em` (seletor CSS em `main`). */
export interface DadosDaTela {
  em: string;
  texto: string;
}

/** Vista alternativa da mesma rota (outra aba, modo lista...), medida com chave própria. */
export interface EstadoDaTela {
  /** Chave em PENDENTES: `${path}#${nome}`. */
  nome: string;
  /** Seletor Playwright do controle que troca a vista. */
  clicar: string;
  dados: DadosDaTela;
}

export interface RotaMedida {
  /** O `path` exatamente como está em AppRoutes.tsx. */
  path: string;
  /** Perfil que consegue abrir a rota (e que vê linhas nas tabelas dela). */
  perfil: Perfil;
  /** Rota com parâmetro: o spec descobre o id pela API antes de navegar. */
  parametro?: 'solicitacaoEditavel';
  /** Título próprio da tela (h1-h5, heading ou título de Card dentro de `main`). */
  marco: string;
  /** Nas telas com tabela ou lista: a linha com o texto do seed. */
  dados?: DadosDaTela;
  estados?: readonly EstadoDaTela[];
}

const LINHA = '.ant-table-row';

export const ROTAS_MEDIDAS: readonly RotaMedida[] = [
  { path: '/', perfil: 'controle', marco: 'Página Inicial' },
  { path: '/dashboards', perfil: 'superusuario', marco: 'Dashboards e Analises', dados: { em: LINHA, texto: T.pessoa } },
  { path: '/dashboards/compras', perfil: 'dat', marco: 'Dashboard de Compras', dados: { em: LINHA, texto: T.municipio } },
  { path: '/dashboards/equipe', perfil: 'dat', marco: 'Dashboard da Equipe', dados: { em: LINHA, texto: T.pessoa } },
  { path: '/dashboards/gcal', perfil: 'controle', marco: 'Dashboard Google Calendar', dados: { em: LINHA, texto: T.municipio } },
  {
    path: '/mapa-brasil',
    perfil: 'superusuario',
    marco: 'Mapa de Eventos',
    dados: { em: LINHA, texto: 'BA' },
    estados: [
      { nome: 'lista', clicar: 'label.ant-radio-button-wrapper:has-text("Lista")', dados: { em: '.ant-list-item', texto: T.municipio } },
    ],
  },
  { path: '/solicitacoes/minhas', perfil: 'coordenador', marco: 'Minhas Solicitações', dados: { em: LINHA, texto: T.municipio } },
  { path: '/solicitacoes/nova', perfil: 'coordenador', marco: 'Nova Solicitação' },
  {
    path: '/solicitacoes/publicacao',
    perfil: 'superusuario',
    marco: 'Publicar na agenda do Google',
    dados: { em: LINHA, texto: T.municipio },
  },
  {
    path: '/solicitacoes/:id/editar',
    perfil: 'coordenador',
    parametro: 'solicitacaoEditavel',
    marco: 'Editar Solicitação',
    dados: { em: 'form', texto: T.pessoa },
  },
  { path: '/solicitacoes/aprovacoes', perfil: 'aprovador', marco: 'Aprovações', dados: { em: LINHA, texto: T.municipio } },
  {
    path: '/solicitacoes/disponibilidade',
    perfil: 'controle',
    marco: 'Grade Mensal de Disponibilidade',
    dados: { em: 'tr', texto: T.pessoa },
  },
  {
    path: '/solicitacoes/bloqueios',
    perfil: 'coordenador',
    marco: 'Gerenciar Disponibilidade',
    dados: { em: LINHA, texto: T.motivoBloqueio },
  },
  { path: '/solicitacoes/deslocamentos', perfil: 'controle', marco: 'Deslocamentos', dados: { em: LINHA, texto: T.municipio } },
  { path: '/solicitacoes/meus-eventos', perfil: 'coordenador', marco: 'Meus Eventos', dados: { em: LINHA, texto: T.municipio } },
  { path: '/perfil', perfil: 'coordenador', marco: 'Meu perfil' },
  { path: '/politica-privacidade', perfil: 'coordenador', marco: 'Política de Privacidade' },
  { path: '/controle', perfil: 'controle', marco: 'Painel de Controle' },
  { path: '/controle/acoes', perfil: 'controle', marco: 'Gestão de Ações', dados: { em: LINHA, texto: T.coordenadorDat } },
  { path: '/controle/compras', perfil: 'controle', marco: 'Gestão de Compras/Materiais', dados: { em: LINHA, texto: T.produto } },
  {
    path: '/controle/coordenadores',
    perfil: 'controle',
    marco: 'Gestão de Coordenadores',
    dados: { em: '.ant-card', texto: T.coordenadorDat },
    estados: [
      { nome: 'lista', clicar: 'button[aria-label="Visualizar como lista"]', dados: { em: LINHA, texto: T.coordenadorDat } },
      {
        nome: 'area',
        clicar: 'button[aria-label="Visualizar por área"]',
        dados: { em: 'section[aria-label="Lista de coordenadores"]', texto: T.coordenadorDat },
      },
    ],
  },
  { path: '/controle/plano-formacoes', perfil: 'controle', marco: 'Plano de Formacoes', dados: { em: LINHA, texto: T.municipio } },
  { path: '/controle/pre-agenda', perfil: 'controle', marco: 'Pré-agenda', dados: { em: LINHA, texto: T.municipio } },
  { path: '/acoes-notificacao', perfil: 'superusuario', marco: 'Ações Internas', dados: { em: LINHA, texto: T.acao } },
  {
    path: '/acoes-notificacao/timeline',
    perfil: 'superusuario',
    marco: 'Timeline das Ações',
    dados: { em: '.ant-timeline-item', texto: T.acao },
  },
  { path: '/notificacoes-internas', perfil: 'superusuario', marco: 'Notificações Internas', dados: { em: LINHA, texto: T.notificacao } },
  { path: '/dat/admin', perfil: 'dat', marco: 'Admin DAT' },
  { path: '/dat/admin/usuarios', perfil: 'dat', marco: 'Usuários', dados: { em: LINHA, texto: T.pessoa } },
  { path: '/dat/admin/municipios', perfil: 'dat', marco: 'Municípios', dados: { em: LINHA, texto: T.municipio } },
  { path: '/dat/admin/projetos', perfil: 'dat', marco: 'Projetos', dados: { em: LINHA, texto: T.projeto } },
  { path: '/dat/admin/grupos', perfil: 'dat', marco: 'Grupos RBAC', dados: { em: LINHA, texto: T.grupo } },
  // Setores e funções listam só os grupos classificados (seed_rbac): não há texto longo a semear.
  { path: '/dat/admin/setores', perfil: 'dat', marco: 'Setores', dados: { em: LINHA, texto: 'Vidas' } },
  { path: '/dat/admin/funcoes', perfil: 'dat', marco: 'Funções', dados: { em: LINHA, texto: 'Coordenador' } },
  { path: '/dat/admin/gerencias', perfil: 'dat', marco: 'Gerencias', dados: { em: LINHA, texto: T.gerencia } },
  { path: '/dat/admin/produtos', perfil: 'dat', marco: 'Produtos', dados: { em: LINHA, texto: T.produto } },
  { path: '/dat/admin/projetos-gerais', perfil: 'dat', marco: 'Projetos Gerais', dados: { em: LINHA, texto: T.projetoGeral } },
  { path: '/dat/admin/configuracoes', perfil: 'dat', marco: 'Configurações do Sistema' },
  { path: '/dat/admin/colecoes', perfil: 'dat', marco: 'Importação de Coleções' },
  { path: '/dat/admin/equipe-gerencia', perfil: 'dat', marco: 'Importação de Vínculos' },
  {
    path: '/dat/cadastros',
    perfil: 'dat',
    marco: 'Gestão de Cadastros em Plataformas',
    dados: { em: LINHA, texto: T.municipio },
  },
  { path: '/dat/importacoes', perfil: 'dat', marco: 'DAT > Importações' },
  { path: '/dat/registros', perfil: 'dat', marco: 'Listagem de Registros DAT', dados: { em: LINHA, texto: T.municipio } },
];

/** Chave de uma medição em PENDENTES: o path, ou `path#estado` para uma vista alternativa. */
export function chaveDe(rota: RotaMedida, estado?: EstadoDaTela): string {
  return estado ? `${rota.path}#${estado.nome}` : rota.path;
}

/**
 * Telas e estados que o spec NÃO mede, com o motivo. É documentação da lacuna: cada item
 * sai daqui quando passar a ser medido (de preferência no PR do Programa C que mexe na tela).
 */
export const NAO_MEDIDOS: Readonly<Record<string, string>> = {
  'Home com outros perfis': 'os cartões da Home mudam por perfil; a rota é medida só com Controle',
  '/controle/plano-formacoes (Calendário e Resumo)': 'placeholders "em desenvolvimento", sem conteúdo',
  '/controle/pre-agenda (modo Google)': 'a tabela de eventos do Google exige OAuth',
  '/solicitacoes/disponibilidade (detalhe do dia)':
    'o drawer abre ao clicar num evento do mês corrente, e o seed não garante evento no mês (C4)',
  '/solicitacoes/nova (passos 2 em diante)': 'exige preencher o formulário do wizard (C3)',
  '/mapa-brasil (municípios do estado clicado)': 'exige clicar numa região do mapa',
  '/dat/cadastros (aba AVALIAR)': 'o seed só tem cadastro FORMAR',
  'ImportUploader depois da validação':
    'exige upload de planilha e validação no backend (importações, coleções, vínculos, municípios)',
  'Modais e drawers de edição': 'o AntD limita a largura do modal; o plano não muda modais',
};

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
 * Medida em 2026-09-29 (main acd04afd, seed com textos longos): 126 combinações em 34
 * chaves (31 das 42 rotas; 3 são vistas alternativas). Rola a página, rola por dentro ou
 * corta sem reticências. A 1280 px (com a barra de rolagem de 15 px) ainda falham 26 chaves.
 * Diferenças só do Linux da CI (fonte) ficam em PENDENTES_SO_LINUX, no fim do arquivo.
 * C1 (30/09/2026): saíram 9 — as 4 de /dat/admin/usuarios (o piloto) e 5 que a sidebar nova
 * liberou (sobreposta abaixo de 992 px dá 250 px a mais a 768; recolhida dá 170 px a mais a
 * 1024): Mapa e Mapa "Lista" a 768, edição de solicitação a 768, Coordenadores "Por área" a
 * 768 e Notificações Internas a 1024. Ficam 117.
 * O ratchet do Vitest (semRolagemHorizontal.pendentes.test.ts) trava a lista: nada novo
 * entra e o tamanho só desce.
 */
export const PENDENTES: Readonly<Record<string, readonly Largura[]>> = {
  '/dashboards': [360, 768, 1024],
  '/dashboards/compras': [360, 768, 1024, 1280],
  '/dashboards/equipe': [360, 768, 1024, 1280],
  '/dashboards/gcal': [360, 768, 1024],
  '/mapa-brasil': [360, 1024, 1280],
  '/mapa-brasil#lista': [360, 1024, 1280],
  '/solicitacoes/minhas': [360, 768, 1024, 1280],
  '/solicitacoes/publicacao': [360, 768, 1024, 1280],
  '/solicitacoes/:id/editar': [360],
  '/solicitacoes/aprovacoes': [360, 768, 1024, 1280],
  '/solicitacoes/disponibilidade': [360, 768, 1024],
  '/solicitacoes/bloqueios': [360, 768, 1024, 1280],
  '/solicitacoes/deslocamentos': [360, 768, 1024, 1280],
  '/solicitacoes/meus-eventos': [360, 768, 1024, 1280],
  '/controle/acoes': [360, 768, 1024, 1280],
  '/controle/compras': [360, 768, 1024, 1280],
  '/controle/coordenadores': [360, 768, 1024, 1280],
  '/controle/coordenadores#lista': [360, 768, 1024, 1280],
  '/controle/coordenadores#area': [360],
  '/controle/plano-formacoes': [360, 768, 1024, 1280],
  '/controle/pre-agenda': [360, 768, 1024, 1280],
  '/acoes-notificacao': [360, 768, 1024, 1280],
  '/notificacoes-internas': [360, 768],
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

/**
 * DÍVIDA MEDIDA SÓ NA REFERÊNCIA: combinações que rolam no Chromium Linux da CI (a medição
 * de referência da trava) e não no Windows. As fontes do Linux (Liberation/DejaVu) são mais
 * largas que a Segoe UI, e estas tabelas passam do limite por poucos px. O spec só as marca
 * como falha esperada quando `process.platform === 'linux'`; no Windows elas passam e não
 * dão "Expected to fail, but passed". Mesmo ratchet de PENDENTES (linha de base e teto), e
 * uma combinação não pode estar nas duas listas.
 */
export const PENDENTES_SO_LINUX: Readonly<Record<string, readonly Largura[]>> = {
  // CI de 29/09/2026 (run 36655341855): Top 5 Coordenadores, rolagem interna +18 px.
  '/dashboards': [1280],
  // CI de 29/09/2026 (run 36655341855): tabela de eventos, rolagem interna +4 px.
  '/dashboards/gcal': [1280],
};
