import { useState, useEffect } from 'react';
import { API_BASE } from '../utils/apiBase';

interface ScheduledRunData {
  enabled: boolean;
  next_run_at: string | null;
  interval_hours: number;
  time_remaining_seconds?: number;
  time_remaining_human?: string;
}

export const useScheduledRun = () => {
  const [data, setData] = useState<ScheduledRunData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchScheduledRunData = async () => {
    try {
      setError(null);
      const response = await fetch(`${API_BASE}/api/scheduler/next-run`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScheduledRunData();
    
    // Refresh every 30 seconds to keep countdown accurate
    const interval = setInterval(fetchScheduledRunData, 30000);
    
    return () => clearInterval(interval);
  }, []);

  return { data, loading, error, refresh: fetchScheduledRunData };
};