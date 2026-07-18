/**
 * SEC-007: Neutralização de CSV formula injection (frontend).
 *
 * Espelha o contrato do backend (`apps/core/utils/csv_sanitize.py`): uma célula
 * que começa com `= + - @ TAB CR LF` é executada como fórmula ao abrir o CSV em
 * Excel, LibreOffice ou Google Sheets. Prefixamos `'` para neutralizar.
 *
 * Aspas NÃO neutralizam fórmula (só resolvem delimitação de campo), por isso o
 * prefixo `'` é aplicado ANTES de qualquer quoting.
 */

// Mesmos 7 caracteres e mesma âncora `^` do backend (_FORMULA_CHARS).
const FORMULA_CHARS = /^[=+\-@\t\r\n]/;

/**
 * Sanitiza uma célula: prefixa `'` quando o valor começa com um gatilho de
 * fórmula. Números, texto benigno e null/undefined passam como string simples.
 */
export function sanitizeCsvCell(value: string | number | null | undefined): string {
  const s = String(value ?? '');
  if (FORMULA_CHARS.test(s)) {
    return `'${s}`;
  }
  return s;
}

/**
 * Monta uma linha CSV sanitizando cada célula e depois aplicando quoting RFC-4180
 * (aspas duplas com doubling) quando a célula resultante contém o separador,
 * aspas ou quebra de linha.
 *
 * ORDEM OBRIGATÓRIA: sanitizar (prefixo `'`) ANTES de quotar.
 */
export function buildCsvRow(
  cells: Array<string | number | null | undefined>,
  sep = ';',
): string {
  return cells
    .map((cell) => {
      const sanitized = sanitizeCsvCell(cell);
      const needsQuoting =
        sanitized.includes(sep) ||
        sanitized.includes('"') ||
        sanitized.includes('\n') ||
        sanitized.includes('\r');
      if (needsQuoting) {
        return `"${sanitized.replace(/"/g, '""')}"`;
      }
      return sanitized;
    })
    .join(sep);
}
