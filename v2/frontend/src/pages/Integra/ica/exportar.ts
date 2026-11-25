/**
 * Exportação das telas da Integra: planilha (CSV) e PDF (impressão do navegador).
 *
 * CSV para o Excel em português:
 * - começa com o BOM UTF-8 (sem ele, o Excel quebra os acentos);
 * - separador ";" e decimal com vírgula;
 * - texto passa pelo `sanitizeCsvCell` do projeto (SEC-007): célula que começa com = + - @ TAB CR LF
 *   ganha uma aspa simples na frente e não vira fórmula. Número não passa pelo sanitizador: não carrega
 *   fórmula, e o negativo (-3) continuaria sendo número no Excel.
 *
 * PDF: `imprimirPagina()` abre a impressão do navegador; o `impressao.css` tira o menu, o cabeçalho e
 * as faixas de filtro (classe `print:hidden`) e mantém a faixa "DADOS SIMULADOS".
 */
import { sanitizeCsvCell } from '../../../utils/csvSanitize';

import './impressao.css';

export type CelulaCsv = string | number | null | undefined;

const SEPARADOR = ';';

/**
 * Primeira linha de todo CSV da Integra, e prefixo de todo nome de arquivo: a planilha anexada a um
 * e-mail ou aberta no Excel não pode passar por exportação real do sistema.
 */
const AVISO_SIMULADO =
  'DADOS SIMULADOS: pessoas fictícias e números gerados na tela, mas os municípios são reais e os tempos de deslocamento são as estimativas do relatório da Coordenação Pedagógica. Nada foi gravado.';
const PREFIXO_ARQUIVO = 'SIMULADO_';

function celula(valor: CelulaCsv): string {
  const texto = typeof valor === 'number' ? String(valor).replace('.', ',') : sanitizeCsvCell(valor);
  const precisaDeAspas = /[;"\r\n]/.test(texto);
  return precisaDeAspas ? `"${texto.replace(/"/g, '""')}"` : texto;
}

/** O texto do CSV: BOM, aviso de dados simulados, cabeçalho e linhas, separados por ";" e quebrados com CRLF. */
export function montarCsv(cabecalho: readonly string[], linhas: ReadonlyArray<readonly CelulaCsv[]>): string {
  const corpo = [[AVISO_SIMULADO], cabecalho, ...linhas].map((linha) => linha.map(celula).join(SEPARADOR)).join('\r\n');
  return `﻿${corpo}`;
}

/** Baixa o CSV com o nome dado e `SIMULADO_` na frente (ex.: `SIMULADO_ica_por_gerencia.csv`). */
export function baixarCsv(
  nomeArquivo: string,
  cabecalho: readonly string[],
  linhas: ReadonlyArray<readonly CelulaCsv[]>,
): void {
  const blob = new Blob([montarCsv(cabecalho, linhas)], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const ancora = document.createElement('a');
  ancora.href = url;
  ancora.download = `${PREFIXO_ARQUIVO}${nomeArquivo}`;
  ancora.click();
  URL.revokeObjectURL(url);
}

/** Abre a impressão do navegador; dali a pessoa escolhe "Salvar como PDF". */
export function imprimirPagina(): void {
  window.print();
}
