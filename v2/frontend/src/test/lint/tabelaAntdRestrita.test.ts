/**
 * Trava do lint do Programa C (C0): `Table` do AntD só entra por
 * `components/ResponsiveTable` (o padrão, criado no C1, isento para sempre). Os
 * arquivos que importavam `Table` em 2026-09-29 estão em
 * `eslint.tabela-antd-allowlist.js`, que só encolhe.
 *
 * O teste lê a configuração REAL (`calculateConfigForFile`) e roda as regras
 * resolvidas com o `Linter` do ESLint, sem o parser type-aware do projeto (as
 * duas regras não precisam de tipos): o arquivo inteiro leva poucos segundos.
 *
 * Três camadas:
 * 1. cada forma de importar Table (barris, caminhos profundos, `.js`, `/index`,
 *    import dinâmico, require) dá erro fora da allowlist;
 * 2. o ratchet compara IDENTIDADE: o conjunto de arquivos de `src/` que importam
 *    Table, medido com os comentários `eslint-disable` desligados, tem de ser
 *    igual à allowlist. Arquivo novo que escapa por comentário, e entrada velha
 *    que já não importa, reprovam;
 * 3. controles provam que a medição enxerga cada forma de escape por comentário.
 * E a allowlist tem exatamente TETO_ALLOWLIST arquivos, teto que só desce.
 */
import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { ESLint, Linter } from 'eslint';
import tseslint from 'typescript-eslint';
import { describe, expect, test } from 'vitest';

import { TABELA_ANTD_ALLOWLIST, TABELA_ANTD_PADRAO } from '../../../eslint.tabela-antd-allowlist.js';

const RAIZ = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const REGRAS = ['no-restricted-imports', 'no-restricted-syntax'] as const;
const FORA_DA_ALLOWLIST = 'src/pages/TelaNova/TelaNovaPage.tsx';

const eslint = new ESLint({ cwd: RAIZ });

/** As regras da trava como a config real as resolve para `arquivo` ({} = isento). */
async function regrasPara(arquivo: string): Promise<Linter.RulesRecord> {
  const config = (await eslint.calculateConfigForFile(arquivo)) as Linter.Config;
  const regras: Linter.RulesRecord = {};
  for (const regra of REGRAS) {
    const entrada = config.rules?.[regra];
    if (entrada !== undefined) regras[regra] = entrada;
  }
  return regras;
}

/** Mensagens das regras da trava. `comComentarios=false` ignora `eslint-disable` e config inline. */
function verificar(regras: Linter.RulesRecord, arquivo: string, codigo: string, comComentarios = true): Linter.LintMessage[] {
  if (Object.keys(regras).length === 0) return [];
  const mensagens = new Linter({ configType: 'flat' }).verify(
    codigo,
    [{ files: ['**/*.{ts,tsx}'], languageOptions: { parser: tseslint.parser }, rules: regras }],
    { filename: resolve(RAIZ, arquivo), allowInlineConfig: comComentarios }
  );
  const fatal = mensagens.find((m) => m.fatal);
  if (fatal) throw new Error(`${arquivo}: o parser falhou (${fatal.message}); a medição não pode ser confiada`);
  return mensagens.filter((m) => (REGRAS as readonly (string | null)[]).includes(m.ruleId));
}

function arquivosDoSrc(dir = join(RAIZ, 'src')): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entrada) => {
    const caminho = join(dir, entrada.name);
    if (entrada.isDirectory()) return arquivosDoSrc(caminho);
    return /\.(ts|tsx)$/.test(entrada.name) ? [relative(RAIZ, caminho).split('\\').join('/')] : [];
  });
}

/** Quem importa Table, medido com a regra SEM a isenção e sem comentários inline. */
function quemImportaTable(regras: Linter.RulesRecord, arquivos: readonly (readonly [string, string])[]): string[] {
  return arquivos
    .filter(([arquivo]) => arquivo !== TABELA_ANTD_PADRAO)
    .filter(([arquivo, codigo]) => verificar(regras, arquivo, codigo, false).length > 0)
    .map(([arquivo]) => arquivo)
    .sort();
}

/**
 * Tamanho atual da allowlist: 27 em 2026-09-29, 26 depois do C1 (Usuários) e 21 depois do C2
 * (Admin DAT: grupos, gerências, municípios, produtos e projetos gerais) e 20 depois de Projetos
 * (marca de série, 01/10/2026). Só desce: voltar a
 * pôr um arquivo na allowlist (e fazê-lo importar Table de novo) reprova aqui, no diff deste teste.
 */
const TETO_ALLOWLIST = 20;

function conferirTeto(allowlist: Readonly<Record<string, string>>, teto: number): string[] {
  const tamanho = Object.keys(allowlist).length;
  if (tamanho > teto) return [`a allowlist tem ${tamanho} arquivos e o teto é ${teto}: o teto só desce`];
  if (tamanho < teto) return [`a allowlist encolheu para ${tamanho}: baixe TETO_ALLOWLIST de ${teto} para ${tamanho}`];
  return [];
}

function compararComAllowlist(medidos: readonly string[], allowlist: Readonly<Record<string, string>>) {
  return {
    foraDaAllowlist: medidos.filter((a) => !(a in allowlist)),
    semImportar: Object.keys(allowlist).filter((a) => !medidos.includes(a)).sort(),
  };
}

describe('lint: Table do AntD só via ResponsiveTable (Programa C)', () => {
  test.each([
    ["import { Table } from 'antd';", 'import nomeado de antd'],
    ["import { Button, Table as Grade } from 'antd';", 'import renomeado de antd'],
    ["import * as antd from 'antd';", 'namespace de antd'],
    ["export { Table } from 'antd';", 'reexport de antd'],
    ["import { Table } from 'antd/es';", 'barril antd/es'],
    ["import { Table } from 'antd/lib';", 'barril antd/lib'],
    ["import { Table } from 'antd/es/index.js';", 'barril com /index.js'],
    ["import { Table } from 'antd/dist/antd';", 'bundle UMD'],
    ["import Table from 'antd/es/table';", 'default de antd/es/table'],
    ["import Table from 'antd/lib/table';", 'default de antd/lib/table'],
    ["import { default as Table } from 'antd/es/table';", 'default renomeado'],
    ["import Table from 'antd/es/table/index';", 'caminho com /index'],
    ["import Table from 'antd/es/table/index.js';", 'caminho com /index.js'],
    ["import Table from 'antd/es/table/Table';", 'caminho profundo do componente'],
    ["import Table from 'antd/lib/table/Table.js';", 'caminho profundo com .js'],
    ["import Column from 'antd/es/table/Column';", 'Table.Column por caminho profundo'],
    ["import RcTable from 'antd/lib/table/RcTable';", 'rc-table do antd'],
    ["import Table from 'rc-table';", 'rc-table direto'],
    ["const antd = await import('antd');", 'import dinâmico de antd'],
    ["const m = import('antd/es/table');", 'import dinâmico do caminho da tabela'],
    ['const m = import(`antd`);', 'import dinâmico com template literal'],
    ["const { Table } = require('antd');", 'require de antd'],
  ])('fora da allowlist, %s dá erro (%s)', async (codigo) => {
    const erros = verificar(await regrasPara(FORA_DA_ALLOWLIST), FORA_DA_ALLOWLIST, codigo);
    expect(erros.length).toBeGreaterThan(0);
    expect(erros.every((e) => e.severity === 2)).toBe(true);
    expect(erros[0]?.message).toContain('components/ResponsiveTable');
  });

  test.each([
    ["import type { ColumnsType } from 'antd/es/table';", 'tipo de coluna'],
    ["import type { TablePaginationConfig } from 'antd/lib/table';", 'tipo da paginação'],
    ["import type { TableRowSelection } from 'antd/es/table/interface';", 'tipos da interface'],
    ["import { Button, Space } from 'antd';", 'outros componentes do antd'],
    ["import { Button } from 'antd/es';", 'outro componente pelo barril'],
    ["const Pagina = lazy(() => import('../pages/Home/HomePage'));", 'import dinâmico de página'],
  ])('fora da allowlist, %s continua permitido (%s)', async (codigo) => {
    expect(verificar(await regrasPara(FORA_DA_ALLOWLIST), FORA_DA_ALLOWLIST, codigo)).toEqual([]);
  });

  test('components/ResponsiveTable é isento para sempre, fora da allowlist', async () => {
    expect(TABELA_ANTD_PADRAO).toBe('src/components/ResponsiveTable.tsx');
    expect(TABELA_ANTD_PADRAO in TABELA_ANTD_ALLOWLIST).toBe(false);
    expect(await regrasPara(TABELA_ANTD_PADRAO)).toEqual({});
  });

  test('arquivo da allowlist não recebe a regra', async () => {
    const [primeiro] = Object.keys(TABELA_ANTD_ALLOWLIST);
    expect(primeiro).toBeDefined();
    expect(await regrasPara(primeiro ?? '')).toEqual({});
  });

  test('toda entrada da allowlist diz qual PR do Programa C a remove', () => {
    const semMotivo = Object.entries(TABELA_ANTD_ALLOWLIST)
      .filter(([, motivo]) => !/^C[1-7]\b/.test(motivo))
      .map(([arquivo]) => arquivo);
    expect(semMotivo).toEqual([]);
  });
});

describe('ratchet da allowlist por identidade', () => {
  const TABELA = "import { Table } from 'antd';\nexport const x = Table;\n";

  test.each([
    [`// eslint-disable-next-line no-restricted-imports\n${TABELA}`, 'eslint-disable-next-line'],
    [`/* eslint-disable */\n${TABELA}`, 'eslint-disable geral'],
    [`/* eslint-disable no-restricted-imports, no-restricted-syntax */\n${TABELA}`, 'eslint-disable das regras'],
    [`/* eslint no-restricted-imports: off */\n${TABELA}`, 'config inline desligando a regra'],
    ["// eslint-disable-next-line no-restricted-syntax\nconst m = import('antd');\n", 'disable do import dinâmico'],
  ])('a medição enxerga Table escondido por comentário (%#: %s)', async (codigo) => {
    const regras = await regrasPara(FORA_DA_ALLOWLIST);
    const medidos = quemImportaTable(regras, [[FORA_DA_ALLOWLIST, codigo]]);
    expect(medidos).toEqual([FORA_DA_ALLOWLIST]);
    expect(compararComAllowlist(medidos, {}).foraDaAllowlist).toEqual([FORA_DA_ALLOWLIST]);
  });

  test('entrada velha (arquivo que não importa mais Table) é apontada', async () => {
    const regras = await regrasPara(FORA_DA_ALLOWLIST);
    const medidos = quemImportaTable(regras, [['src/pages/Ja/Consertada.tsx', "import { Button } from 'antd';\n"]]);
    expect(compararComAllowlist(medidos, { 'src/pages/Ja/Consertada.tsx': 'C2 — teste' }).semImportar).toEqual([
      'src/pages/Ja/Consertada.tsx',
    ]);
  });

  test.each([
    ['maior que o teto reprova', { 'a.tsx': 'C2', 'b.tsx': 'C2', 'c.tsx': 'C3' }, [
      'a allowlist tem 3 arquivos e o teto é 2: o teto só desce',
    ]],
    ['menor que o teto pede para baixar o teto', { 'a.tsx': 'C2' }, [
      'a allowlist encolheu para 1: baixe TETO_ALLOWLIST de 2 para 1',
    ]],
    ['igual ao teto passa', { 'a.tsx': 'C2', 'b.tsx': 'C2' }, []],
  ])('teto da allowlist: %s', (_caso, allowlist, esperado) => {
    expect(conferirTeto(allowlist, 2)).toEqual(esperado);
  });

  test('a allowlist tem o tamanho do teto (só desce)', () => {
    expect(conferirTeto(TABELA_ANTD_ALLOWLIST, TETO_ALLOWLIST)).toEqual([]);
  });

  test('o conjunto de src/ que importa Table é exatamente a allowlist', async () => {
    const regras = await regrasPara(FORA_DA_ALLOWLIST);
    const arquivos = arquivosDoSrc();
    // Piso anti-vacuidade: se a varredura não achar src/, a igualdade passaria por vazio.
    expect(arquivos.length).toBeGreaterThan(200);
    const medidos = quemImportaTable(
      regras,
      arquivos.map((a) => [a, readFileSync(join(RAIZ, a), 'utf8')] as const)
    );
    expect(
      compararComAllowlist(medidos, TABELA_ANTD_ALLOWLIST),
      'foraDaAllowlist: use components/ResponsiveTable; semImportar: tire o arquivo da allowlist'
    ).toEqual({ foraDaAllowlist: [], semImportar: [] });
  }, 60_000);
});
