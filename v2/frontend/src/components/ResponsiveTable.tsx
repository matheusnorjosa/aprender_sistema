/**
 * ResponsiveTable: a tabela do app, sem rolagem horizontal (Programa C).
 *
 * Único arquivo que importa `Table` do AntD (lint em eslint.config.js). O padrão:
 * - o tipo não aceita `scroll` nem coluna `fixed`: a largura se resolve por prioridade;
 * - cada coluna declara a partir de que largura aparece (`responsive`, via
 *   VISIVEL_A_PARTIR); sem `responsive`, aparece sempre (identidade, estado e ações);
 * - o que está escondido na largura atual aparece na linha expandida, como
 *   `<Descriptions column={1}>`, com o `title` e o `render` da própria coluna: nada some;
 * - `tableLayout="fixed"`: `width` só nas colunas estreitas e `ellipsis` nas de texto.
 * Densidade: `middle` por padrão e `small` no celular (abaixo de `md`), para caber mais
 * colunas na linha antes de mandá-las para o detalhe.
 * Padrão: v2/docs/specs/frontend/pages.spec.md, "Padrão responsivo".
 */
import type { JSX, ReactNode } from 'react';
import { Descriptions, Grid, Table } from 'antd';
import type { Breakpoint, TableProps } from 'antd';
import type { ColumnType } from 'antd/es/table';
import type { AnyObject } from 'antd/es/_util/type';

/** Prioridade da coluna: a partir de que largura (quebras do AntD) ela aparece na linha. */
export const VISIVEL_A_PARTIR = {
  sm: ['sm'], // >= 576 px
  md: ['md'], // >= 768 px
  lg: ['lg'], // >= 992 px
  xl: ['xl'], // >= 1200 px
  xxl: ['xxl'], // >= 1600 px
} as const satisfies Record<string, readonly Breakpoint[]>;

export type PrioridadeDaColuna = (typeof VISIVEL_A_PARTIR)[keyof typeof VISIVEL_A_PARTIR];

export interface ColunaResponsiva<T> extends Omit<ColumnType<T>, 'fixed' | 'responsive' | 'title' | 'render'> {
  /** Rótulo da coluna; na linha expandida, rotula o valor. */
  title: ReactNode;
  /** A partir de que largura a coluna aparece na linha. Sem ele, aparece sempre. */
  responsive?: PrioridadeDaColuna;
  /** Sem o envelope `{ children, props }` do rc-table: o detalhe reaproveita o que a célula mostra. */
  render?(valor: unknown, registro: T, indice: number): ReactNode;
}

export interface ResponsiveTableProps<T extends AnyObject>
  extends Omit<TableProps<T>, 'columns' | 'scroll' | 'tableLayout' | 'expandable'> {
  columns: ColunaResponsiva<T>[];
}

type Telas = Partial<Record<Breakpoint, boolean>>;

function visivel<T>(coluna: ColunaResponsiva<T>, telas: Telas): boolean {
  return !coluna.responsive || coluna.responsive.some((quebra) => telas[quebra]);
}

/** O valor em `dataIndex` (campo ou caminho `['a', 'b']`), como o AntD o lê. */
function lerCampo(registro: unknown, caminho: unknown): unknown {
  const chaves: unknown[] = Array.isArray(caminho) ? caminho : [caminho];
  let atual: unknown = registro;
  for (const chave of chaves) {
    if (atual === null || typeof atual !== 'object') return undefined;
    atual = Reflect.get(atual, String(chave));
  }
  return atual;
}

function conteudo<T>(coluna: ColunaResponsiva<T>, registro: T, indice: number): ReactNode {
  const valor = coluna.dataIndex === undefined ? undefined : lerCampo(registro, coluna.dataIndex);
  if (coluna.render) return coluna.render(valor, registro, indice);
  return typeof valor === 'string' || typeof valor === 'number' ? valor : null;
}

export default function ResponsiveTable<T extends AnyObject>({
  columns,
  size,
  ...props
}: ResponsiveTableProps<T>): JSX.Element {
  const telas = Grid.useBreakpoint();
  const naLinha = columns.filter((coluna) => visivel(coluna, telas)).map(({ responsive: _prioridade, ...coluna }) => coluna);
  const escondidas = columns.filter((coluna) => !visivel(coluna, telas));

  return (
    <Table<T>
      {...props}
      size={telas.md ? (size ?? 'middle') : 'small'}
      columns={naLinha}
      tableLayout="fixed"
      {...(escondidas.length > 0 && {
        expandable: {
          columnWidth: 40,
          expandedRowRender: (registro: T, indice: number) => (
            <Descriptions
              size="small"
              column={1}
              items={escondidas.map((coluna, posicao) => ({
                key: String(coluna.key ?? posicao),
                label: coluna.title,
                children: conteudo(coluna, registro, indice),
              }))}
            />
          ),
        },
      })}
    />
  );
}
