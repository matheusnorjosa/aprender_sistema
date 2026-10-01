/**
 * O padrão: o ÚNICO arquivo que importa `Table` do AntD para sempre (criado no C1).
 * Isenção permanente, separada da allowlist, que é temporária.
 */
export const TABELA_ANTD_PADRAO = 'src/components/ResponsiveTable.tsx';

/**
 * Allowlist da regra "Table do AntD só via components/ResponsiveTable" (Programa C, C0).
 *
 * Medida em 2026-09-29 pela própria regra, sem allowlist: 27 arquivos importavam
 * `Table` de `antd`; 26 depois do C1 (Usuários, o piloto), 21 depois do C2 (Admin DAT)
 * e 20 depois de Projetos (01/10/2026).
 * SÓ ENCOLHE. Cada PR do Programa C tira os arquivos que migra (o valor diz qual PR). src/test/lint/tabelaAntdRestrita.test.ts mede quem importa
 * Table em src/ e exige que o conjunto seja exatamente esta lista: arquivo novo
 * reprova (use ResponsiveTable) e entrada que já não importa também (tire-a daqui).
 *
 * Dados puros: importado pelo eslint.config.js e pelo teste (o Vitest não carrega
 * o eslint.config.js direto).
 *
 * @type {Readonly<Record<string, string>>}
 */
export const TABELA_ANTD_ALLOWLIST = {
  'src/components/MyBlocksTable.tsx': 'C3 — Bloqueios',
  'src/pages/Aprovacoes/ApprovalsPage.tsx': 'C3 — Aprovações',
  'src/pages/Deslocamentos/DeslocamentosPage.tsx': 'C3 — Deslocamentos',
  'src/pages/MeusEventos/MeusEventosPage.tsx': 'C3 — Meus eventos',
  'src/pages/Solicitacoes/MySolicitacoesPage.tsx': 'C3 — Minhas solicitações',
  'src/pages/Solicitacoes/PublicacaoSetorPage.tsx': 'C3 — Publicação',
  'src/pages/Controle/AcoesNotificacaoPage.tsx': 'C5 — Notificações',
  'src/pages/Controle/NotificacoesInternasPage.tsx': 'C5 — Notificações',
  'src/pages/DATModule/AcoesPage.tsx': 'C5 — Ações',
  'src/pages/DATModule/CadastrosPage.tsx': 'C5 — Cadastros',
  'src/pages/DATModule/ComprasPage.tsx': 'C5 — Compras',
  'src/pages/DATModule/CoordenadoresPage.tsx': 'C5 — Coordenadores',
  'src/pages/PreAgenda/PreAgendaPage.tsx': 'C5 — Pré-agenda',
  'src/pages/DATModule/DATRegistrosPage.tsx': 'C6 — Registros DAT (matriz, decisão 2)',
  'src/pages/DATModule/PlanoFormacoesPage.tsx': 'C6 — Plano de formações (matriz, decisão 2)',
  'src/pages/Dashboards/ComprasDashboardPage.tsx': 'C7 — dashboards',
  'src/pages/Dashboards/DashboardsPage.tsx': 'C7 — dashboards',
  'src/pages/Dashboards/EquipeDashboardPage.tsx': 'C7 — dashboards',
  'src/pages/Dashboards/GCalDashboardPage.tsx': 'C7 — dashboards',
  'src/pages/MapaBrasil/MapaBrasilPage.tsx': 'C7 — mapa',
};
