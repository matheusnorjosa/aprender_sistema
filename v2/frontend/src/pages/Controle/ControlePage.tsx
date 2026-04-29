/**
 * Página de Controle - Gestão de COMPRAS e AÇÕES
 *
 * Features:
 * - Listagem de COMPRAS com filtros
 * - Aviso de centralização de importações em DAT > Importações
 * - Campos corretos: Data, Município, UF, Projeto, Código, Quant., Uso
 */

import { useState, useEffect, useCallback, ChangeEvent } from 'react';
import { listCompras } from '../../api/ops';
import type { Compra, ComprasFilters } from '../../api/ops';
import DatImportsCentralizedBanner from '../../components/DatImportsCentralizedBanner';

export default function ControlePage(): JSX.Element {
  const [compras, setCompras] = useState<Compra[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [filters, setFilters] = useState<ComprasFilters>({
    municipio: '',
    projeto: '',
    uf: '',
    from: '',
    to: '',
    q: '',
  });

  /**
   * Carrega lista de compras.
   */
  const fetchCompras = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await listCompras(filters);
      setCompras(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  /**
   * Handler de mudança de filtros.
   */
  const handleFilterChange = (key: keyof ComprasFilters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  /**
   * Carrega compras ao montar ou quando filtros mudam.
   */
  useEffect(() => {
    fetchCompras();
  }, [fetchCompras]);

  return (
    <main className="p-6 space-y-6 bg-gray-50 min-h-screen" aria-labelledby="controle-title">
      {/* Título */}
      <header>
        <h1 id="controle-title" className="text-3xl font-bold text-gray-900">Controle</h1>
        <p className="text-sm text-gray-600 mt-1">
          Gestão de compras e ações de controle
        </p>
      </header>

      <DatImportsCentralizedBanner />

      {/* Filtros de COMPRAS */}
      <section aria-label="Filtros de compras" className="bg-white rounded-lg shadow p-4">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">
          Filtros de COMPRAS
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <input
            type="text"
            placeholder="Município"
            value={filters.municipio}
            onChange={(e: ChangeEvent<HTMLInputElement>) => handleFilterChange('municipio', e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="text"
            placeholder="Projeto"
            value={filters.projeto}
            onChange={(e: ChangeEvent<HTMLInputElement>) => handleFilterChange('projeto', e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="text"
            placeholder="UF"
            value={filters.uf}
            onChange={(e: ChangeEvent<HTMLInputElement>) => handleFilterChange('uf', e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="date"
            placeholder="De"
            value={filters.from}
            onChange={(e: ChangeEvent<HTMLInputElement>) => handleFilterChange('from', e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="date"
            placeholder="Até"
            value={filters.to}
            onChange={(e: ChangeEvent<HTMLInputElement>) => handleFilterChange('to', e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="text"
            placeholder="Buscar uso/código"
            value={filters.q}
            onChange={(e: ChangeEvent<HTMLInputElement>) => handleFilterChange('q', e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </section>

      {/* Tabela de COMPRAS */}
      <section aria-label="Tabela de compras" className="bg-white rounded-lg shadow overflow-hidden">
        <header className="px-4 py-3 border-b">
          <h2 className="text-lg font-semibold text-gray-900">
            COMPRAS ({compras.length})
          </h2>
        </header>

        {error && (
          <div className="p-4 bg-red-50 border-b border-red-200">
            <p className="text-sm text-red-800">Erro: {error}</p>
            <p className="text-xs text-red-600 mt-1">
              Verifique se o backend está rodando e se você está autenticado.
            </p>
          </div>
        )}

        {loading ? (
          <div className="p-8 text-center">
            <p className="text-gray-500">Carregando...</p>
          </div>
        ) : compras.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-500">Nenhuma compra encontrada.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Data</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Município</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">UF</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Projeto</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Código</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Quantidade</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Uso</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {compras.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">{r.data}</td>
                    <td className="px-4 py-3">{r.municipio}</td>
                    <td className="px-4 py-3">{r.uf}</td>
                    <td className="px-4 py-3">{r.projeto}</td>
                    <td className="px-4 py-3">{r.codigo}</td>
                    <td className="px-4 py-3">{r.quantidade}</td>
                    <td className="px-4 py-3">{r.uso}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
