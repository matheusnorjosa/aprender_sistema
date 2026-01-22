/**
 * Tests for useSessionMonitor hook.
 *
 * @see useSessionMonitor.js
 */

import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import useSessionMonitor from '../useSessionMonitor';
import api from '../../api';

vi.mock('../../api');

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

    // Initial timeLeft should be close to sessionAge (7200s)
    expect(result.current.timeLeft).toBeLessThanOrEqual(7200);
    expect(result.current.timeLeft).toBeGreaterThan(7100);
  });

  it('renewSession updates session and returns true on success', async () => {
    api.post.mockResolvedValue({
      data: { session_age: 7200 },
    });

    const { result } = renderHook(() => useSessionMonitor());

    let success;
    await act(async () => {
      success = await result.current.renewSession();
    });

    expect(success).toBe(true);
    expect(api.post).toHaveBeenCalledWith('/auth/ping/');
    expect(result.current.showWarning).toBe(false);
  });

  it('renewSession returns false on API error', async () => {
    api.post.mockRejectedValue(new Error('Network error'));

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

    api.post.mockRejectedValue({
      response: { status: 401 },
    });

    const { result } = renderHook(() => useSessionMonitor());

    await act(async () => {
      await result.current.renewSession();
    });

    expect(window.location.href).toBe('/login');

    window.location = originalLocation;
  });

  it('shows warning when time left is below threshold', async () => {
    const { result } = renderHook(() => useSessionMonitor());

    // Advance time to near expiration (7200 - 300 = 6900 seconds + 60s for interval)
    await act(async () => {
      vi.advanceTimersByTime((6900 + 60) * 1000);
    });

    // Assertion direta após os timers serem processados
    expect(result.current.showWarning).toBe(true);
  });
});
