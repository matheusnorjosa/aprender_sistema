/**
 * Contraste AA (4,5:1) do vermelho de erro e do texto de exemplo no tema claro (DEF-28).
 *
 * O AntD pinta a mensagem de erro do Form e o asterisco do obrigatório com o `colorError`, e o
 * `Text type="danger"` com o `colorErrorText`: os dois eram #ff4d4f (3,27:1 no branco, 2,91:1 na
 * página e 2,74:1 no cartão do login). O texto de exemplo (placeholder) de Input, Select e
 * DatePicker usa o `colorTextPlaceholder`, que era o quaternário rgba(0,0,0,0.25) (1,83:1 no campo).
 * O axe do checklist não pega nenhum dos dois: o erro só aparece depois de validar, e o
 * `::placeholder` fica fora da regra de contraste dele.
 *
 * O `colorError` é token SEED (o AntD deriva dele o `colorErrorText`): o teste mede os tokens
 * DERIVADOS (`theme.getDesignToken`) da configuração que o ThemeProvider monta, como o teste do link.
 */
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { render } from '@testing-library/react';
import { describe, expect, test } from 'vitest';
import { theme, type GlobalToken } from 'antd';

import { BRAND_COLORS, ThemeProvider, useTheme, type ThemeContextValue } from '../ThemeContext';

type Rgb = [number, number, number];

function tokensDoTemaClaro(): GlobalToken {
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
  expect(valor!.isDark).toBe(false);
  return theme.getDesignToken(valor!.antThemeConfig);
}

/** Onde o texto aparece no tema claro: Card, campo (Input, Select) e Modal usam os fundos do AntD. */
function fundosDoTemaClaro(t: GlobalToken): Record<string, string> {
  return {
    'fundo da página': BRAND_COLORS.pageBackground,
    card: t.colorBgContainer,
    campo: t.colorBgContainer,
    modal: t.colorBgElevated,
  };
}

describe('Tema claro: vermelho de erro e texto de exemplo com contraste AA', { timeout: 20000 }, () => {
  test('erro do Form e Text danger: 4,5:1 na página, no card, no campo, no modal e no cartão do login', () => {
    const t = tokensDoTemaClaro();
    // O login e a troca obrigatória de senha mostram os erros do Form sobre o verde-claro da marca.
    const fundos = { ...fundosDoTemaClaro(t), 'cartão do login': BRAND_COLORS.primaryLight };
    for (const nome of ['colorError', 'colorErrorText'] as const) {
      for (const [onde, fundo] of Object.entries(fundos)) {
        expect(contraste(t[nome], fundo), `${nome} ${t[nome]} sobre ${onde} (${fundo})`).toBeGreaterThanOrEqual(4.5);
      }
    }
  });

  test('texto de exemplo dos campos: 4,5:1 na página, no card, no campo e no modal', () => {
    const t = tokensDoTemaClaro();
    for (const [onde, fundo] of Object.entries(fundosDoTemaClaro(t))) {
      expect(contraste(t.colorTextPlaceholder, fundo), `${t.colorTextPlaceholder} sobre ${onde} (${fundo})`).toBeGreaterThanOrEqual(
        4.5,
      );
    }
  });

  test('texto de exemplo do login (App.css, vence o token): 4,5:1 no campo branco', () => {
    const exemplo = valorNoAppCss('.login-page .login-card .ant-input::placeholder', 'color');
    // A senha (Input.Password) tem a mesma cor, na mesma regra.
    expect(valorNoAppCss('.login-page .login-card .ant-input-affix-wrapper input::placeholder', 'color')).toBe(exemplo);
    const campo = valorNoAppCss('.login-page .login-card .ant-input', 'background-color');
    expect(contraste(exemplo, campo), `${exemplo} sobre ${campo}`).toBeGreaterThanOrEqual(4.5);
  });
});

// `?raw` de CSS volta vazio no Vitest (CSS desligado): lê o arquivo do disco.
const appCss = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), '../../App.css'), 'utf-8');

/** Valor da propriedade na regra do App.css que lista exatamente este seletor. */
function valorNoAppCss(seletor: string, propriedade: string): string {
  const folha = document.createElement('style');
  folha.textContent = appCss;
  document.head.appendChild(folha);
  try {
    const regra = Array.from(folha.sheet?.cssRules ?? [])
      .filter((r): r is CSSStyleRule => 'selectorText' in r)
      .find((r) => r.selectorText.split(',').map((s) => s.trim()).includes(seletor));
    if (!regra) throw new Error(`App.css não tem regra para: ${seletor}`);
    return regra.style.getPropertyValue(propriedade);
  } finally {
    folha.remove();
  }
}

/** `#rrggbb`, `rgb(...)` ou `rgba(...)` como [r, g, b, alfa]. */
function canais(cor: string): [number, number, number, number] {
  const hex = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(cor.trim());
  if (hex) return [parseInt(hex[1]!, 16), parseInt(hex[2]!, 16), parseInt(hex[3]!, 16), 1];
  const rgb = /^rgba?\(([^)]*)\)$/.exec(cor.trim());
  if (!rgb) throw new Error(`cor ilegível: ${cor}`);
  const [r, g, b, a = 1] = rgb[1]!.split(',').map(Number);
  return [r!, g!, b!, a];
}

/** A cor como o navegador a pinta sobre um fundo opaco (compõe o alfa). */
function sobre(cor: string, fundo: string): Rgb {
  const [r, g, b, a] = canais(cor);
  const [fr, fg, fb] = canais(fundo);
  return [r * a + fr * (1 - a), g * a + fg * (1 - a), b * a + fb * (1 - a)];
}

/** Luminância relativa (WCAG 2.x). */
function luminancia(rgb: Rgb): number {
  const [r, g, b] = rgb.map((v) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!;
}

function contraste(cor: string, fundo: string): number {
  const [claro, escuro] = [luminancia(sobre(cor, fundo)), luminancia(sobre(fundo, fundo))].sort((x, y) => y - x);
  return (claro! + 0.05) / (escuro! + 0.05);
}
