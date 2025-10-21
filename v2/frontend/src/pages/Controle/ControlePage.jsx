/**
 * Página de Controle - Gestão de Compras e Importações
 *
 * Features:
 * - Upload de arquivos (COMPRAS, AÇÕES, CADASTROS)
 * - Listagem de COMPRAS com filtros
 * - Campos corretos: Data, Município, UF, Projeto, Código, Quant., Uso
 */

import { useState, useEffect } from 'react';
import { importCompras, importAcoes, importCadastros, listCompras } from '../../api/ops';

export default function ControlePage() {
  const [compras, setCompras] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [filters, setFilters] = useState({
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
  const fetchCompras = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await listCompras(filters);
      setCompras(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handler de upload de arquivo.
   *
   * @param {string} type - Tipo: 'compras', 'acoes', 'cadastros'
   * @param {File} file - Arquivo selecionado
   * @param {boolean} dryRun - Se true, apenas preview
   */
  const handleUpload = async (type, file, dryRun = true) => {
    if (!file) {
      alert('Selecione um arquivo');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      let result;

      if (type === 'compras') {
        result = await importCompras(file, dryRun);
      } else if (type === 'acoes') {
        result = await importAcoes(file, dryRun);
      } else if (type === 'cadastros') {
        result = await importCadastros(file, dryRun);
      }

      alert(
        `Importação ${dryRun ? 'simulada' : 'concluída'}!\n\n` +
        `Criados: ${result.stats?.created || 0}\n` +
        `Atualizados: ${result.stats?.updated || 0}\n` +
        `Pulados: ${JSON.stringify(result.stats?.skipped || {})}`
      );

      // Recarregar lista se aplicou mudanças
      if (!dryRun && type === 'compras') {
        await fetchCompras();
      }
    } catch (err) {
      setError(err.message);
      alert(`Erro: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handler de mudança de filtros.
   */
  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  /**
   * Carrega compras ao montar ou quando filtros mudam.
   */
  useEffect(() => {
    fetchCompras();
  }, [filters]);

  return (
    <div className="p-6 space-y-6 bg-gray-50 min-h-screen">
      {/* Título */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Controle</h1>
        <p className="text-sm text-gray-600 mt-1">
          Gestão de compras, ações e importações
        </p>
      </div>

      {/* Cards de Upload */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Upload COMPRAS */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">
            Importar COMPRAS
          </h3>
          <input
            type="file"
            accept=".csv,.xlsx"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleUpload('compras', file, true);
            }}
            className="text-sm"
            disabled={loading}
          />
          <p className="text-xs text-gray-500 mt-2">
            CSV/XLSX com colunas: codigo, produto, quant, municipio, uf, data, uso
          </p>
        </div>

        {/* Upload AÇÕES */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">
            Importar AÇÕES
          </h3>
          <input
            type="file"
            accept=".csv,.xlsx"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleUpload('acoes', file, true);
            }}
            className="text-sm"
            disabled={loading}
          />
          <p className="text-xs text-gray-500 mt-2">
            CSV/XLSX de Ações de Controle
          </p>
        </div>

        {/* Upload CADASTROS */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">
            Importar CADASTROS (DAT)
          </h3>
          <input
            type="file"
            accept=".csv,.xlsx"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleUpload('cadastros', file, true);
            }}
            className="text-sm"
            disabled={loading}
          />
          <p className="text-xs text-gray-500 mt-2">
            CSV/XLSX de Cadastros DAT
          </p>
        </div>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          Filtros de COMPRAS
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <input
            type="text"
            placeholder="Município"
            value={filters.municipio}
            onChange={(e) => handleFilterChange('municipio', e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 rounded"
          />
          <input
            type="text"
            placeholder="Projeto"
            value={filters.projeto}
            onChange={(e) => handleFilterChange('projeto', e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 rounded"
          />
          <input
            type="text"
            placeholder="UF"
            value={filters.uf}
            onChange={(e) => handleFilterChange('uf', e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 rounded"
          />
          <input
            type="date"
            placeholder="De"
            value={filters.from}
            onChange={(e) => handleFilterChange('from', e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 rounded"
          />
          <input
            type="date"
            placeholder="Até"
            value={filters.to}
            onChange={(e) => handleFilterChange('to', e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 rounded"
          />
          <input
            type="text"
            placeholder="Buscar uso/código"
            value={filters.q}
            onChange={(e) => handleFilterChange('q', e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 rounded"
          />
        </div>
      </div>

      {/* Tabela de COMPRAS */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-4 py-3 border-b">
          <h3 className="text-lg font-semibold text-gray-900">
            COMPRAS ({compras.length})
          </h3>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border-b border-red-200">
            <p className="text-sm text-red-800">Erro: {error}</p>
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
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Quant.</th>
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
      </div>
    </div>
  );
}
