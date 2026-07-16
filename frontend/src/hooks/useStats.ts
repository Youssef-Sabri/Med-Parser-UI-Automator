import { useEffect, useState, useCallback } from 'react';
import { getStats } from '../services/api';
import type { Stats } from '../types';

const STATS_POLL_INTERVAL_MS = 30_000;

export function useStats(): Stats | null {
  const [stats, setStats] = useState<Stats | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      const data = await getStats();
      setStats({ ...data, daily_capacity: data.daily_capacity ?? 200 });
    } catch (err) {
      console.error('Failed to fetch stats', err);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, STATS_POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchStats]);

  return stats;
}
