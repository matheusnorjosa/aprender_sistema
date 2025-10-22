/**
 * Componente Reutilizável para Upload de Importação.
 *
 * Permite selecionar arquivo, executar dry-run (preview) e apply (persistir).
 * Exibe relatório JSON do backend com stats e pendências.
 */

import { useState } from 'react';

export default function ImportUploader({ label, onDryRun, onApply, description }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Handler genérico para dry-run ou apply.
   *
   * @param {string} action - 'dry' ou 'apply'
   */
  async function handle(action) {
    if (!file) {
      alert('Selecione um arquivo primeiro');
      return;
    }

    setBusy(true);
    setError(null);

    try {
      const report = await (action === 'dry' ? onDryRun(file) : onApply(file));
      setPreview(report);

      // Se aplicou, mostrar mensagem de sucesso
      if (action === 'apply') {
        alert(
          `Importação concluída!\n\n` +
          `Criados: ${report.stats?.created || 0}\n` +
          `Atualizados: ${report.stats?.updated || 0}\n` +
          `Inalterados: ${report.stats?.unchanged || 0}`
        );
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="border rounded p-4 space-y-3 bg-white shadow">
      {/* Label */}
      <div className="font-semibold text-gray-900">{label}</div>

      {/* Description */}
      {description && (
        <p className="text-xs text-gray-500">{description}</p>
      )}

      {/* File input */}
      <input
        type="file"
        accept=".csv,.xlsx"
        onChange={(e) => {
          const selectedFile = e.target.files?.[0] || null;
          setFile(selectedFile);
          setPreview(null); // Limpar preview anterior
          setError(null);
        }}
        className="block w-full text-sm text-gray-900 border border-gray-300 rounded cursor-pointer bg-gray-50 focus:outline-none"
      />

      {/* Buttons */}
      <div className="flex gap-2">
        <button
          type="button"
          className="px-3 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={!file || busy}
          onClick={() => handle('dry')}
        >
          {busy ? 'Processando...' : 'Dry-run (Preview)'}
        </button>
        <button
          type="button"
          className="px-3 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={!file || busy}
          onClick={() => handle('apply')}
        >
          {busy ? 'Processando...' : 'Apply (Persistir)'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded">
          <p className="text-sm text-red-800 font-medium">Erro</p>
          <p className="text-xs text-red-700 mt-1">{error}</p>
        </div>
      )}

      {/* Preview */}
      {preview && (
        <div className="p-3 bg-gray-50 border border-gray-200 rounded">
          <p className="text-sm font-medium text-gray-900 mb-2">
            Relatório {preview.dry_run ? '(Dry-run)' : '(Aplicado)'}
          </p>

          {/* Stats */}
          {preview.stats && (
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-600">Criados:</span>
                <span className="font-semibold text-green-700">{preview.stats.created || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Atualizados:</span>
                <span className="font-semibold text-blue-700">{preview.stats.updated || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Inalterados:</span>
                <span className="font-semibold text-gray-700">{preview.stats.unchanged || 0}</span>
              </div>
            </div>
          )}

          {/* Pendências */}
          {preview.pendencias && Object.keys(preview.pendencias).length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-medium text-yellow-800 mb-1">Pendências:</p>
              <pre className="text-[10px] text-yellow-700 bg-yellow-50 p-2 rounded overflow-x-auto">
                {JSON.stringify(preview.pendencias, null, 2)}
              </pre>
            </div>
          )}

          {/* JSON completo (colapsado) */}
          <details className="mt-3">
            <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-900">
              Ver JSON completo
            </summary>
            <pre className="text-[10px] text-gray-700 bg-white p-2 rounded overflow-x-auto mt-2 border">
              {JSON.stringify(preview, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}
