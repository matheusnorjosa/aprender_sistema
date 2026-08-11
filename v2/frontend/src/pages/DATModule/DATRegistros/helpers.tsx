/**
 * Helper functions for DATRegistrosPage
 * Issue #303: Split large DATModule pages
 */

import {
  CheckCircleFilled,
  ClockCircleFilled,
  ExclamationCircleFilled,
  MinusCircleFilled,
  CloseCircleFilled,
  QuestionCircleFilled,
} from '@ant-design/icons';

import type { JSX } from "react";

/**
 * Status type for workflow steps (espelha DATRegistro.STATUS_CHOICES + TURMA_STATUS_CHOICES).
 */
export type WorkflowStatus =
  | 'concluido'
  | 'em_andamento'
  | 'pendente'
  | 'nao_aplicavel'
  | 'erro'
  | 'criada';

/**
 * Renders status icon based on status value.
 *
 * M16-08: `erro` DEVE ser visualmente distinto de `nao_aplicavel` — antes ambos caíam no
 * default (minus cinza) e a legenda rotulava o cinza como "Não Aplicável", exibindo uma
 * etapa em ERRO como se não se aplicasse. O default passa a ser um "?" (valor desconhecido),
 * separado do cinza de `nao_aplicavel`.
 */
export function renderStatusIcon(status: string | undefined): JSX.Element {
  switch (status) {
    case 'concluido':
    case 'criada':
      return <CheckCircleFilled className="text-green-500 text-lg" />;
    case 'em_andamento':
      return <ClockCircleFilled className="text-yellow-500 text-lg" />;
    case 'pendente':
      return <ExclamationCircleFilled className="text-red-500 text-lg" />;
    case 'erro':
      return <CloseCircleFilled className="text-red-600 text-lg" />;
    case 'nao_aplicavel':
      return <MinusCircleFilled className="text-gray-400 text-lg" />;
    default:
      return <QuestionCircleFilled className="text-gray-400 text-lg" />;
  }
}
