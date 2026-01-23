/**
 * Helper functions for CadastrosPage
 * Issue #303: Split large DATModule pages
 */

import {
  CheckCircleFilled,
  ClockCircleFilled,
  ExclamationCircleFilled,
  MinusCircleFilled,
} from '@ant-design/icons';
import type { Etapa } from './constants';

/**
 * Status type for workflow steps
 */
export type WorkflowStatus = 'concluido' | 'em_andamento' | 'pendente' | 'na';

/**
 * Ant Design Steps status type
 */
export type StepsStatus = 'finish' | 'process' | 'wait' | 'error';

/**
 * Cadastro record interface (partial, for helper functions)
 */
export interface CadastroRecord {
  [key: string]: unknown;
}

/**
 * Renders status icon based on status value
 * @param status - Status value (concluido, em_andamento, pendente, na)
 * @returns Icon component with appropriate color
 */
export function renderStatusIcon(status: string | undefined): JSX.Element {
  switch (status) {
    case 'concluido':
      return <CheckCircleFilled className="text-green-500 text-lg" />;
    case 'em_andamento':
      return <ClockCircleFilled className="text-yellow-500 text-lg" />;
    case 'pendente':
      return <ExclamationCircleFilled className="text-red-500 text-lg" />;
    case 'na':
      return <MinusCircleFilled className="text-gray-400 text-lg" />;
    default:
      return <MinusCircleFilled className="text-gray-400 text-lg" />;
  }
}

/**
 * Maps status to Ant Design Steps status
 * @param status - Status value
 * @returns Steps status (finish, process, wait)
 */
export function getStepStatus(status: string | undefined): StepsStatus {
  switch (status) {
    case 'concluido':
      return 'finish';
    case 'em_andamento':
      return 'process';
    case 'pendente':
      return 'wait';
    default:
      return 'wait';
  }
}

/**
 * Calculate current step index based on completed etapas
 * @param record - Cadastro record
 * @param etapas - Array of etapa definitions
 * @returns Current step index
 */
export function getCurrentStep(record: CadastroRecord, etapas: Etapa[]): number {
  for (let i = 0; i < etapas.length; i++) {
    const status = record[`status_${etapas[i].key}`];
    if (status !== 'concluido') {
      return i;
    }
  }
  return etapas.length;
}
