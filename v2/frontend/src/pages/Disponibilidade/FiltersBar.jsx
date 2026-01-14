/**
 * Barra de filtros compartilhados.
 *
 * Filtros: ano, mês, gerência, setor, busca (q).
 * Sem "role" (controlado pela página principal).
 */

import { useState, useEffect } from 'react';
import { getGerencias } from '../../api/availability';

export default function FiltersBar({ year, month, gerenciaId, sector, q, onChange }) {
  const [gerencias, setGerencias] = useState([]);
  const [loadingGerencias, setLoadingGerencias] = useState(true);

  // Carrega lista de gerências ao montar
  useEffect(() => {
    async function fetchGerencias() {
      try {
        const data = await getGerencias();
        setGerencias(data);
      } catch (err) {
        console.error('Erro ao carregar gerências:', err);
      } finally {
        setLoadingGerencias(false);
      }
    }
    fetchGerencias();
  }, []);

  /**
   * Incrementa/decrementa mês.
   *
   * @param {number} delta - Delta de meses (-1 ou +1)
   */
  const bump = (delta) => {
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
          ←
        </button>
        <div className="px-3 py-2 font-semibold text-gray-900">
          {String(month).padStart(2, '0')}/{year}
        </div>
        <button
          type="button"
          onClick={() => bump(1)}
          className="px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded border border-gray-300"
        >
          →
        </button>
      </div>

      {/* Filtro de gerência */}
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Gerência
        </label>
        <select
          value={gerenciaId || ''}
          onChange={(e) => onChange({ gerenciaId: e.target.value ? Number(e.target.value) : null })}
          disabled={loadingGerencias}
          className="w-52 px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
        >
          <option value="">Todas (Superintendência)</option>
          {gerencias.map((g) => (
            <option key={g.id} value={g.id}>
              {g.nome}
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
          onChange={(e) => onChange({ sector: e.target.value })}
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
          onChange={(e) => onChange({ q: e.target.value })}
          placeholder="Buscar nome/email"
          className="w-48 px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
    </div>
  );
}
