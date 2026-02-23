/**
 * Admin DAT - Importação de Coleções
 *
 * Página para importação em massa de Coleções via CSV/XLSX.
 */

import { Typography } from 'antd';
import { importColecoes } from '../../api/ops';
import ImportUploader from '../../components/ImportUploader';
import type { ValidationResult, ApplyResult } from '../../components/ImportUploader';

const { Title, Text } = Typography;

function toValidationResult(report: Record<string, unknown>): ValidationResult {
  const stats = (report.stats as Record<string, number | undefined>) || {};
  return {
    stats: {
      created: stats.created || 0,
      updated: stats.updated || 0,
      unchanged: stats.unchanged || 0,
    },
    errors: [],
    pendencias: (report.pendencias as Record<string, unknown>) || {},
  };
}

function toApplyResult(report: Record<string, unknown>): ApplyResult {
  const stats = (report.stats as Record<string, number | undefined>) || {};
  return {
    stats: {
      created: stats.created || 0,
      updated: stats.updated || 0,
      unchanged: stats.unchanged || 0,
    },
  };
}

export default function ColecoesImportPage(): JSX.Element {
  return (
    <section className="p-6 bg-gray-50 min-h-screen">
      <header className="mb-6">
        <Title level={2}>Importação de Coleções</Title>
        <Text type="secondary">
          Envie CSV/XLSX com colunas: nome, projeto (obrigatórios), descricao e ativo (opcionais).
        </Text>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ImportUploader
          label="Importar Coleções"
          description="CSV/XLSX de Coleções (nome, projeto, descricao, ativo)"
          onDryRun={async (file: File) => toValidationResult(await importColecoes(file, true) as unknown as Record<string, unknown>)}
          onApply={async (file: File) => toApplyResult(await importColecoes(file, false) as unknown as Record<string, unknown>)}
        />
      </div>
    </section>
  );
}
