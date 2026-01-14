/**
 * Página de Grade Mensal de Disponibilidade (Dual).
 *
 * Renderiza duas grades empilhadas: Formadores e Coordenadores.
 * Filtros compartilhados (ano, mês, setor, q).
 * Drawer compartilhado (sabe de qual grade veio a seleção).
 * Export CSV por grade.
 *
 * Design visual atualizado: células maiores, barras coloridas, layout limpo.
 */

import { useState, useMemo } from 'react';
import useMonthlyQuery from './useMonthlyQuery';
import FiltersBar from './FiltersBar';
import Legend from './Legend';
import Grid from './Grid';
import DetailsDrawer from './DetailsDrawer';
import { exportMonthlyCsv } from './exportCsv';

export default function MonthlyPage() {
  // Estado de filtros compartilhados
  const now = new Date();
  const [filters, setFilters] = useState({
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
  const [selected, setSelected] = useState(null);

  /**
   * Handlers de seleção por grade.
   */
  const onSelectFormador = (rowIdx, dayIdx) => {
    setSelected({ role: 'FORMADOR', rowIdx, dayIdx });
  };

  const onSelectCoordenador = (rowIdx, dayIdx) => {
    setSelected({ role: 'COORDENADOR', rowIdx, dayIdx });
  };

  /**
   * Dataset e detalhes baseados na seleção atual.
   */
  const dataset = selected?.role === 'COORDENADOR'
    ? coordenadores.data
    : formadores.data;

  const details = useMemo(() => {
    if (!dataset || !selected) return [];
    const key = `${selected.rowIdx}:${selected.dayIdx}`;
    return dataset.details_index?.[key] ?? [];
  }, [dataset, selected]);

  /**
   * Pessoa e dia selecionados.
   */
  const person = selected && dataset?.people?.[selected.rowIdx];
  const day = selected && dataset?.days?.[selected.dayIdx];

  /**
   * Handler de mudança de filtros.
   */
  const handleFiltersChange = (partial) => {
    setFilters((prev) => ({ ...prev, ...partial }));
  };

  /**
   * Handlers de export CSV.
   */
  const exportFormadores = () => {
    if (!formadores.data) return;
    exportMonthlyCsv({
      ...filters,
      role: 'FORMADOR',
      days: formadores.data.days,
      people: formadores.data.people,
      cells: formadores.data.cells,
    });
  };

  const exportCoordenadores = () => {
    if (!coordenadores.data) return;
    exportMonthlyCsv({
      ...filters,
      role: 'COORDENADOR',
      days: coordenadores.data.days,
      people: coordenadores.data.people,
      cells: coordenadores.data.cells,
    });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="p-6 md:p-10 space-y-6">
        {/* Título */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Grade Mensal de Disponibilidade
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Visualize a disponibilidade mensal de formadores e coordenadores.
            Clique em uma célula para ver detalhes dos eventos.
          </p>
        </div>

        {/* Filtros compartilhados */}
        <FiltersBar
          year={filters.year}
          month={filters.month}
          gerenciaId={filters.gerenciaId}
          sector={filters.sector}
          q={filters.q}
          onChange={handleFiltersChange}
        />

        {/* Legenda */}
        <Legend legend={formadores.data?.legend || coordenadores.data?.legend} />

        {/* Grades */}
        <div className="space-y-6">
            {/* Grade de Formadores */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-900">Formadores</h2>
                {formadores.data && (
                  <button
                    type="button"
                    onClick={exportFormadores}
                    className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
                  >
                    Exportar CSV
                  </button>
                )}
              </div>

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
                    💡 Verifique se o backend está rodando (porta 8002) e se você está autenticado.
                  </p>
                </div>
              ) : formadores.data ? (
                <Grid
                  title="Formadores"
                  year={filters.year}
                  month={filters.month}
                  days={formadores.data.days}
                  people={formadores.data.people}
                  cells={formadores.data.cells}
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
            </div>

            {/* Grade de Coordenadores */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-900">Coordenadores</h2>
                {coordenadores.data && (
                  <button
                    type="button"
                    onClick={exportCoordenadores}
                    className="px-4 py-2 text-sm font-semibold text-white bg-green-600 hover:bg-green-700 rounded-lg transition-colors"
                  >
                    Exportar CSV
                  </button>
                )}
              </div>

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
                    💡 Verifique se o backend está rodando (porta 8002) e se você está autenticado.
                  </p>
                </div>
              ) : coordenadores.data ? (
                <Grid
                  title="Coordenadores"
                  year={filters.year}
                  month={filters.month}
                  days={coordenadores.data.days}
                  people={coordenadores.data.people}
                  cells={coordenadores.data.cells}
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
            </div>
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
    </div>
  );
}
