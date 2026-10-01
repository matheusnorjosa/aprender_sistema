/**
 * ResponsiveTable: a tabela do app, sem rolagem horizontal (Programa C).
 *
 * Único arquivo que importa `Table` do AntD (lint em eslint.config.js). O padrão:
 * - o tipo não aceita `scroll` nem coluna `fixed`: a largura se resolve por prioridade;
 * - cada coluna declara a partir de que largura aparece (`responsive`, via
 *   VISIVEL_A_PARTIR); sem `responsive`, aparece sempre (identidade, estado e ações);
 * - o que está escondido na largura atual aparece na linha expandida, como
 *   `<Descriptions column={1}>`, com o `title` e o `render` da própria coluna: nada some;
 *   o botão que a abre leva o nome da linha (`nomeDaLinha`), "Expandir linha de Maria";
 * - `tableLayout="fixed"`: `width` só nas colunas estreitas e `ellipsis` nas de texto;
 * - falha ao carregar (`erro`): o motivo e "Tentar de novo" no lugar das linhas, não "Não há dados",
 *   e sem paginação (o total seria o da carga anterior). Se o "Tentar de novo" carrega, as linhas
 *   tomam o lugar do botão: o foco que estava nele vai para a tabela (tabindex=-1 só nesse instante), não para o body;
 * - vazio da tela (`locale.emptyText`) na cor de texto secundário: a do AntD é a de desabilitado.
 * Densidade: `middle` por padrão e `small` no celular (abaixo de `md`), para caber mais
 * colunas na linha antes de mandá-las para o detalhe.
 * Padrão: v2/docs/specs/frontend/pages.spec.md, "Padrão responsivo".
 */
import { useEffect, useRef, type JSX, type ReactNode } from 'react';
import { Alert, Button, Descriptions, Grid, Table, theme } from 'antd';
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
  /** Quem a linha representa (ex.: o nome): nomeia o botão de expandir, "Expandir linha de Maria". */
  nomeDaLinha(registro: T): string;
  /** Falha ao carregar: o motivo aparece no lugar das linhas (erro não é "Não há dados"). */
  erro?: string | null;
  /** Com `erro`, o botão "Tentar de novo". */
  onTentarDeNovo?: () => void;
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
  nomeDaLinha,
  erro,
  onTentarDeNovo,
  dataSource,
  locale,
  ...props
}: ResponsiveTableProps<T>): JSX.Element {
  const telas = Grid.useBreakpoint();
  const { token } = theme.useToken();
  const naLinha = columns.filter((coluna) => visivel(coluna, telas)).map(({ responsive: _prioridade, ...coluna }) => coluna);
  const escondidas = columns.filter((coluna) => !visivel(coluna, telas));
  const vazio = locale?.emptyText;
  const tabelaRef = useRef<HTMLDivElement>(null);
  const tentouDeNovo = useRef(false);

  useEffect(() => {
    if (erro || !tentouDeNovo.current) return;
    tentouDeNovo.current = false;
    // Carregou: o aviso saiu e levou o botão. Se o foco estava nele, caiu no body (e o Tab recomeçaria
    // do topo); se a pessoa já tinha ido para outro campo, está lá e não é tirado dela.
    const alvo = tabelaRef.current;
    if (!alvo || document.activeElement !== document.body) return;
    // Focável só neste instante: fixo, um clique na tabela focaria o contêiner e o Tab voltaria ao topo dela.
    alvo.setAttribute('tabindex', '-1');
    alvo.addEventListener('blur', () => alvo.removeAttribute('tabindex'), { once: true });
    alvo.focus();
  }, [erro]);

  const textos = erro
    ? {
        ...locale,
        emptyText: (
          <Alert
            type="error"
            showIcon
            className="text-left"
            message="Não foi possível carregar a lista."
            description={erro}
            action={
              onTentarDeNovo ? (
                <Button
                  size="small"
                  onClick={() => {
                    tentouDeNovo.current = true;
                    onTentarDeNovo();
                  }}
                >
                  Tentar de novo
                </Button>
              ) : undefined
            }
          />
        ),
      }
    : vazio === undefined
      ? locale
      : {
          ...locale,
          // O AntD pinta o vazio com a cor de texto desabilitado (#bfbfbf, 1,83:1 no branco); o vazio
          // da tela diz o que fazer, então vai com a cor de texto secundário (AA).
          emptyText: <div style={{ color: token.colorTextSecondary }}>{typeof vazio === 'function' ? vazio() : vazio}</div>,
        };

  return (
    // Alvo do foco depois de um "Tentar de novo" que carregou; fora do Tab.
    <div ref={tabelaRef}>
      <Table<T>
        {...props}
        // Com erro, as linhas antigas (e o total delas) saem: não parecem o resultado de uma carga que falhou.
        dataSource={erro ? [] : dataSource}
        {...(erro && { pagination: false })}
        {...(textos && { locale: textos })}
        size={telas.md ? (size ?? 'middle') : 'small'}
        columns={naLinha}
        tableLayout="fixed"
        {...(escondidas.length > 0 && {
          expandable: {
            columnWidth: 40,
            columnTitle: <span className="sr-only">Detalhes</span>,
            // O botão do AntD, com as classes dele (o +/-), mas com o nome da linha: o padrão
            // ("Expandir linha") é o mesmo em todas e não diz de quem é o detalhe.
            expandIcon: ({ prefixCls, expanded, record, onExpand }) => (
              <button
                type="button"
                className={`${prefixCls}-row-expand-icon ${prefixCls}-row-expand-icon-${expanded ? 'expanded' : 'collapsed'}`}
                aria-label={`Expandir linha de ${nomeDaLinha(record)}`}
                aria-expanded={expanded}
                onClick={(evento) => {
                  onExpand(record, evento);
                  evento.stopPropagation();
                }}
              />
            ),
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
    </div>
  );
}
