export interface FunctionalMatrixUser {
  username: string;
  password: string;
}

export interface FunctionalMatrixAssertion {
  field: string;
  endpoint: string;
  selector: string;
  expectedText: string;
}

export interface FunctionalMatrixCase {
  id: string;
  route: string;
  user: FunctionalMatrixUser;
  endpoints: string[];
  assertions: FunctionalMatrixAssertion[];
}

/**
 * Matriz funcional crítica (issue #705).
 *
 * Cada caso conecta:
 * - rota crítica
 * - endpoint(s) esperado(s)
 * - campo(s) renderizados que provam hidratação correta
 */
export const FUNCTIONAL_CRITICAL_MATRIX: FunctionalMatrixCase[] = [
  {
    id: 'controle-compras-core-compra',
    route: '/controle/compras',
    user: { username: 'controle_e2e@test.com', password: 'testpass123' },
    endpoints: ['/api/dat/compras-materiais/'],
    assertions: [
      {
        field: 'Tabela de compras exibe código importado',
        endpoint: '/api/dat/compras-materiais/',
        selector: 'table',
        expectedText: 'MATRIX-PEND-001',
      },
      {
        field: 'Tabela de compras exibe município esperado',
        endpoint: '/api/dat/compras-materiais/',
        selector: 'table',
        expectedText: 'Matrizopolis',
      },
    ],
  },
  {
    id: 'dashboard-compras-pendencias',
    route: '/dashboards/compras',
    user: { username: 'dat_matrix@test.com', password: 'testpass123' },
    endpoints: ['/api/dat/compras-materiais/dashboard/', '/api/dat/compras-materiais/pendencias/'],
    assertions: [
      {
        field: 'Seção de pendências renderiza título',
        endpoint: '/api/dat/compras-materiais/pendencias/',
        selector: 'section',
        expectedText: 'Municípios pendentes de agendamento',
      },
      {
        field: 'Tabela de pendências exibe município esperado',
        endpoint: '/api/dat/compras-materiais/pendencias/',
        selector: 'table',
        expectedText: 'Matrizopolis',
      },
      {
        field: 'Gráfico Top Produtos mostra item da matriz',
        endpoint: '/api/dat/compras-materiais/dashboard/',
        selector: 'section',
        expectedText: 'KIT MATRIX CONTRACT',
      },
    ],
  },
];
