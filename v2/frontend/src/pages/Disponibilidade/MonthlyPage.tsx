/**
 * Página de Grade Mensal de Disponibilidade (Dual).
 *
 * Renderiza duas grades empilhadas: Formadores e Coordenadores.
 * Filtros compartilhados (ano, mês, setor, q).
 * Drawer compartilhado (sabe de qual grade veio a seleção).
 *
 * Design visual atualizado: células maiores, barras coloridas, layout limpo.
 *
 * Sem rolagem horizontal (C4, decisão do dono): abaixo de 1280 px (a mesma quebra da sidebar,
 * `useResponsive`), as duas grades mostram a mesma semana, com ‹ › dentro do mês; a partir de
 * 1280 px, o mês inteiro.
 */

import { useState, useMemo, JSX } from 'react';
import dayjs from 'dayjs';
import { FORTALEZA_TZ } from '../../utils/datetime';
import useMonthlyQuery from './useMonthlyQuery';
import SyncIndicator from '../../components/SyncIndicator';
import AvisoAtualizacaoPausada from '../../components/AvisoAtualizacaoPausada';
import FiltersBar from './FiltersBar';
import Legend from './Legend';
import Grid from './Grid';
import DetailsDrawer from './DetailsDrawer';
import { rotuloSemana, semanaInicial, semanasDoMes } from './semanas';
import { useResponsive } from '../../hooks/useResponsive';
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

/** Semana escolhida nas setas, válida só no mês da `chave` (`ano-mês`). */
interface SemanaEscolhida {
  chave: string;
  indice: number;
}

const BOTAO_SEMANA =
  'px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded border border-gray-300 ' +
  'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 ' +
  'aria-disabled:opacity-50 aria-disabled:cursor-not-allowed aria-disabled:hover:bg-gray-100';

/** Selection type */
interface SelectionType {
  role: 'FORMADOR' | 'COORDENADOR';
  rowIdx: number;
  dayIdx: number;
}

export default function MonthlyPage(): JSX.Element {
  // Estado de filtros compartilhados
  const now = dayjs().tz(FORTALEZA_TZ); // mês de hoje em Fortaleza, como a semana inicial
  const [filters, setFilters] = useState<FiltersType>({
    year: now.year(),
    month: now.month() + 1,
    gerenciaId: null, // null = Superintendência (default)
    sector: '',
    q: '',
  });

  // Queries para ambas as grades
  const formadores = useMonthlyQuery({ ...filters, role: 'FORMADOR' });
  const coordenadores = useMonthlyQuery({ ...filters, role: 'COORDENADOR' });

  // Estado de seleção (sabe de qual grade veio)
  const [selected, setSelected] = useState<SelectionType | null>(null);

  // Semana ou mês inteiro. As duas grades são do mesmo mês: os mesmos dias.
  const mesInteiro = useResponsive().modo === 'aberta';
  const days = formadores.data?.days ?? coordenadores.data?.days;
  const semanas = useMemo(
    () => semanasDoMes(filters.year, filters.month, days ?? []),
    [filters.year, filters.month, days],
  );
  const chaveMes = `${filters.year}-${filters.month}`;
  const [semanaEscolhida, setSemanaEscolhida] = useState<SemanaEscolhida | null>(null);
  // Mês trocado: volta à semana inicial sem efeito, porque a escolha guardada é de outro mês.
  const indiceSemana = Math.min(
    semanaEscolhida?.chave === chaveMes
      ? semanaEscolhida.indice
      : semanaInicial(filters.year, filters.month, days ?? [], semanas),
    Math.max(semanas.length - 1, 0),
  );
  const semanaAtual = semanas[indiceSemana] ?? [];
  const diasVisiveis = mesInteiro ? (days ?? []).map((_, idx) => idx) : semanaAtual;
  const primeiraSemana = indiceSemana === 0;
  const ultimaSemana = indiceSemana >= semanas.length - 1;
  const irParaSemana = (indice: number): void => setSemanaEscolhida({ chave: chaveMes, indice });

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

  // Falha ao atualizar com a grade na tela (uma mensagem só para as duas grades).
  const erroAtualizacao = formadores.erroAtualizacao ?? coordenadores.erroAtualizacao;

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
              loading={formadores.loading || formadores.atualizando}
              onRefresh={formadores.refetch}
            />
          </div>
        </header>

        {(formadores.pollingPausado || coordenadores.pollingPausado) && <AvisoAtualizacaoPausada />}

        {erroAtualizacao && (
          <div role="alert" className="bg-yellow-50 border border-yellow-300 rounded-lg p-4 text-sm text-yellow-900">
            Não foi possível atualizar a grade: {erroAtualizacao} O que está na tela pode estar
            desatualizado; a próxima atualização automática tenta de novo.
          </div>
        )}

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

        {/* Semana mostrada (abaixo de 1280 px) */}
        {!mesInteiro && semanaAtual.length > 0 && (
          <div role="group" aria-label="Semana mostrada" className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              aria-label="Semana anterior"
              aria-disabled={primeiraSemana}
              onClick={() => !primeiraSemana && irParaSemana(indiceSemana - 1)}
              className={BOTAO_SEMANA}
            >
              &lsaquo;
            </button>
            <span aria-live="polite" className="px-3 py-2 font-semibold text-gray-900">
              Semana: {rotuloSemana(filters.month, semanaAtual.map((idx) => days?.[idx] ?? 0))}
            </span>
            <button
              type="button"
              aria-label="Próxima semana"
              aria-disabled={ultimaSemana}
              onClick={() => !ultimaSemana && irParaSemana(indiceSemana + 1)}
              className={BOTAO_SEMANA}
            >
              &rsaquo;
            </button>
          </div>
        )}

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
                  <button
                    type="button"
                    aria-label="Tentar de novo: carregar os formadores"
                    aria-disabled={formadores.atualizando}
                    onClick={() => !formadores.atualizando && void formadores.refetch()}
                    className={`${BOTAO_SEMANA} mt-3`}
                  >
                    Tentar de novo
                  </button>
                </div>
              ) : formadores.data ? (
                <Grid
                  title="Formadores"
                  year={filters.year}
                  month={filters.month}
                  days={formadores.data.days}
                  diasVisiveis={diasVisiveis}
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
                  <button
                    type="button"
                    aria-label="Tentar de novo: carregar os coordenadores"
                    aria-disabled={coordenadores.atualizando}
                    onClick={() => !coordenadores.atualizando && void coordenadores.refetch()}
                    className={`${BOTAO_SEMANA} mt-3`}
                  >
                    Tentar de novo
                  </button>
                </div>
              ) : coordenadores.data ? (
                <Grid
                  title="Coordenadores"
                  year={filters.year}
                  month={filters.month}
                  days={coordenadores.data.days}
                  diasVisiveis={diasVisiveis}
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
