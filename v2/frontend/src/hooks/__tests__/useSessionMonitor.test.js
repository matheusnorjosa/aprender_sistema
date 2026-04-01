/**
 * Tests for useSessionMonitor hook.
 * Migrated from axios mock to fetchAPI mock (Epic #1039)
 */

import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

const fetchAPIMock = vi.hoisted(() => vi.fn());

vi.mock('../../api/config', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, fetchAPI: fetchAPIMock };
});

import useSessionMonitor from '../useSessionMonitor';

describe('useSessionMonitor', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('initializes with default values', () => {
    const { result } = renderHook(() => useSessionMonitor());

    expect(result.current.sessionAge).toBe(7200);
    expect(result.current.showWarning).toBe(false);
    expect(result.current.timeLeft).toBeGreaterThan(0);
  });

  it('calculates timeLeft correctly', () => {
    const { result } = renderHook(() => useSessionMonitor());

    expect(result.current.timeLeft).toBeLessThanOrEqual(7200);
    expect(result.current.timeLeft).toBeGreaterThan(7100);
  });

  it('renewSession updates session and returns true on success', async () => {
    fetchAPIMock.mockResolvedValue({ session_age: 7200 });

    const { result } = renderHook(() => useSessionMonitor());

    let success;
    await act(async () => {
      success = await result.current.renewSession();
    });

    expect(success).toBe(true);
    expect(fetchAPIMock).toHaveBeenCalledWith('/auth/ping/', { method: 'POST' });
    expect(result.current.showWarning).toBe(false);
  });

  it('renewSession returns false on API error', async () => {
    fetchAPIMock.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useSessionMonitor());

    let success;
    await act(async () => {
      success = await result.current.renewSession();
    });

    expect(success).toBe(false);
  });

  it('renewSession redirects to login on 401', async () => {
    const originalLocation = window.location;
    delete window.location;
    window.location = { href: '' };

    fetchAPIMock.mockRejectedValue({ response: { status: 401 } });

    const { result } = renderHook(() => useSessionMonitor());

    await act(async () => {
      await result.current.renewSession();
    });

    expect(window.location.href).toBe('/login');

    window.location = originalLocation;
  });

  it('shows warning when time left is below threshold', async () => {
    const { result } = renderHook(() => useSessionMonitor());

    await act(async () => {
      vi.advanceTimersByTime(6960 * 1000);
    });

    expect(result.current.showWarning).toBe(true);
  });
});
