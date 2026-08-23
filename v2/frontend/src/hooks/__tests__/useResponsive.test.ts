/**
 * useResponsive — breakpoint mobile (window.innerWidth vs LAYOUT.MOBILE_BREAKPOINT)
 * + auto-toggle do sidebar SÓ na transição real mobile↔desktop.
 *
 * O contrato é: o resize atualiza `isMobile` sempre, mas só mexe em
 * `sidebarCollapsed` quando o regime realmente cruza o breakpoint — assim a
 * preferência manual do usuário (toggleSidebar) não é sobrescrita a cada resize.
 */
import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, test } from 'vitest';
import { useResponsive } from '../useResponsive';
import { LAYOUT } from '../../constants';

const DESKTOP = LAYOUT.MOBILE_BREAKPOINT + 200; // 968 → desktop
const DESKTOP_ALT = LAYOUT.MOBILE_BREAKPOINT + 400; // 1168 → ainda desktop
const MOBILE = LAYOUT.MOBILE_BREAKPOINT - 200; // 568 → mobile

const originalInnerWidth = window.innerWidth;

/** Define a largura da janela ANTES do render (estado inicial do hook). */
function setInnerWidth(value: number): void {
  Object.defineProperty(window, 'innerWidth', {
    configurable: true,
    writable: true,
    value,
  });
}

/** Muda a largura e dispara `resize` dentro de act (efeito do hook roda). */
function resizeTo(value: number): void {
  act(() => {
    setInnerWidth(value);
    window.dispatchEvent(new Event('resize'));
  });
}

afterEach(() => {
  setInnerWidth(originalInnerWidth);
});

describe('useResponsive', () => {
  test('inicial desktop: não é mobile e sidebar aberto', () => {
    setInnerWidth(DESKTOP);
    const { result } = renderHook(() => useResponsive());

    expect(result.current.isMobile).toBe(false);
    expect(result.current.sidebarCollapsed).toBe(false);
  });

  test('inicial mobile: é mobile e sidebar colapsado', () => {
    setInnerWidth(MOBILE);
    const { result } = renderHook(() => useResponsive());

    expect(result.current.isMobile).toBe(true);
    expect(result.current.sidebarCollapsed).toBe(true);
  });

  test('transição desktop→mobile colapsa o sidebar', () => {
    setInnerWidth(DESKTOP);
    const { result } = renderHook(() => useResponsive());
    expect(result.current.sidebarCollapsed).toBe(false);

    resizeTo(MOBILE);

    expect(result.current.isMobile).toBe(true);
    expect(result.current.sidebarCollapsed).toBe(true);
  });

  test('transição mobile→desktop expande o sidebar', () => {
    setInnerWidth(MOBILE);
    const { result } = renderHook(() => useResponsive());
    expect(result.current.sidebarCollapsed).toBe(true);

    resizeTo(DESKTOP);

    expect(result.current.isMobile).toBe(false);
    expect(result.current.sidebarCollapsed).toBe(false);
  });

  test('resize sem cruzar o breakpoint preserva a preferência manual', () => {
    setInnerWidth(DESKTOP);
    const { result } = renderHook(() => useResponsive());

    // Usuário colapsa manualmente em desktop.
    act(() => {
      result.current.toggleSidebar();
    });
    expect(result.current.sidebarCollapsed).toBe(true);

    // Resize dentro do regime desktop NÃO deve mexer no sidebar.
    resizeTo(DESKTOP_ALT);

    expect(result.current.isMobile).toBe(false);
    expect(result.current.sidebarCollapsed).toBe(true);
  });

  test('toggleSidebar alterna o estado sem depender de resize', () => {
    setInnerWidth(DESKTOP);
    const { result } = renderHook(() => useResponsive());
    expect(result.current.sidebarCollapsed).toBe(false);

    act(() => {
      result.current.toggleSidebar();
    });
    expect(result.current.sidebarCollapsed).toBe(true);

    act(() => {
      result.current.toggleSidebar();
    });
    expect(result.current.sidebarCollapsed).toBe(false);
  });
});
