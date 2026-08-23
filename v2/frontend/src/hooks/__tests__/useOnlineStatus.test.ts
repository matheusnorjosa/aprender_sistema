/**
 * useOnlineStatus — reflete navigator.onLine + eventos window online/offline (#416).
 *
 * O hook lê navigator.onLine no mount e depois escuta os eventos 'online'/'offline'
 * do window. No unmount os listeners são removidos (nenhum setState após desmontar).
 */
import { renderHook, act } from '@testing-library/react';
import { afterEach, describe, expect, test } from 'vitest';
import { useOnlineStatus } from '../useOnlineStatus';

const onLineOriginal = Object.getOwnPropertyDescriptor(
  Navigator.prototype,
  'onLine'
);

function setOnLine(value: boolean): void {
  Object.defineProperty(navigator, 'onLine', { configurable: true, value });
}

describe('useOnlineStatus', () => {
  afterEach(() => {
    // Restaura o navigator.onLine original entre os testes.
    if (onLineOriginal) {
      Object.defineProperty(Navigator.prototype, 'onLine', onLineOriginal);
    }
    delete (navigator as { onLine?: boolean }).onLine;
  });

  test('estado inicial reflete navigator.onLine=false', () => {
    setOnLine(false);
    const { result } = renderHook(() => useOnlineStatus());
    expect(result.current).toBe(false);
  });

  test('estado inicial reflete navigator.onLine=true', () => {
    setOnLine(true);
    const { result } = renderHook(() => useOnlineStatus());
    expect(result.current).toBe(true);
  });

  test('evento offline vira false; evento online vira true', () => {
    setOnLine(true);
    const { result } = renderHook(() => useOnlineStatus());
    expect(result.current).toBe(true);

    act(() => {
      window.dispatchEvent(new Event('offline'));
    });
    expect(result.current).toBe(false);

    act(() => {
      window.dispatchEvent(new Event('online'));
    });
    expect(result.current).toBe(true);
  });

  test('após unmount os listeners são removidos (disparar evento não lança)', () => {
    setOnLine(true);
    const { result, unmount } = renderHook(() => useOnlineStatus());
    expect(result.current).toBe(true);

    unmount();

    expect(() => {
      act(() => {
        window.dispatchEvent(new Event('offline'));
      });
    }).not.toThrow();
    // O valor final (último render) permanece o de antes do unmount.
    expect(result.current).toBe(true);
  });
});
