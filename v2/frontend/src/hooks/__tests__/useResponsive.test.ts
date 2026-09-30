/**
 * useResponsive — modo da sidebar pela largura da janela (Programa C, C1):
 * - abaixo de 992 px (LAYOUT.TABLET_BREAKPOINT, o `lg` do AntD): 'sobreposta' — fechada,
 *   abre por cima do conteúdo, que ocupa a largura toda;
 * - de 992 a 1279 px: 'recolhida' — só os ícones (80 px);
 * - a partir de 1280 px (LAYOUT.DESKTOP_BREAKPOINT): 'aberta' (250 px).
 *
 * O resize só mexe em `sidebarCollapsed` quando o modo muda; dentro do mesmo modo a
 * preferência manual (toggleSidebar) fica.
 */
import { act, renderHook } from '@testing-library/react';
import { describe, expect, test } from 'vitest';
import { useResponsive } from '../useResponsive';
import { LAYOUT } from '../../constants';
import { definirLarguraTela } from '../../test/larguraTela';

function resizeTo(px: number): void {
  act(() => definirLarguraTela(px));
}

describe('useResponsive', () => {
  test('os limites são o lg do AntD (992) e o desktop (1280)', () => {
    expect(LAYOUT.TABLET_BREAKPOINT).toBe(992);
    expect(LAYOUT.DESKTOP_BREAKPOINT).toBe(1280);
  });

  test.each([
    [360, 'sobreposta', true],
    [768, 'sobreposta', true],
    [991, 'sobreposta', true],
    [992, 'recolhida', true],
    [1024, 'recolhida', true],
    [1279, 'recolhida', true],
    [1280, 'aberta', false],
    [1600, 'aberta', false],
  ] as const)('a %i px o modo inicial é %s (recolhida=%s)', (largura, modo, recolhida) => {
    definirLarguraTela(largura);
    const { result } = renderHook(() => useResponsive());

    expect(result.current.modo).toBe(modo);
    expect(result.current.sidebarCollapsed).toBe(recolhida);
  });

  test('aberta → recolhida recolhe; recolhida → aberta abre', () => {
    const { result } = renderHook(() => useResponsive());
    expect(result.current.modo).toBe('aberta');

    resizeTo(1024);
    expect(result.current.modo).toBe('recolhida');
    expect(result.current.sidebarCollapsed).toBe(true);

    resizeTo(1366);
    expect(result.current.modo).toBe('aberta');
    expect(result.current.sidebarCollapsed).toBe(false);
  });

  test('recolhida → sobreposta fecha a que o usuário abriu', () => {
    definirLarguraTela(1024);
    const { result } = renderHook(() => useResponsive());
    act(() => result.current.toggleSidebar());
    expect(result.current.sidebarCollapsed).toBe(false);

    resizeTo(800);

    expect(result.current.modo).toBe('sobreposta');
    expect(result.current.sidebarCollapsed).toBe(true);
  });

  test('resize dentro do mesmo modo preserva a preferência manual', () => {
    const { result } = renderHook(() => useResponsive());
    act(() => result.current.toggleSidebar());
    expect(result.current.sidebarCollapsed).toBe(true);

    resizeTo(1500);

    expect(result.current.modo).toBe('aberta');
    expect(result.current.sidebarCollapsed).toBe(true);
  });

  test('toggleSidebar alterna o estado sem depender de resize', () => {
    definirLarguraTela(360);
    const { result } = renderHook(() => useResponsive());
    expect(result.current.sidebarCollapsed).toBe(true);

    act(() => result.current.toggleSidebar());
    expect(result.current.sidebarCollapsed).toBe(false);

    act(() => result.current.toggleSidebar());
    expect(result.current.sidebarCollapsed).toBe(true);
  });
});
