import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useScheduledRun } from '../../hooks/useScheduledRun';

// Mock fetch globally
global.fetch = vi.fn();

describe('useScheduledRun', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should fetch scheduled run data on mount', async () => {
    const mockData = {
      enabled: true,
      next_run_at: '2025-07-16T16:46:18.828267+00:00',
      interval_hours: 24,
      time_remaining_seconds: 43200,
      time_remaining_human: '12h 0m'
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockData
    });

    const { result } = renderHook(() => useScheduledRun());

    // Initially loading
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBe(null);
    expect(result.current.error).toBe(null);

    // Wait for the hook to fetch data
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    }, { timeout: 3000 });

    expect(result.current.data).toEqual(mockData);
    expect(result.current.error).toBe(null);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/scheduler/next-run')
    );
  });

  it('should handle fetch errors', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 500
    });

    const { result } = renderHook(() => useScheduledRun());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    }, { timeout: 3000 });

    expect(result.current.data).toBe(null);
    expect(result.current.error).toBe('HTTP error! status: 500');
  });

  it('should handle network errors', async () => {
    (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useScheduledRun());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    }, { timeout: 3000 });

    expect(result.current.data).toBe(null);
    expect(result.current.error).toBe('Network error');
  });

  it('should call fetch initially', async () => {
    const mockData = {
      enabled: true,
      next_run_at: '2025-07-16T16:46:18.828267+00:00',
      interval_hours: 24,
      time_remaining_seconds: 43200,
      time_remaining_human: '12h 0m'
    };

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => mockData
    });

    const { result } = renderHook(() => useScheduledRun());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    }, { timeout: 3000 });

    // Should have called fetch at least once on mount
    expect(global.fetch).toHaveBeenCalled();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/scheduler/next-run')
    );
  });

  it('should provide refresh function', async () => {
    const mockData = {
      enabled: true,
      next_run_at: '2025-07-16T16:46:18.828267+00:00',
      interval_hours: 24,
      time_remaining_seconds: 43200,
      time_remaining_human: '12h 0m'
    };

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => mockData
    });

    const { result } = renderHook(() => useScheduledRun());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    }, { timeout: 3000 });

    const initialCallCount = (global.fetch as any).mock.calls.length;

    // Call refresh function
    await result.current.refresh();

    // Should have made one more call
    expect(global.fetch).toHaveBeenCalledTimes(initialCallCount + 1);
  });

  it('should handle disabled scheduler', async () => {
    const mockData = {
      enabled: false,
      next_run_at: null,
      interval_hours: 24
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockData
    });

    const { result } = renderHook(() => useScheduledRun());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    }, { timeout: 3000 });

    expect(result.current.data).toEqual(mockData);
    expect(result.current.data?.time_remaining_seconds).toBeUndefined();
    expect(result.current.data?.time_remaining_human).toBeUndefined();
  });
});