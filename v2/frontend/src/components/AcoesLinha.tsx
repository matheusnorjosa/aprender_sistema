/**
 * Ações de uma linha de tabela sem ocupar largura (Programa C, padrão responsivo).
 *
 * Botões só de ícone, com nome acessível e Tooltip (molde de DeslocamentosPage). Até
 * ICONES_NA_LINHA ícones; da 4ª ação em diante, o menu "Mais ações". No celular
 * (`compacto`), todas as ações vão para o menu. A coluna usa `larguraAcoesLinha`.
 * Padrão: v2/docs/specs/frontend/pages.spec.md, "Padrão responsivo".
 */
import { useRef, useState, type JSX, type KeyboardEvent, type ReactNode } from 'react';
import { Button, Dropdown, Tooltip } from 'antd';
import type { TooltipProps } from 'antd';
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

/** O rótulo aparece também no foco por teclado, não só no hover (o padrão do AntD). */
const DICA_NO_FOCO: NonNullable<TooltipProps['trigger']> = ['hover', 'focus'];
const MAIS_ACOES = 'mais-acoes'; // chave da dica do botão "Mais ações"

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
  const [menuAberto, setMenuAberto] = useState(false);
  const botaoMaisRef = useRef<HTMLButtonElement>(null);
  // Dica aberta (chave da ação): controlada para o Esc fechá-la sem tirar o foco (WCAG 1.4.13).
  // Sem isso, a dica que abre quando um modal devolve o foco ao ícone ficava presa.
  const [dicaAberta, setDicaAberta] = useState<string | null>(null);
  const dica = (chave: string): Pick<TooltipProps, 'open' | 'onOpenChange'> => ({
    open: dicaAberta === chave,
    onOpenChange: (aberta) => setDicaAberta((atual) => (aberta ? chave : atual === chave ? null : atual)),
  });
  const fecharDicaNoEsc = (evento: KeyboardEvent): void => {
    if (evento.key === 'Escape') setDicaAberta(null);
  };

  return (
    <div className="flex flex-nowrap items-center gap-1">
      {icones.map((acao) => (
        <Tooltip key={acao.chave} title={acao.rotulo} trigger={DICA_NO_FOCO} {...dica(acao.chave)}>
          <Button
            type="link"
            size="small"
            icon={acao.icone}
            danger={Boolean(acao.perigo)}
            aria-label={nome(acao.rotulo)}
            onClick={acao.onClick}
            onKeyDown={fecharDicaNoEsc}
          />
        </Tooltip>
      ))}
      {noMenu.length > 0 && (
        // O Button é filho direto do Dropdown: é nele que o rc-dropdown devolve o foco no Esc.
        <Tooltip title="Mais ações" trigger={DICA_NO_FOCO} {...dica(MAIS_ACOES)}>
          <Dropdown
            trigger={['click']}
            open={menuAberto}
            onOpenChange={(aberto, info) => {
              setMenuAberto(aberto);
              // Escolheu uma ação: o foco volta ao botão antes de a ação abrir o modal, que o
              // devolve aqui ao fechar (sem isso, ficava no item do menu escondido e se perdia).
              if (!aberto && info.source === 'menu') botaoMaisRef.current?.focus();
            }}
            autoFocus
            menu={{
              items: noMenu.map((acao) => ({
                key: acao.chave,
                label: acao.rotulo,
                icon: acao.icone,
                danger: Boolean(acao.perigo),
                onClick: ({ domEvent }) => {
                  // Enter: o rc-menu chama isto já no keydown, e o foco volta ao botão ali mesmo.
                  // Cancelar o keydown suprime o keypress, que no botão viraria clique e reabriria
                  // o menu por cima do modal.
                  if (domEvent.type === 'keydown') domEvent.preventDefault();
                  acao.onClick();
                },
              })),
            }}
          >
            <Button
              ref={botaoMaisRef}
              type="link"
              size="small"
              icon={<MoreOutlined />}
              aria-label={nome('Mais ações')}
              onKeyDown={fecharDicaNoEsc}
              aria-haspopup="menu"
              aria-expanded={menuAberto}
            />
          </Dropdown>
        </Tooltip>
      )}
    </div>
  );
}
