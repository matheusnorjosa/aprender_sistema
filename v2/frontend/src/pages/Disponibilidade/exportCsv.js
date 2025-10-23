/**
 * Função para exportar grade mensal para CSV.
 *
 * Exporta matriz de códigos com cabeçalhos de pessoa e dias.
 */

/**
 * Exporta grade mensal para CSV.
 *
 * @param {object} params - Parâmetros da exportação
 * @param {number} params.year - Ano
 * @param {number} params.month - Mês
 * @param {string} params.role - Role (FORMADOR | COORDENADOR)
 * @param {number[]} params.days - Lista de dias do mês
 * @param {Array} params.people - Lista de pessoas
 * @param {string[][]} params.cells - Matriz de códigos
 */
export function exportMonthlyCsv({ year, month, role, days, people, cells }) {
  // Construir CSV
  const rows = [];

  // Header row
  const header = ['Pessoa', ...days.map((d) => `Dia ${d}`)];
  rows.push(header.join(';'));

  // Data rows
  people.forEach((person, rowIdx) => {
    const row = [person.name, ...cells[rowIdx]];
    rows.push(row.join(';'));
  });

  // Criar Blob e download
  const csv = rows.join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = `disponibilidade-${role.toLowerCase()}-${year}-${String(
    month
  ).padStart(2, '0')}.csv`;
  link.click();

  URL.revokeObjectURL(url);
}
