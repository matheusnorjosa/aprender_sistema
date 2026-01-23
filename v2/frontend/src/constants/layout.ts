/**
 * Layout constants - Centralized dimensions
 *
 * Issue #438: Criar estrutura de constantes frontend
 */

export const LAYOUT = {
  // Sidebar
  SIDEBAR_WIDTH: 250,

  // Input widths
  INPUT_WIDTH_SMALL: 200,
  INPUT_WIDTH_MEDIUM: 300,
  INPUT_WIDTH_LARGE: 400,

  // Dialog/Modal widths
  DIALOG_WIDTH_SMALL: 520,
  DIALOG_WIDTH_MEDIUM: 600,
  DIALOG_WIDTH_LARGE: 800,
  DIALOG_WIDTH_XLARGE: 900,

  // Table scroll widths
  TABLE_SCROLL_SMALL: 800,
  TABLE_SCROLL_MEDIUM: 1000,
  TABLE_SCROLL_LARGE: 1200,
  TABLE_SCROLL_XLARGE: 1400,
} as const;

/** Type for LAYOUT keys */
export type LayoutKey = keyof typeof LAYOUT;
