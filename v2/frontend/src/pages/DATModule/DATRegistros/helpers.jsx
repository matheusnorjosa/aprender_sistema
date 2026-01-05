/**
 * Helper functions for DATRegistrosPage
 * Issue #303: Split large DATModule pages
 */

import {
  CheckCircleFilled,
  ClockCircleFilled,
  ExclamationCircleFilled,
  MinusCircleFilled,
} from '@ant-design/icons';

/**
 * Renders status icon based on status value
 * @param {string} status - Status value (concluido, em_andamento, pendente)
 * @returns {JSX.Element} Icon component with appropriate color
 */
export function renderStatusIcon(status) {
  switch (status) {
    case 'concluido':
      return <CheckCircleFilled className="text-green-500 text-lg" />;
    case 'em_andamento':
      return <ClockCircleFilled className="text-yellow-500 text-lg" />;
    case 'pendente':
      return <ExclamationCircleFilled className="text-red-500 text-lg" />;
    default:
      return <MinusCircleFilled className="text-gray-400 text-lg" />;
  }
}
