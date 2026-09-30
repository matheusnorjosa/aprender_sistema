/**
 * Ações de uma linha de tabela sem ocupar largura (Programa C, padrão responsivo).
 *
 * Botões só de ícone, com nome acessível e Tooltip (molde de DeslocamentosPage). Até
 * ICONES_NA_LINHA ícones; da 4ª ação em diante, o menu "Mais ações". No celular
 * (`compacto`), todas as ações vão para o menu. A coluna usa `larguraAcoesLinha`.
 * Padrão: v2/docs/specs/frontend/pages.spec.md, "Padrão responsivo".
 */
import type { JSX, ReactNode } from 'react';
import { Button, Dropdown, Tooltip } from 'antd';
import { MoreOutlined } from '@ant-design/icons';

export interface AcaoDaLinha {
  chave: string;
  /** Texto curto: Tooltip do ícone, item do menu e início do nome acessível. */
  rotulo: string;
  icone: ReactNode;
  onClick: () => void;
  perigo?: boolean;
}

/** Quantos ícones ficam na linha; da 4ª ação em diante, o menu "Mais ações". */
export const ICONES_NA_LINHA = 3;

const BOTAO_PX = 24; // Button size="small" só de ícone
const ESPACO_PX = 4; // gap-1 entre os botões
const CELULA_PX = 32; // padding horizontal da célula (8 + 8 no middle/small) e folga
const MINIMO_PX = 64; // o título "Ações" cabe sem quebrar

/** Largura da coluna de ações para `quantidade` ações (a maior da tabela). */
export function larguraAcoesLinha(quantidade: number, compacto = false): number {
  const botoes = compacto ? 1 : Math.min(quantidade, ICONES_NA_LINHA) + (quantidade > ICONES_NA_LINHA ? 1 : 0);
  return Math.max(MINIMO_PX, botoes * BOTAO_PX + (botoes - 1) * ESPACO_PX + CELULA_PX);
}

interface AcoesLinhaProps {
  acoes: readonly AcaoDaLinha[];
  /** Quem a linha representa (ex.: o nome): completa o nome acessível, "Editar: Maria". */
  alvo?: string;
  /** Celular: um botão só, com todas as ações no menu. */
  compacto?: boolean;
}

export function AcoesLinha({ acoes, alvo, compacto = false }: AcoesLinhaProps): JSX.Element {
  const nome = (rotulo: string): string => (alvo ? `${rotulo}: ${alvo}` : rotulo);
  const icones = compacto ? [] : acoes.slice(0, ICONES_NA_LINHA);
  const noMenu = compacto ? acoes : acoes.slice(ICONES_NA_LINHA);

  return (
    <div className="flex flex-nowrap items-center gap-1">
      {icones.map((acao) => (
        <Tooltip key={acao.chave} title={acao.rotulo}>
          <Button
            type="link"
            size="small"
            icon={acao.icone}
            danger={Boolean(acao.perigo)}
            aria-label={nome(acao.rotulo)}
            onClick={acao.onClick}
          />
        </Tooltip>
      ))}
      {noMenu.length > 0 && (
        <Dropdown
          trigger={['click']}
          menu={{
            items: noMenu.map((acao) => ({
              key: acao.chave,
              label: acao.rotulo,
              icon: acao.icone,
              danger: Boolean(acao.perigo),
              onClick: acao.onClick,
            })),
          }}
        >
          <Tooltip title="Mais ações">
            <Button type="link" size="small" icon={<MoreOutlined />} aria-label={nome('Mais ações')} />
          </Tooltip>
        </Dropdown>
      )}
    </div>
  );
}
