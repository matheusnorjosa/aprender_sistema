/**
 * Desenho do DFF na Integra (decisão do dono, 26/11/2026): os tokens num lugar só.
 *
 * Valem só na moldura da Integra (`IntegraLayout`) e só no tema claro (o DFF não tem modo escuro). O verde da marca
 * já é o do DFF no sistema inteiro (`BRAND_COLORS`); aqui ficam o fundo verde-claro, o cartão e a tabela. O CSS
 * (`integra.css`) lê estas cores pelas variáveis `--integra-*` que a moldura põe no próprio elemento.
 * Contraste conferido em `__tests__/IntegraLayout.test.tsx`.
 */
import type { CSSProperties } from 'react';
import type { ThemeConfig } from 'antd';

export const VISUAL_DFF = {
  /** Fundo verde-claro do DFF, só na Integra. */
  fundo: '#d8edcb',
  /** Borda do cartão (slate-200). Enfeite: o cartão não é controle, e o conteúdo dele fica no branco. */
  borda: '#e2e8f0',
  /** Fundo do cabeçalho da tabela (slate-50). */
  cabecalho: '#f8fafc',
  /** Texto do cabeçalho da tabela (slate-600): 7,24:1. O slate-500 do DFF dá 4,55:1, no limite. */
  textoCabecalho: '#475569',
  /** Linha entre as linhas da tabela (slate-100). */
  divisoria: '#f1f5f9',
} as const;

/** As cores para o `integra.css`, no `style` da moldura. */
export const VARIAVEIS_DFF = {
  '--integra-fundo': VISUAL_DFF.fundo,
  '--integra-borda': VISUAL_DFF.borda,
  '--integra-cabecalho': VISUAL_DFF.cabecalho,
  '--integra-texto-cabecalho': VISUAL_DFF.textoCabecalho,
} as CSSProperties;

/** Tema do antd só na moldura (precedente: `TEMA_DA_TABELA` em `Aprovacoes/ApprovalsPage.tsx`). */
export const TEMA_DA_INTEGRA: ThemeConfig = {
  components: {
    Button: { borderRadius: 8, borderRadiusLG: 8, borderRadiusSM: 8 },
    Card: { borderRadiusLG: 16, colorBorderSecondary: VISUAL_DFF.borda },
    Table: {
      headerBg: VISUAL_DFF.cabecalho,
      headerColor: VISUAL_DFF.textoCabecalho,
      headerSplitColor: 'transparent',
      borderColor: VISUAL_DFF.divisoria,
    },
    Typography: { fontWeightStrong: 700 },
  },
};
