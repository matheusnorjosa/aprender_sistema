/**
 * Shared inline styles - §14 Epic #459
 *
 * Consolidates commonly repeated inline styles across the application.
 * Use these constants instead of inline style objects to improve consistency
 * and reduce re-renders caused by object recreation.
 */

import type { CSSProperties } from 'react';

/** Style object type helper */
type StyleMap<K extends string> = Record<K, CSSProperties>;

// Status indicator styles
export const STATUS_STYLES: StyleMap<'disabled' | 'inactive'> = {
  disabled: {
    opacity: 0.6,
  },
  inactive: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
};

// Card styles
export const CARD_STYLES: StyleMap<'noPadding' | 'smallPadding' | 'modalBody'> = {
  noPadding: { padding: 0 },
  smallPadding: { padding: 8 },
  modalBody: {
    maxHeight: 'calc(100vh - 250px)',
    overflowY: 'auto',
  },
};

// Text styles
export const TEXT_STYLES: StyleMap<'small' | 'tiny' | 'code' | 'label' | 'ellipsis'> = {
  small: { fontSize: 11 },
  tiny: { fontSize: 10 },
  code: { fontSize: 11, fontFamily: 'monospace' },
  label: { fontSize: 12, textTransform: 'uppercase' },
  ellipsis: { whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' },
};

// Spacing styles
export const SPACING_STYLES: StyleMap<'marginLeft8' | 'marginRight8' | 'marginTop4' | 'marginTop8' | 'marginBottom4' | 'tightDivider' | 'normalDivider'> = {
  marginLeft8: { marginLeft: 8 },
  marginRight8: { marginRight: 8 },
  marginTop4: { marginTop: 4 },
  marginTop8: { marginTop: 8 },
  marginBottom4: { marginBottom: 4 },
  tightDivider: { margin: '8px 0' },
  normalDivider: { margin: '12px 0' },
};

// Color styles for common status colors
export const COLOR_STYLES: StyleMap<'success' | 'warning' | 'error' | 'info' | 'primary' | 'muted'> = {
  success: { color: '#52c41a' },
  warning: { color: '#faad14' },
  error: { color: '#ff4d4f' },
  info: { color: '#1890ff' },
  primary: { color: '#006B52' },
  muted: { color: '#999' },
};

// Border styles
export const BORDER_STYLES: StyleMap<'accentYellow' | 'accentGreen' | 'accentBlue'> = {
  accentYellow: { color: '#faad14', borderColor: '#faad14' },
  accentGreen: { color: '#52c41a', borderColor: '#52c41a' },
  accentBlue: { color: '#1890ff', borderColor: '#1890ff' },
};

// Width styles
export const WIDTH_STYLES: StyleMap<'full' | 'half' | 'fixed200' | 'fixed300'> = {
  full: { width: '100%' },
  half: { width: '50%' },
  fixed200: { width: 200 },
  fixed300: { width: 300 },
};

// Container styles
export const CONTAINER_STYLES: StyleMap<'centerText' | 'centerPadded' | 'flexBetween' | 'flexEnd' | 'flexGap'> = {
  centerText: { textAlign: 'center' },
  centerPadded: { textAlign: 'center', padding: 40 },
  flexBetween: { display: 'flex', justifyContent: 'space-between' },
  flexEnd: { display: 'flex', justifyContent: 'flex-end' },
  flexGap: { display: 'flex', gap: 8 },
};

// Page container style
export const PAGE_CONTAINER_STYLE: CSSProperties = {
  minHeight: 'calc(100vh - 64px)',
};
