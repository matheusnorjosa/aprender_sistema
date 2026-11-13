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
import { Button, ConfigProvider, theme, type GlobalToken, type ThemeConfig } from 'antd';

import { BRAND_COLORS, ThemeProvider, useTheme, type ThemeContextValue } from '../ThemeContext';

type Rgb = [number, number, number];

function configDoTemaClaro(): ThemeConfig {
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
  return valor!.antThemeConfig;
}

function tokensDoTemaClaro(): GlobalToken {
  return theme.getDesignToken(configDoTemaClaro());
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
    const exemplo = valorNoCss(appCss, '.login-page .login-card .ant-input::placeholder', 'color');
    // A senha (Input.Password) tem a mesma cor, na mesma regra.
    expect(valorNoCss(appCss, '.login-page .login-card .ant-input-affix-wrapper input::placeholder', 'color')).toBe(exemplo);
    const campo = valorNoCss(appCss, '.login-page .login-card .ant-input', 'background-color');
    expect(contraste(exemplo, campo), `${exemplo} sobre ${campo}`).toBeGreaterThanOrEqual(4.5);
  });

  test('texto de exemplo dos <input> comuns (index.css, fora do token): 4,5:1 no campo branco', () => {
    // O token só pinta os campos do AntD. O <input> comum (filtros da Disponibilidade) ficava com o
    // cinza do preflight do Tailwind, #9ca3af: 2,54:1. A regra fica no `@layer base` para sair logo
    // depois do preflight e vencê-lo; os seletores do AntD e do login são mais fortes e seguem valendo.
    const exemplo = valorNoCss(indexCss, 'input::placeholder', 'color', '@layer base');
    expect(valorNoCss(indexCss, 'textarea::placeholder', 'color', '@layer base')).toBe(exemplo);
    // O <input> comum fica com o fundo branco do navegador, também no tema escuro (sem color-scheme).
    expect(contraste(exemplo, '#ffffff'), `${exemplo} sobre o campo branco`).toBeGreaterThanOrEqual(4.5);
  });
});

/**
 * Botão `danger`: o AntD pinta o hover com o `colorErrorHover`, e o pressionado do botão de texto com o
 * `colorErrorHover` sobre o `colorErrorBgActive`. Derivados do red-7, davam 3,87:1 no hover e 1,96:1
 * no pressionado do "Excluir" dos modais (o botão pinta o próprio fundo rosado, em qualquer lugar).
 * O teste lê o CSS que o AntD gera com o tema, porque o ajuste é token do componente Button.
 */
describe('Tema claro: botão danger com contraste AA no hover e no pressionado', { timeout: 20000 }, () => {
  test.each([
    ['text', 'hover'],
    ['text', 'active'],
    ['link', 'hover'],
    ['link', 'active'],
    ['outlined', 'hover'],
    ['outlined', 'active'],
    ['solid', 'hover'],
    ['solid', 'active'],
  ] as const)('variante %s, estado %s: 4,5:1', (variante, estado) => {
    render(
      <ConfigProvider theme={configDoTemaClaro()}>
        <Button danger type="text">
          Excluir
        </Button>
        <Button danger type="link">
          Excluir
        </Button>
        <Button danger>Excluir</Button>
        <Button danger type="primary">
          Excluir
        </Button>
      </ConfigProvider>,
    );
    const { cor, fundo } = estiloDoBotaoDanger(variante, estado);
    // Sem fundo na regra (link e contorno): mede no branco, na página e no cartão do login.
    const fundos = fundo ? [fundo] : ['#ffffff', BRAND_COLORS.pageBackground, BRAND_COLORS.primaryLight];
    for (const f of fundos) {
      expect(contraste(cor, f), `${variante} ${estado}: ${cor} sobre ${f}`).toBeGreaterThanOrEqual(4.5);
    }
  });
});

/** Cor do texto e fundo próprio do botão danger nesta variante e neste estado, no CSS que o AntD gerou. */
function estiloDoBotaoDanger(
  variante: 'text' | 'link' | 'outlined' | 'solid',
  estado: 'hover' | 'active',
): { cor: string; fundo: string | undefined } {
  const alvo = `.ant-btn-color-dangerous.ant-btn-variant-${variante}:not(:disabled):not(.ant-btn-disabled):${estado}`;
  const regra = Array.from(document.styleSheets)
    .flatMap((folha) => Array.from(folha.cssRules))
    .filter((r): r is CSSStyleRule => 'selectorText' in r)
    .find((r) => r.selectorText.split(',').some((s) => s.trim().endsWith(alvo)));
  if (!regra) throw new Error(`o AntD não gerou regra para: ${alvo}`);
  const fundo = regra.style.getPropertyValue('background-color') || regra.style.getPropertyValue('background') || undefined;
  // Botão cheio: o texto é branco sobre o fundo da regra.
  return { cor: variante === 'solid' ? '#ffffff' : regra.style.getPropertyValue('color'), fundo };
}

// `?raw` de CSS volta vazio no Vitest (CSS desligado): lê o arquivo do disco.
const lerCss = (arquivo: string): string =>
  readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), '../..', arquivo), 'utf-8');
const appCss = lerCss('App.css');
const indexCss = lerCss('index.css');

/**
 * Valor da propriedade na regra que lista exatamente este seletor. Com `bloco` (ex.: '@layer base'),
 * procura só dentro dele; sem, só no nível de cima da folha.
 */
function valorNoCss(css: string, seletor: string, propriedade: string, bloco?: string): string {
  const folha = document.createElement('style');
  folha.textContent = css;
  document.head.appendChild(folha);
  try {
    let regras = Array.from(folha.sheet?.cssRules ?? []);
    if (bloco) {
      const grupo = regras.find((r) => r.cssText.startsWith(`${bloco} `)) as CSSGroupingRule | undefined;
      regras = Array.from(grupo?.cssRules ?? []);
    }
    const regra = regras
      .filter((r): r is CSSStyleRule => 'selectorText' in r)
      .find((r) => r.selectorText.split(',').map((s) => s.trim()).includes(seletor));
    if (!regra) throw new Error(`sem regra${bloco ? ` em ${bloco}` : ''} para: ${seletor}`);
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
