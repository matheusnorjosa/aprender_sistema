/**
 * Página de Grade Mensal de Disponibilidade (Dual).
 *
 * Renderiza duas grades empilhadas: Formadores e Coordenadores.
 * Filtros compartilhados (ano, mês, setor, q).
 * Drawer compartilhado (sabe de qual grade veio a seleção).
 *
 * Design visual atualizado: células maiores, barras coloridas, layout limpo.
 */

import { useState, useMemo, JSX } from 'react';
import useMonthlyQuery from './useMonthlyQuery';
import SyncIndicator from '../../components/SyncIndicator';
import FiltersBar from './FiltersBar';
import Legend from './Legend';
import Grid from './Grid';
import DetailsDrawer from './DetailsDrawer';
import type { ID } from '../../types';
import type { PersonType, EventDetailType } from './DetailsDrawer';

/** Filters type */
interface FiltersType {
  year: number;
  month: number;
  gerenciaId: ID | null;
  sector: string;
  q: string;
}

/** Selection type */
interface SelectionType {
  role: 'FORMADOR' | 'COORDENADOR';
  rowIdx: number;
  dayIdx: number;
}

export default function MonthlyPage(): JSX.Element {
  // Estado de filtros compartilhados
  const now = new Date();
  const [filters, setFilters] = useState<FiltersType>({
    year: now.getFullYear(),
    month: now.getMonth() + 1,
    gerenciaId: null, // null = Superintendência (default)
    sector: '',
    q: '',
  });

  // Queries para ambas as grades
  const formadores = useMonthlyQuery({ ...filters, role: 'FORMADOR' });
  const coordenadores = useMonthlyQuery({ ...filters, role: 'COORDENADOR' });

  // Estado de seleção (sabe de qual grade veio)
  const [selected, setSelected] = useState<SelectionType | null>(null);

  /**
   * Handlers de seleção por grade.
   */
  const onSelectFormador = (rowIdx: number, dayIdx: number): void => {
    setSelected({ role: 'FORMADOR', rowIdx, dayIdx });
  };

  const onSelectCoordenador = (rowIdx: number, dayIdx: number): void => {
    setSelected({ role: 'COORDENADOR', rowIdx, dayIdx });
  };

  /**
   * Dataset e detalhes baseados na seleção atual.
   */
  const dataset = selected?.role === 'COORDENADOR'
    ? coordenadores.data
    : formadores.data;

  const details = useMemo((): EventDetailType[] => {
    if (!dataset || !selected) return [];
    const key = `${selected.rowIdx}:${selected.dayIdx}`;
    return (dataset.details_index?.[key] as EventDetailType[] | undefined) ?? [];
  }, [dataset, selected]);

  /**
   * Pessoa e dia selecionados.
   */
  const person: PersonType | null = selected && dataset?.people?.[selected.rowIdx]
    ? { ...dataset.people[selected.rowIdx] } as PersonType
    : null;
  const day: number | null = (selected && dataset?.days?.[selected.dayIdx]) ?? null;

  /**
   * Handler de mudança de filtros.
   */
  const handleFiltersChange = (partial: Partial<FiltersType>): void => {
    setFilters((prev) => ({ ...prev, ...partial }));
  };

  return (
    <section className="min-h-screen bg-gray-50" aria-labelledby="grade-mensal-title">
      <div className="p-6 md:p-10 space-y-6">
        {/* Header semantico */}
        <header>
          <h1 id="grade-mensal-title" className="text-3xl font-bold text-gray-900">
            Grade Mensal de Disponibilidade
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Visualize a disponibilidade mensal de formadores e coordenadores.
            Clique em uma célula para ver detalhes dos eventos.
          </p>
          <div className="mt-2">
            <SyncIndicator
              lastUpdated={formadores.lastUpdated}
              loading={formadores.loading}
              onRefresh={formadores.refetch}
            />
          </div>
        </header>

        {/* Filtros compartilhados */}
        <nav aria-label="Filtros da grade">
          <FiltersBar
            year={filters.year}
            month={filters.month}
            gerenciaId={filters.gerenciaId}
            sector={filters.sector}
            q={filters.q}
            onChange={handleFiltersChange}
          />
        </nav>

        {/* Legenda */}
        <aside aria-label="Legenda de cores">
          <Legend legend={formadores.data?.legend || coordenadores.data?.legend} />
        </aside>

        {/* Grades */}
        <div className="space-y-6">
            {/* Grade de Formadores */}
            <article aria-labelledby="formadores-heading">
              <header className="mb-4">
                <h2 id="formadores-heading" className="text-xl font-semibold text-gray-900">Formadores</h2>
              </header>

              {formadores.loading ? (
                <div className="bg-white rounded-lg shadow-sm p-8 text-center">
                  <div className="text-gray-500">Carregando...</div>
                </div>
              ) : formadores.error ? (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <p className="text-sm text-red-800 font-medium mb-2">
                    Erro ao carregar formadores
                  </p>
                  <p className="text-xs text-red-700">
                    {formadores.error}
                  </p>
                  <p className="text-xs text-red-600 mt-3">
                    Verifique se o backend está rodando (porta 8002) e se você está autenticado.
                  </p>
                </div>
              ) : formadores.data ? (
                <Grid
                  title="Formadores"
                  year={filters.year}
                  month={filters.month}
                  days={formadores.data.days}
                  people={formadores.data.people}
                  cells={formadores.data.cells as ('' | 'E' | '2' | 'P' | 'T' | 'X' | 'D' | 'D1')[][]}
                  detailsIndex={formadores.data.details_index || {}}
                  onSelect={onSelectFormador}
                  selected={
                    selected?.role === 'FORMADOR'
                      ? { rowIdx: selected.rowIdx, dayIdx: selected.dayIdx }
                      : null
                  }
                />
              ) : (
                <div className="bg-white rounded-lg shadow-sm p-8 text-center">
                  <p className="text-sm text-gray-500">
                    Nenhum dado disponível.
                  </p>
                </div>
              )}
            </article>

            {/* Grade de Coordenadores */}
            <article aria-labelledby="coordenadores-heading">
              <header className="mb-4">
                <h2 id="coordenadores-heading" className="text-xl font-semibold text-gray-900">Coordenadores</h2>
              </header>

              {coordenadores.loading ? (
                <div className="bg-white rounded-lg shadow-sm p-8 text-center">
                  <div className="text-gray-500">Carregando...</div>
                </div>
              ) : coordenadores.error ? (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <p className="text-sm text-red-800 font-medium mb-2">
                    Erro ao carregar coordenadores
                  </p>
                  <p className="text-xs text-red-700">
                    {coordenadores.error}
                  </p>
                  <p className="text-xs text-red-600 mt-3">
                    Verifique se o backend está rodando (porta 8002) e se você está autenticado.
                  </p>
                </div>
              ) : coordenadores.data ? (
                <Grid
                  title="Coordenadores"
                  year={filters.year}
                  month={filters.month}
                  days={coordenadores.data.days}
                  people={coordenadores.data.people}
                  cells={coordenadores.data.cells as ('' | 'E' | '2' | 'P' | 'T' | 'X' | 'D' | 'D1')[][]}
                  detailsIndex={coordenadores.data.details_index || {}}
                  onSelect={onSelectCoordenador}
                  selected={
                    selected?.role === 'COORDENADOR'
                      ? { rowIdx: selected.rowIdx, dayIdx: selected.dayIdx }
                      : null
                  }
                />
              ) : (
                <div className="bg-white rounded-lg shadow-sm p-8 text-center">
                  <p className="text-sm text-gray-500">
                    Nenhum dado disponível.
                  </p>
                </div>
              )}
            </article>
        </div>
      </div>

      {/* Drawer compartilhado */}
      <DetailsDrawer
        open={!!selected}
        onClose={() => setSelected(null)}
        person={person}
        day={day}
        details={details}
      />
    </section>
  );
}
