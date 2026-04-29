/**
 * Tests da página /dat/importacoes (PR-B do plano DAT-Imports, 2026-04-29).
 *
 * Cobertura:
 * - Header com título canônico
 * - 3 categorias renderizadas (Cadastros base, Operacional, Disponibilidade)
 * - 11 cards de upload (cada um com label esperado)
 *
 * Não cobre (escopo de outros PRs):
 * - Guard `canDAT` na rota (PR-B só configura — guard é validado em
 *   testes de AppRoutes, padrão de PR 11/12 do programa hardening RBAC)
 * - Lógica de upload em si (já coberta pelos testes de `ImportUploader`)
 * - Backend gate de cada endpoint (PR-A1 cobre)
 */

import { render, screen, within } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

import ImportacoesPage from '../ImportacoesPage';

// Mock dos imports — não fazem fetch real durante render
vi.mock('../../../api/ops', () => ({
  importAcoes: vi.fn(),
  importBloqueios: vi.fn(),
  importCadastros: vi.fn(),
  importColecoes: vi.fn(),
  importCompras: vi.fn(),
  importDeslocamentos: vi.fn(),
  importEquipeGerencia: vi.fn(),
  importEventos: vi.fn(),
  importMunicipios: vi.fn(),
  importProdutos: vi.fn(),
  importUsuarios: vi.fn(),
}));

describe('ImportacoesPage — DAT > Importações (PR-B)', () => {
  test('renderiza header canônico', () => {
    render(<ImportacoesPage />);
    expect(
      screen.getByRole('heading', { level: 2, name: /DAT.*Importações/i }),
    ).toBeInTheDocument();
  });

  test('renderiza 3 categorias com títulos corretos', () => {
    render(<ImportacoesPage />);
    expect(screen.getByRole('heading', { level: 3, name: 'Cadastros base' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 3, name: 'Operacional' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 3, name: 'Disponibilidade' })).toBeInTheDocument();
  });

  test('Cadastros base contém 5 cards (Usuários, Municípios, Coleções, Cadastros DAT, Vínculos)', () => {
    render(<ImportacoesPage />);
    const section = screen.getByRole('region', { name: 'Cadastros base' });
    expect(within(section).getByText(/Importar USUÁRIOS/)).toBeInTheDocument();
    expect(within(section).getByText(/Importar MUNICÍPIOS/)).toBeInTheDocument();
    expect(within(section).getByText(/Importar COLEÇÕES/)).toBeInTheDocument();
    expect(within(section).getByText(/Importar CADASTROS DAT/)).toBeInTheDocument();
    expect(within(section).getByText(/Importar VÍNCULOS/)).toBeInTheDocument();
  });

  test('Operacional contém 4 cards (Compras, Ações, Eventos, Produtos)', () => {
    render(<ImportacoesPage />);
    const section = screen.getByRole('region', { name: 'Operacional' });
    expect(within(section).getByText(/Importar COMPRAS/)).toBeInTheDocument();
    expect(within(section).getByText(/Importar AÇÕES/)).toBeInTheDocument();
    expect(within(section).getByText(/Importar EVENTOS/)).toBeInTheDocument();
    expect(within(section).getByText(/Importar PRODUTOS/)).toBeInTheDocument();
  });

  test('Disponibilidade contém 2 cards (Bloqueios, Deslocamentos)', () => {
    render(<ImportacoesPage />);
    const section = screen.getByRole('region', { name: 'Disponibilidade' });
    expect(within(section).getByText(/Importar BLOQUEIOS/)).toBeInTheDocument();
    expect(within(section).getByText(/Importar DESLOCAMENTOS/)).toBeInTheDocument();
  });

  test('total de 11 cards de import (5 + 4 + 2)', () => {
    render(<ImportacoesPage />);
    // Cada card tem um label começando com "Importar X".
    const cardLabels = screen.getAllByText(/^Importar [A-Z]/);
    expect(cardLabels).toHaveLength(11);
  });
});
