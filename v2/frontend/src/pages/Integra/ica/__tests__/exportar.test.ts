/**
 * Exportação das tabelas da Integra: CSV para o Excel (BOM UTF-8, separador ";", decimal com vírgula)
 * sem injeção de fórmula, e a impressão do navegador (PDF).
 */
import { afterEach, describe, expect, test, vi } from 'vitest';

import { baixarCsv, imprimirPagina, montarCsv } from '../exportar';

const BOM = '﻿';
const AVISO = 'DADOS SIMULADOS: pessoas fictícias e números gerados na tela. Nada foi gravado.';

/** As linhas do CSV depois do BOM e do aviso: do cabeçalho em diante. */
const semAviso = (csv: string): string[] => csv.slice(1).split('\r\n').slice(1);

describe('montarCsv', () => {
  test('começa com o BOM UTF-8 e o aviso de dados simulados, separa com ";" e quebra linha com CRLF', () => {
    const csv = montarCsv(['Município', 'UF'], [['Petrolina', 'PE'], ['Milagres', 'CE']]);
    expect(csv.startsWith(BOM)).toBe(true);
    expect(csv.slice(1)).toBe(`${AVISO}\r\nMunicípio;UF\r\nPetrolina;PE\r\nMilagres;CE`);
  });

  test('texto que começa com = + - @ TAB ou CR vira texto (aspa simples na frente)', () => {
    const csv = montarCsv(['Nome'], [['=1+1'], ['+55'], ['-x'], ['@SOMA(A1)'], ['\tx'], ['\rx']]);
    const linhas = semAviso(csv);
    expect(linhas.slice(1, 5)).toEqual(["'=1+1", "'+55", "'-x", "'@SOMA(A1)"]);
    expect(linhas[5]).toBe("'\tx");
    // CR é gatilho e também pede aspas (quebra de linha dentro da célula).
    expect(csv).toContain('"\'\rx"');
  });

  test('número sai com vírgula decimal e o negativo continua número (sem aspa simples)', () => {
    const csv = montarCsv(['ICA', 'Variação'], [[168.5, -3], [100, 0]]);
    expect(semAviso(csv)).toEqual(['ICA;Variação', '168,5;-3', '100;0']);
  });

  test('célula com ";", aspas ou quebra de linha vai entre aspas (aspas dobradas)', () => {
    const csv = montarCsv(['Texto'], [['a;b'], ['disse "oi"'], ['linha 1\nlinha 2']]);
    expect(semAviso(csv).slice(1, 3)).toEqual(['"a;b"', '"disse ""oi"""']);
    expect(csv).toContain('"linha 1\nlinha 2"');
  });

  test('vazio e nulo viram célula vazia', () => {
    expect(semAviso(montarCsv(['A', 'B', 'C'], [[null, undefined, '']]))).toEqual(['A;B;C', ';;']);
  });
});

describe('baixarCsv', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('baixa um arquivo .csv com o conteúdo montado e SIMULADO_ na frente do nome', async () => {
    const criar = vi.fn((_blob: Blob) => 'blob:teste');
    const liberar = vi.fn();
    Object.assign(URL, { createObjectURL: criar, revokeObjectURL: liberar });
    const clicar = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);

    baixarCsv('ica_por_gerencia.csv', ['Gerência'], [['Gerência 1']]);

    expect(clicar).toHaveBeenCalledTimes(1);
    const ancora = clicar.mock.contexts[0] as HTMLAnchorElement;
    expect(ancora.download).toBe('SIMULADO_ica_por_gerencia.csv');
    expect(ancora.href).toBe('blob:teste');
    const blob = criar.mock.calls[0]?.[0] as Blob;
    expect(blob.type).toBe('text/csv;charset=utf-8');
    const bytes = await new Promise<ArrayBuffer>((resolver) => {
      const leitor = new FileReader();
      leitor.onload = () => resolver(leitor.result as ArrayBuffer);
      leitor.readAsArrayBuffer(blob);
    });
    // ignoreBOM: o BOM fica no texto (sem a opção, o TextDecoder o tira).
    const texto = new TextDecoder('utf-8', { ignoreBOM: true }).decode(bytes);
    expect(texto).toBe(`${BOM}${AVISO}\r\nGerência\r\nGerência 1`);
    expect(liberar).toHaveBeenCalledWith('blob:teste');
    expect(document.querySelector('a[download]')).toBeNull();
  });
});

describe('imprimirPagina', () => {
  test('abre a impressão do navegador (dali sai o PDF)', () => {
    const imprimir = vi.spyOn(window, 'print').mockImplementation(() => undefined);
    imprimirPagina();
    expect(imprimir).toHaveBeenCalledTimes(1);
    imprimir.mockRestore();
  });
});
