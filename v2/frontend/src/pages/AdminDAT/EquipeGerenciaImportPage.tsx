/**
 * Admin DAT - Importação de Vínculos (EquipeGerência)
 *
 * Página para importação em massa de vínculos usuário↔setor.
 */

import { Typography } from 'antd';
import { importEquipeGerencia } from '../../api/ops';
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

export default function EquipeGerenciaImportPage(): JSX.Element {
  return (
    <section className="p-6 bg-gray-50 min-h-screen">
      <header className="mb-6">
        <Title level={2}>Importação de Vínculos (EquipeGerência)</Title>
        <Text type="secondary">
          CSV/XLSX com colunas: setor/gerencia, papel, usuario_cpf/email/nome.
          Para papel APOIO, incluir coordenador_supervisor.
        </Text>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ImportUploader
          label="Importar Vínculos (EquipeGerência)"
          description="CSV/XLSX de Vínculos (setor, papel, usuario_cpf/email/nome, coordenador_supervisor)"
          onDryRun={async (file: File) => toValidationResult(await importEquipeGerencia(file, true) as unknown as Record<string, unknown>)}
          onApply={async (file: File) => toApplyResult(await importEquipeGerencia(file, false) as unknown as Record<string, unknown>)}
        />
      </div>
    </section>
  );
}
