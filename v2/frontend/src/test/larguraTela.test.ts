/**
 * O mock de matchMedia do setup (src/test/larguraTela.ts) é contrato de toda a suíte:
 * as colunas do ResponsiveTable dependem dele para existir nos testes.
 */
import { describe, expect, test, vi } from 'vitest';

import { LARGURA_PADRAO, avaliarMidia, definirLarguraTela } from './larguraTela';

describe('mock de matchMedia por largura', () => {
  test('o padrão é 1280 px: desktop, com as quebras do AntD até xl', () => {
    expect(LARGURA_PADRAO).toBe(1280);
    expect(window.innerWidth).toBe(1280);
    expect(window.matchMedia('(min-width: 1200px)').matches).toBe(true);
    expect(window.matchMedia('(min-width: 1600px)').matches).toBe(false);
    expect(window.matchMedia('(max-width: 575px)').matches).toBe(false);
  });

  test('avalia min-width, max-width e "and"; o que não é largura dá false', () => {
    expect(avaliarMidia('(min-width: 576px)', 576)).toBe(true);
    expect(avaliarMidia('(min-width: 576px)', 575)).toBe(false);
    expect(avaliarMidia('(max-width: 575px)', 575)).toBe(true);
    expect(avaliarMidia('screen and (min-width: 768px) and (max-width: 991.98px)', 800)).toBe(true);
    expect(avaliarMidia('screen and (min-width: 768px) and (max-width: 991.98px)', 992)).toBe(false);
    expect(avaliarMidia('(prefers-color-scheme: dark)', 1280)).toBe(false);
    expect(avaliarMidia('(prefers-reduced-motion: reduce)', 1280)).toBe(false);
  });

  test('definirLarguraTela muda innerWidth e as queries e avisa só quem mudou de estado', () => {
    const md = window.matchMedia('(min-width: 768px)');
    const xl = window.matchMedia('(min-width: 1200px)');
    const ouvinteMd = vi.fn();
    const ouvinteXl = vi.fn();
    md.addEventListener('change', ouvinteMd);
    xl.addListener(ouvinteXl);
    const resize = vi.fn();
    window.addEventListener('resize', resize);

    definirLarguraTela(1024);

    expect(window.innerWidth).toBe(1024);
    expect(md.matches).toBe(true);
    expect(xl.matches).toBe(false);
    expect(ouvinteMd).not.toHaveBeenCalled();
    expect(ouvinteXl).toHaveBeenCalledWith({ matches: false, media: '(min-width: 1200px)' });
    expect(resize).toHaveBeenCalledTimes(1);

    xl.removeListener(ouvinteXl);
    md.removeEventListener('change', ouvinteMd);
    window.removeEventListener('resize', resize);
  });

  test('o setup devolve a largura padrão antes de cada teste', () => {
    expect(window.innerWidth).toBe(LARGURA_PADRAO);
  });
});
