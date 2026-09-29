/**
 * Trava do lint do Programa C (C0): `Table` do AntD só entra por
 * `components/ResponsiveTable` (criado no C1). Os arquivos que importavam
 * `Table` em 2026-09-29 estão em `eslint.tabela-antd-allowlist.js`, que só encolhe.
 *
 * O teste lê a configuração REAL (`calculateConfigForFile`) e roda a regra
 * resolvida com o `Linter` do ESLint. Não usa o parser type-aware do projeto:
 * `no-restricted-imports` não precisa de tipos, e assim o teste leva milissegundos.
 */
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { ESLint, Linter } from 'eslint';
import tseslint from 'typescript-eslint';
import { describe, expect, test } from 'vitest';

import { TABELA_ANTD_ALLOWLIST } from '../../../eslint.tabela-antd-allowlist.js';

const RAIZ = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const REGRA = 'no-restricted-imports';

/**
 * Teto da allowlist: 27 arquivos medidos em 2026-09-29 (pela própria regra,
 * sem allowlist). Só desce. Ao tirar arquivos da allowlist, baixe este número
 * junto; arquivo novo com `Table` não entra aqui, usa ResponsiveTable.
 */
const TETO_ALLOWLIST = 27;

const eslint = new ESLint({ cwd: RAIZ });

async function regraPara(arquivo: string): Promise<Linter.RuleEntry | undefined> {
  const config = (await eslint.calculateConfigForFile(arquivo)) as Linter.Config;
  return config.rules?.[REGRA];
}

async function violacoes(arquivo: string, codigo: string): Promise<Linter.LintMessage[]> {
  const entrada = await regraPara(arquivo);
  if (entrada === undefined) return [];
  const linter = new Linter({ configType: 'flat' });
  return linter
    .verify(
      codigo,
      [{ files: ['**/*.{ts,tsx}'], languageOptions: { parser: tseslint.parser }, rules: { [REGRA]: entrada } }],
      { filename: resolve(RAIZ, arquivo) }
    )
    .filter((m) => m.ruleId === REGRA);
}

const FORA_DA_ALLOWLIST = 'src/pages/TelaNova/TelaNovaPage.tsx';

describe('lint: Table do AntD só via ResponsiveTable (Programa C)', () => {
  test.each([
    ["import { Table } from 'antd';", 'import nomeado de antd'],
    ["import { Button, Table as Grade } from 'antd';", 'import renomeado de antd'],
    ["import * as antd from 'antd';", 'namespace de antd'],
    ["import Table from 'antd/es/table';", 'default de antd/es/table'],
    ["import Table from 'antd/lib/table';", 'default de antd/lib/table'],
    ["export { Table } from 'antd';", 'reexport de antd'],
    ["import Table from 'antd/es/table/Table';", 'caminho profundo do componente'],
    ["import RcTable from 'antd/lib/table/RcTable';", 'caminho profundo do rc-table do antd'],
    ["import Table from 'rc-table';", 'rc-table direto'],
  ])('arquivo fora da allowlist: %s dá erro (%s)', async (codigo) => {
    const erros = await violacoes(FORA_DA_ALLOWLIST, codigo);
    expect(erros).toHaveLength(1);
    expect(erros[0]?.severity).toBe(2);
    expect(erros[0]?.message).toContain('components/ResponsiveTable');
  });

  test.each([
    ["import type { ColumnsType } from 'antd/es/table';", 'tipo de coluna'],
    ["import type { TableRowSelection } from 'antd/es/table/interface';", 'tipos da interface'],
    ["import { Button, Space } from 'antd';", 'outros componentes do antd'],
  ])('arquivo fora da allowlist: %s continua permitido (%s)', async (codigo) => {
    expect(await violacoes(FORA_DA_ALLOWLIST, codigo)).toEqual([]);
  });

  test('arquivo da allowlist não recebe a regra', async () => {
    const [primeiro] = Object.keys(TABELA_ANTD_ALLOWLIST);
    expect(primeiro).toBeDefined();
    expect(await violacoes(primeiro ?? '', "import { Table } from 'antd';")).toEqual([]);
  });

  test('toda entrada da allowlist diz qual PR do Programa C a remove', () => {
    const semMotivo = Object.entries(TABELA_ANTD_ALLOWLIST)
      .filter(([, motivo]) => !/^C[1-7]\b/.test(motivo))
      .map(([arquivo]) => arquivo);
    expect(semMotivo).toEqual([]);
  });

  test('a allowlist só encolhe: todo arquivo listado ainda importa Table', async () => {
    const jaConsertados: string[] = [];
    for (const arquivo of Object.keys(TABELA_ANTD_ALLOWLIST)) {
      const codigo = readFileSync(resolve(RAIZ, arquivo), 'utf8');
      // Mede com a regra de um arquivo FORA da allowlist (a mesma regra, sem a exceção).
      if ((await violacoes(FORA_DA_ALLOWLIST, codigo)).length === 0) jaConsertados.push(arquivo);
    }
    expect(jaConsertados, 'estes arquivos não importam mais Table: tire-os da allowlist').toEqual([]);
  });

  test(`a allowlist tem exatamente ${TETO_ALLOWLIST} entradas (teto que só desce)`, () => {
    expect(
      Object.keys(TABELA_ANTD_ALLOWLIST).length,
      'a allowlist mudou de tamanho: se encolheu, baixe TETO_ALLOWLIST; se cresceu, use ResponsiveTable'
    ).toBe(TETO_ALLOWLIST);
  });
});
