/**
 * Selectors - Playwright E2E Tests
 *
 * Centraliza todos os selectors CSS/XPath usados nos testes.
 * Facilita manutenção quando UI muda.
 *
 * Fase 2 - Plano DAT/GCal 2025-10-29
 */

export const selectors = {
  /**
   * Autenticação (Login/Logout)
   */
  auth: {
    usernameInput: 'input[name="username"], input[type="text"]',
    passwordInput: 'input[name="password"], input[type="password"]',
    submitButton: 'button[type="submit"], button:has-text("Entrar")',
    logoutButton: 'button:has-text("Sair"), button:has-text("Logout")',
    appLogo: 'text=AS v2, text=Aprender Sistema',
  },

  /**
   * Navegação principal
   */
  nav: {
    menuSolicitacoes: 'a[href*="/solicitacoes"]',
    menuAprovacoes: 'a[href="/aprovacoes"]',
    menuPreAgenda: 'a[href="/pre-agenda"]',
    menuAdminDAT: 'a[href="/admin-dat"]',
  },

  /**
   * Solicitações - Nova Solicitação
   */
  solicitacao: {
    novaButton: 'a[href="/solicitacoes/nova"], button:has-text("Nova Solicitação")',
    projetoSelect: 'select[name="projeto_id"], select[name="projeto"]',
    municipioSelect: 'select[name="municipio_id"], select[name="municipio"]',
    formadorSelect: 'select[name="formador_id"], select[name="formador"], select[name="usuario_id"]',
    tituloInput: 'input[name="titulo"], textarea[name="titulo"]',
    descricaoTextarea: 'textarea[name="descricao"]',
    dataInicioInput: 'input[name="data_inicio"], input[name="inicio"]',
    dataFimInput: 'input[name="data_fim"], input[name="fim"]',
    isOnlineCheckbox: 'input[name="is_online"], input[type="checkbox"][name="online"]',
    submitButton: 'button[type="submit"], button:has-text("Salvar"), button:has-text("Criar")',
    cancelButton: 'button:has-text("Cancelar")',
  },

  /**
   * Aprovações - Superintendência
   */
  aprovacoes: {
    table: 'table, .ant-table',
    solicitacaoRow: (id: string | number) => `tr[data-solicitacao-id="${id}"], tr:has-text("${id}")`,
    aprovarButton: 'button:has-text("Aprovar")',
    reprovarButton: 'button:has-text("Reprovar")',
    justificativaTextarea: 'textarea[name="justificativa"], textarea[placeholder*="justificativa"]',
    confirmarButton: 'button:has-text("Confirmar"), .ant-modal button:has-text("OK")',
    successMessage: 'text=/aprovada com sucesso/i, .ant-message-success',
  },

  /**
   * Pré-Agenda - Controle
   */
  preAgenda: {
    table: 'table, .ant-table',
    solicitacaoRow: (id: string | number) => `tr[data-solicitacao-id="${id}"], tr:has-text("${id}")`,
    previewButton: 'button:has-text("Preview"), button:has-text("Visualizar")',
    publishButton: 'button:has-text("Publicar"), button:has-text("Publish")',
    confirmarPublishButton: '.ant-modal button:has-text("Confirmar"), .ant-modal button:has-text("Sim")',
    successMessage: 'text=/publicada com sucesso/i, .ant-message-success',
    previewModal: '.ant-modal:visible',
    previewPayload: '.ant-modal pre, .ant-modal code, [data-testid="gcal-preview-payload"]',
  },

  /**
   * Modais genéricos
   */
  modal: {
    visible: '.ant-modal:visible',
    title: '.ant-modal-title',
    content: '.ant-modal-body',
    okButton: '.ant-modal-footer button:has-text("OK"), .ant-modal-footer .ant-btn-primary',
    cancelButton: '.ant-modal-footer button:has-text("Cancelar"), .ant-modal-footer .ant-btn-default',
    closeIcon: '.ant-modal-close',
  },

  /**
   * Mensagens de feedback
   */
  messages: {
    success: '.ant-message-success, [class*="success"]',
    error: '.ant-message-error, [class*="error"]',
    warning: '.ant-message-warning, [class*="warning"]',
    info: '.ant-message-info, [class*="info"]',
  },

  /**
   * Tabelas genéricas
   */
  table: {
    container: 'table, .ant-table',
    row: 'tr, .ant-table-row',
    cell: 'td, .ant-table-cell',
    headerCell: 'th, .ant-table-thead th',
    emptyText: '.ant-table-placeholder, .ant-empty',
  },

  /**
   * Formulários genéricos
   */
  form: {
    input: 'input',
    textarea: 'textarea',
    select: 'select, .ant-select',
    checkbox: 'input[type="checkbox"]',
    radio: 'input[type="radio"]',
    submitButton: 'button[type="submit"]',
    resetButton: 'button[type="reset"]',
  },
};

/**
 * Helper para criar selector de row de tabela por ID.
 *
 * @param id - ID da solicitação/entidade
 * @returns Selector string
 */
export function rowByIdSelector(id: string | number): string {
  return `tr[data-solicitacao-id="${id}"], tr[data-id="${id}"], tr:has-text("${id}")`;
}

/**
 * Helper para criar selector de botão por texto.
 *
 * @param text - Texto do botão
 * @returns Selector string
 */
export function buttonByTextSelector(text: string): string {
  return `button:has-text("${text}"), a:has-text("${text}")`;
}
