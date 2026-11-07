/**
 * Contraste do link do tema (decisão 6 do piloto C1, lote D, item D5).
 *
 * Sem `colorLink` o AntD usa o colorInfo #1677ff: 4,10:1 no branco e hover #69b1ff com 2,25:1.
 * O `colorLink` é token SEED: o AntD o rederiva pela paleta (no escuro, mistura com #141414).
 * Por isso o teste mede o token DERIVADO (`theme.getDesignToken`), não o objeto passado.
 */
import { act, render } from '@testing-library/react';
import { describe, expect, test } from 'vitest';
import { theme } from 'antd';

import { ThemeProvider, useTheme, type ThemeContextValue } from '../ThemeContext';

const FUNDOS_CLARO = ['#ffffff', '#f0f2f5', '#fafafa', '#f4faf7', '#e5ede5'];
const FUNDOS_ESCURO = ['#1f1f1f', '#141414', '#262626'];
const TOKENS = ['colorLink', 'colorLinkHover', 'colorLinkActive'] as const;

function montarTema(): { atual: () => ThemeContextValue } {
  let valor: ThemeContextValue | undefined;
  function Leitor(): null {
    valor = useTheme();
    return null;
  }
  render(
    <ThemeProvider>
      <Leitor />
    </ThemeProvider>,
  );
  return { atual: () => valor! };
}

function conferirLinks(config: ThemeContextValue['antThemeConfig'], fundos: string[]): void {
  const t = theme.getDesignToken(config);
  for (const nome of TOKENS) {
    for (const fundo of fundos) {
      expect(contraste(t[nome], fundo), `${nome} ${t[nome]} sobre ${fundo}`).toBeGreaterThanOrEqual(4.5);
    }
  }
}

describe('ThemeContext: link do tema com contraste AA', { timeout: 20000 }, () => {
  test('tema claro: colorLink, hover e active com 4,5:1 nos fundos claros', () => {
    const tema = montarTema();
    expect(tema.atual().isDark).toBe(false);
    conferirLinks(tema.atual().antThemeConfig, FUNDOS_CLARO);
  });

  test('tema escuro: colorLink, hover e active com 4,5:1 nos fundos escuros', () => {
    const tema = montarTema();
    act(() => tema.atual().setThemeMode('dark'));
    expect(tema.atual().isDark).toBe(true);
    conferirLinks(tema.atual().antThemeConfig, FUNDOS_ESCURO);
  });
});

/** Luminância relativa (WCAG 2.x) de #rrggbb. */
function luminancia(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!;
}

function contraste(a: string, b: string): number {
  const [claro, escuro] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (claro! + 0.05) / (escuro! + 0.05);
}
