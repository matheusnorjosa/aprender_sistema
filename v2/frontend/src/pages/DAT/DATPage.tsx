/**
 * Página DAT - Gestão de CADASTROS
 *
 * Features:
 * - Upload de CADASTROS (import-cadastros)
 * - Listagem de CADASTROS com filtros
 */

import { useState, useEffect, useCallback, ChangeEvent, JSX } from 'react';
import { importCadastros, listCadastros } from '../../api/ops';
import ImportUploader from '../../components/ImportUploader';
import type { ID } from '../../types';

/** Record type for cadastro entries */
interface CadastroRecord {
  id: ID;
  data_registro: string;
  municipio: string;
  projeto: string;
  tipo_acao: string;
  responsavel: string;
  observacao: string;
}

/** Filters type */
interface FiltersType {
  q: string;
}

export default function DATPage(): JSX.Element {
  const [cadastros, setCadastros] = useState<CadastroRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [filters, setFilters] = useState<FiltersType>({
    q: '',
  });

  /**
   * Carrega lista de cadastros.
   */
  const fetchCadastros = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await listCadastros(filters as unknown as Record<string, string>);
      setCadastros(data as unknown as CadastroRecord[]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  /**
   * Handler de mudança de filtros.
   */
  const handleFilterChange = (key: keyof FiltersType, value: string): void => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  /**
   * Callback após apply bem-sucedido.
   */
  const handleAfterApply = (): void => {
    // Recarregar lista de cadastros
    fetchCadastros();
  };

  /**
   * Carrega cadastros ao montar ou quando filtros mudam.
   */
  useEffect(() => {
    fetchCadastros();
  }, [fetchCadastros]);

  return (
    <div className="p-6 space-y-6 bg-gray-50 min-h-screen">
      {/* Título */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">DAT</h1>
        <p className="text-sm text-gray-600 mt-1">
          Gestão de cadastros DAT
        </p>
      </div>

      {/* Card de Upload */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ImportUploader
          label="Importar CADASTROS"
          description="CSV/XLSX de Cadastros DAT (Município, Projeto, Tipo de Ação, Responsável, Data, Observação)"
          onDryRun={((file: File) => importCadastros(file, true)) as unknown as (file: File) => Promise<{ valid: boolean; errors?: string[] }>}
          onApply={(async (file: File) => {
            const result = await importCadastros(file, false);
            handleAfterApply();
            return result;
          }) as unknown as (file: File) => Promise<{ created?: number; updated?: number; errors?: string[] }>}
        />
      </div>

      {/* Filtros de CADASTROS */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          Filtros de CADASTROS
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input
            type="text"
            placeholder="Buscar (município, projeto, responsável, observação)"
            value={filters.q}
            onChange={(e: ChangeEvent<HTMLInputElement>) => handleFilterChange('q', e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Tabela de CADASTROS */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-4 py-3 border-b">
          <h3 className="text-lg font-semibold text-gray-900">
            CADASTROS ({cadastros.length})
          </h3>
        </div>

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
        ) : cadastros.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-500">Nenhum cadastro encontrado.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Data</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Município</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Projeto</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Tipo</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Responsável</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-700">Observação</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {cadastros.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">{r.data_registro}</td>
                    <td className="px-4 py-3">{r.municipio}</td>
                    <td className="px-4 py-3">{r.projeto}</td>
                    <td className="px-4 py-3">{r.tipo_acao}</td>
                    <td className="px-4 py-3">{r.responsavel}</td>
                    <td className="px-4 py-3 text-xs text-gray-600">{r.observacao}</td>
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
