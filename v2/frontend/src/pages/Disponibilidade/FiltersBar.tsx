/**
 * Barra de filtros compartilhados.
 *
 * Filtros: ano, mês, gerência, projeto, busca (q).
 * Sem "role" (controlado pela página principal).
 *
 * Gerência (PR A — mesma regra do backend, `CanViewAllAvailability | HasSectorAccess`):
 * - Policy `view_all_availability`: "Participantes de projetos SUPER" + gerências ativas.
 * - Demais: só as gerências do vínculo EquipeGerencia (`me.gerencias`); a primeira é
 *   selecionada sozinha. Grupo de setor NÃO conta (o backend autoriza por vínculo).
 * - Sem vínculo e sem policy: select desabilitado ("Sem gerência vinculada").
 */

import { useState, useEffect, useMemo, ChangeEvent, JSX } from 'react';
import { getGerencias, getMe } from '../../api/availability';
import { getMyPolicies } from '../../api/me';
import type { ID, CurrentUser, Gerencia } from '../../types';
import logger from '../../utils/logger';

/** Filters change partial type */
interface FiltersChangeType {
  year?: number;
  month?: number;
  gerenciaId?: ID | null;
  sector?: string;
  q?: string;
}

interface FiltersBarProps {
  year: number;
  month: number;
  gerenciaId: ID | null;
  sector: string;
  q: string;
  onChange: (partial: FiltersChangeType) => void;
}

/** Opções do select de gerência (id + rótulo de tela). */
interface GerenciaOpcao {
  id: ID;
  rotulo: string;
}

const porRotulo = (a: GerenciaOpcao, b: GerenciaOpcao): number => a.rotulo.localeCompare(b.rotulo, 'pt-BR');

export default function FiltersBar({ year, month, gerenciaId, sector, q, onChange }: FiltersBarProps): JSX.Element {
  const [allGerencias, setAllGerencias] = useState<Gerencia[]>([]);
  const [userInfo, setUserInfo] = useState<CurrentUser | null>(null);
  const [canSeeAll, setCanSeeAll] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  // Carrega gerências ativas, usuário e policies ao montar
  useEffect(() => {
    async function fetchData(): Promise<void> {
      try {
        const [gerenciasData, meData, policies] = await Promise.all([
          getGerencias({ ativo: true }),
          getMe(),
          getMyPolicies().catch(() => [] as string[]),
        ]);
        setAllGerencias(gerenciasData);
        setUserInfo(meData);
        const veTodas = policies.includes('view_all_availability');
        setCanSeeAll(veTodas);

        // Sem a policy, a Grade só abre na gerência do vínculo: seleciona a primeira.
        const primeira = [...(meData.gerencias ?? [])].sort(porRotulo)[0];
        if (!veTodas && primeira && !gerenciaId) {
          onChange({ gerenciaId: primeira.id });
        }
      } catch (err) {
        logger.error('Erro ao carregar dados:', err);
      } finally {
        setLoading(false);
      }
    }
    void fetchData();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /** Com a policy: todas as ativas. Sem ela: só as do vínculo (`me.gerencias`). */
  const gerencias = useMemo((): GerenciaOpcao[] => {
    if (!userInfo) return [];
    const opcoes: GerenciaOpcao[] = canSeeAll ? allGerencias : (userInfo.gerencias ?? []);
    return [...opcoes].sort(porRotulo);
  }, [allGerencias, userInfo, canSeeAll]);

  const semOpcoes = !loading && !canSeeAll && gerencias.length === 0;

  /**
   * Incrementa/decrementa mês.
   */
  const bump = (delta: number): void => {
    const dt = new Date(year, month - 1, 1);
    dt.setMonth(dt.getMonth() + delta);
    onChange({ year: dt.getFullYear(), month: dt.getMonth() + 1 });
  };

  return (
    <div className="flex flex-wrap items-end gap-3 p-4 bg-white rounded-lg shadow-sm">
      {/* Navegação mês/ano */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => bump(-1)}
          className="px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded border border-gray-300"
        >
          &larr;
        </button>
        <div className="px-3 py-2 font-semibold text-gray-900">
          {String(month).padStart(2, '0')}/{year}
        </div>
        <button
          type="button"
          onClick={() => bump(1)}
          className="px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded border border-gray-300"
        >
          &rarr;
        </button>
      </div>

      {/* Filtro de gerência */}
      <div>
        <label htmlFor="filtersbar-gerencia" className="block text-xs font-medium text-gray-700 mb-1">
          Gerência
        </label>
        <select
          id="filtersbar-gerencia"
          value={gerenciaId || ''}
          onChange={(e: ChangeEvent<HTMLSelectElement>) => onChange({ gerenciaId: e.target.value ? Number(e.target.value) : null })}
          disabled={loading || semOpcoes}
          className="w-52 px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
        >
          {/* Sem gerência escolhida a grade mostra os participantes de projetos SUPER
              (monthly_grid_service) — decisão 3 do dono: o rótulo diz isso. */}
          {canSeeAll && <option value="">Participantes de projetos SUPER</option>}
          {semOpcoes && <option value="">Sem gerência vinculada</option>}
          {gerencias.map((g) => (
            <option key={g.id} value={g.id}>
              {g.rotulo}
            </option>
          ))}
        </select>
      </div>

      {/* Filtro por nome do projeto (texto) — o backend filtra `projeto__nome` */}
      <div>
        <label htmlFor="filtersbar-setor" className="block text-xs font-medium text-gray-700 mb-1">
          Projeto
        </label>
        <input
          id="filtersbar-setor"
          type="text"
          value={sector}
          onChange={(e: ChangeEvent<HTMLInputElement>) => onChange({ sector: e.target.value })}
          placeholder="Filtrar por projeto"
          className="w-40 px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Filtro de busca */}
      <div>
        <label htmlFor="filtersbar-buscar" className="block text-xs font-medium text-gray-700 mb-1">
          Buscar
        </label>
        <input
          id="filtersbar-buscar"
          type="text"
          value={q}
          onChange={(e: ChangeEvent<HTMLInputElement>) => onChange({ q: e.target.value })}
          placeholder="Buscar nome/email"
          className="w-48 px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
    </div>
  );
}
