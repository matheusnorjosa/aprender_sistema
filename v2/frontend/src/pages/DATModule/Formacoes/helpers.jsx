/**
 * Helper functions for FormacoesPage
 * Issue #303: Split large DATModule pages
 */

import { Tag } from 'antd';
import { STATUS_OPTIONS, MODALIDADE_OPTIONS } from './constants';

/**
 * Renders a status tag with appropriate color
 * @param {string} status - Status value
 * @returns {JSX.Element} Tag component
 */
export function renderStatusTag(status) {
  const statusConfig = STATUS_OPTIONS.find((s) => s.value === status);
  return <Tag color={statusConfig?.color || 'default'}>{statusConfig?.label || status}</Tag>;
}

/**
 * Renders a modalidade tag with icon
 * @param {string} modalidade - Modalidade value
 * @returns {JSX.Element} Tag component
 */
export function renderModalidadeTag(modalidade) {
  const modalidadeConfig = MODALIDADE_OPTIONS.find((m) => m.value === modalidade);
  return (
    <Tag icon={modalidadeConfig?.icon}>
      {modalidadeConfig?.label || modalidade}
    </Tag>
  );
}
