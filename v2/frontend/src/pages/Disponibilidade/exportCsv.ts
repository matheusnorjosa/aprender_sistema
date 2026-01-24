/**
 * Função para exportar grade mensal para CSV.
 *
 * Exporta matriz de códigos com cabeçalhos de pessoa e dias.
 */

/**
 * Person data for CSV export
 * Using a generic type to accept any object with a name property
 */
interface PersonData {
  name: string;
}

/**
 * Parameters for monthly CSV export
 */
interface ExportMonthlyCsvParams {
  year: number;
  month: number;
  role: string;
  days: number[];
  people: PersonData[];
  cells: string[][];
}

/**
 * Exporta grade mensal para CSV.
 *
 * @param params - Parâmetros da exportação
 * @param params.year - Ano
 * @param params.month - Mês
 * @param params.role - Role (FORMADOR | COORDENADOR)
 * @param params.days - Lista de dias do mês
 * @param params.people - Lista de pessoas
 * @param params.cells - Matriz de códigos
 */
export function exportMonthlyCsv({
  year,
  month,
  role,
  days,
  people,
  cells,
}: ExportMonthlyCsvParams): void {
  // Construir CSV
  const rows: string[] = [];

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
