/**
 * "Carregando..." de tela cheia com contraste AA (WCAG 1.4.3, 4,5:1).
 *
 * O AntD pinta o texto em branco (colorTextLightSolid) sobre a máscara (colorBgMask), que é
 * translúcida. A máscara padrão, rgba(0,0,0,0.45), sobre a página branca vira #8c8c8c e o
 * texto dá 3,36:1. A página branca é o pior caso (no tema claro o <body> não tem fundo; no
 * escuro ele é #141414): qualquer fundo mais escuro só aumenta o contraste. O teste mede a cor
 * que o AntD realmente aplica, sobre o branco, sozinho (boot, fora do ConfigProvider) e nos
 * dois temas do app.
 */
import { render, screen } from '@testing-library/react';
import { ConfigProvider, theme } from 'antd';
import type { ReactNode } from 'react';
import { describe, expect, test } from 'vitest';

import { FullscreenLoader } from '../FullscreenLoader';

type Rgba = [number, number, number, number];

/** `rgb(...)`/`rgba(...)` (como o CSSOM devolve) para [r, g, b, a]. */
function rgbaDe(cor: string): Rgba {
  const m = /rgba?\(([^)]*)\)/.exec(cor);
  if (!m) throw new Error(`cor inesperada: "${cor}"`);
  const [r, g, b, a = 1] = m[1]!.split(',').map((n) => Number(n.trim()));
  return [r!, g!, b!, a];
}

/** Compõe a cor translúcida sobre um fundo opaco. */
function sobre([r, g, b, a]: Rgba, fundo: [number, number, number]): [number, number, number] {
  return [r * a + fundo[0] * (1 - a), g * a + fundo[1] * (1 - a), b * a + fundo[2] * (1 - a)];
}

/** Luminância relativa (WCAG 2.x). */
function luminancia(rgb: [number, number, number]): number {
  const [r, g, b] = rgb.map((v) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!;
}

function contraste(a: [number, number, number], b: [number, number, number]): number {
  const [claro, escuro] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (claro! + 0.05) / (escuro! + 0.05);
}

const BRANCO: [number, number, number] = [255, 255, 255];

const CENARIOS: [string, (filho: ReactNode) => ReactNode][] = [
  ['boot, fora do ConfigProvider', (filho) => filho],
  ['tema claro', (filho) => <ConfigProvider theme={{ algorithm: theme.defaultAlgorithm }}>{filho}</ConfigProvider>],
  ['tema escuro', (filho) => <ConfigProvider theme={{ algorithm: theme.darkAlgorithm }}>{filho}</ConfigProvider>],
];

describe('FullscreenLoader — contraste do "Carregando..."', () => {
  test.each(CENARIOS)('%s: texto sobre a máscara (na página branca) dá 4,5:1 ou mais', (_cenario, envolver) => {
    render(<>{envolver(<FullscreenLoader />)}</>);

    const texto = screen.getByText('Carregando...');
    const mascara = texto.closest('.ant-spin-fullscreen');
    expect(mascara).not.toBeNull();

    const fundo = sobre(rgbaDe(getComputedStyle(mascara!).backgroundColor), BRANCO);
    const corDoTexto = sobre(rgbaDe(getComputedStyle(texto).color), fundo);
    expect(contraste(corDoTexto, fundo)).toBeGreaterThanOrEqual(4.5);
  });
});
