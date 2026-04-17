/**
 * Barra de filtros compartilhados.
 *
 * Filtros: ano, mês, gerência, setor, busca (q).
 * Sem "role" (controlado pela página principal).
 *
 * RBAC: Filtra gerências baseado nos setores do usuário.
 * - Superintendência vê todas as gerências
 * - Demais usuários veem apenas sua(s) gerência(s)
 */

import { useState, useEffect, useMemo, ChangeEvent, JSX } from 'react';
import { getGerencias, getMe } from '../../api/availability';
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

/**
 * Mapeamento de grupo RBAC para nome_setor da gerência.
 * Necessário porque alguns grupos têm nomes diferentes.
 * Ex: Grupo "Superintendência" -> nome_setor "Super"
 */
const GROUP_TO_NOME_SETOR: Record<string, string> = {
  'Superintendência': 'Super',
  // Os demais têm nomes idênticos (Vidas, Fluir, ACerta, etc.)
};

export default function FiltersBar({ year, month, gerenciaId, sector, q, onChange }: FiltersBarProps): JSX.Element {
  const [allGerencias, setAllGerencias] = useState<Gerencia[]>([]);
  const [userInfo, setUserInfo] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Carrega lista de gerências e info do usuário ao montar
  useEffect(() => {
    async function fetchData(): Promise<void> {
      try {
        const [gerenciasData, meData] = await Promise.all([
          getGerencias() as Promise<Gerencia[]>,
          getMe(),
        ]);
        setAllGerencias(gerenciasData);
        setUserInfo(meData);

        // Auto-seleciona gerência se usuário não é Superintendência
        // e ainda não tem gerência selecionada
        if (!meData.is_superintendencia && meData.setores?.length > 0) {
          const userSetores = meData.setores;
          // Converte grupos RBAC para nome_setor
          const userNomeSetores = userSetores.map(
            (setor) => GROUP_TO_NOME_SETOR[setor] || setor
          );
          // Encontra a primeira gerência que corresponde aos setores do usuário
          const matchingGerencia = gerenciasData.find((g: Gerencia) =>
            userNomeSetores.includes(g.nome_setor)
          );
          if (matchingGerencia && !gerenciaId) {
            onChange({ gerenciaId: matchingGerencia.id });
          }
        }
      } catch (err) {
        logger.error('Erro ao carregar dados:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /**
   * Filtra gerências baseado nos setores do usuário.
   * Superintendência vê todas. Demais veem apenas suas.
   */
  const gerencias = useMemo((): Gerencia[] => {
    if (!userInfo || !allGerencias.length) return [];

    // Superintendência ou superuser vê todas as gerências
    if (userInfo.is_superintendencia || userInfo.is_superuser) {
      return allGerencias;
    }

    // Converte grupos RBAC para nome_setor
    const userSetores = userInfo.setores || [];
    const userNomeSetores = userSetores.map(
      (setor) => GROUP_TO_NOME_SETOR[setor] || setor
    );

    // Filtra gerências que correspondem aos setores do usuário
    return allGerencias.filter((g) =>
      userNomeSetores.includes(g.nome_setor)
    );
  }, [allGerencias, userInfo]);

  /**
   * Verifica se pode ver todas as gerências (opção "Todas").
   */
  const canSeeAll = userInfo?.is_superintendencia || userInfo?.is_superuser;

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
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Gerência
        </label>
        <select
          value={gerenciaId || ''}
          onChange={(e: ChangeEvent<HTMLSelectElement>) => onChange({ gerenciaId: e.target.value ? Number(e.target.value) : null })}
          disabled={loading}
          className="w-52 px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
        >
          {/* Opção "Todas" apenas para Superintendência */}
          {canSeeAll && <option value="">Todas</option>}
          {gerencias.map((g) => (
            <option key={g.id} value={g.id}>
              {g.nome_setor}
            </option>
          ))}
        </select>
      </div>

      {/* Filtro de setor (texto) */}
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Setor
        </label>
        <input
          type="text"
          value={sector}
          onChange={(e: ChangeEvent<HTMLInputElement>) => onChange({ sector: e.target.value })}
          placeholder="Filtrar por setor"
          className="w-40 px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Filtro de busca */}
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Buscar
        </label>
        <input
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
