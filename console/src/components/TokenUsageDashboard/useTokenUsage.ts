import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { tokenUsageApi } from "../../api/modules/tokenUsage";
import type {
  TokenUsageSummary,
  TokenUsageStats,
} from "../../api/types/tokenUsage";
import type { UsageBucket } from "./types";

export interface UseTokenUsageOptions {
  /** ISO date YYYY-MM-DD (inclusive). Defaults to today - 7d. */
  startDate?: string;
  /** ISO date YYYY-MM-DD (inclusive). Defaults to today. */
  endDate?: string;
  /** Filter to a single model. */
  model?: string;
  /** Filter to a single provider. */
  provider?: string;
  /** Poll interval in ms. 0/undefined disables polling. */
  refreshMs?: number;
}

export interface UseTokenUsageResult {
  summary: TokenUsageSummary | null;
  loading: boolean;
  error: string | null;
  /** Aggregated rows ready for CostBreakdownChart, grouped by model key. */
  byModelBuckets: UsageBucket[];
  /** Aggregated rows by date (key = YYYY-MM-DD). */
  byDateBuckets: UsageBucket[];
  /** Daily token totals (prompt + completion) sorted by date — for the sparkline. */
  dailySeries: number[];
  refresh: () => void;
}

function todayIso(offsetDays = 0): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

function statsToBucket(key: string, stats: TokenUsageStats): UsageBucket {
  return {
    key,
    promptTokens: stats.prompt_tokens,
    completionTokens: stats.completion_tokens,
    callCount: stats.call_count,
  };
}

/**
 * Reactive hook that loads token usage from the backend and shapes it for
 * `TokenUsageMeter` and `CostBreakdownChart`.
 */
export function useTokenUsage(
  options: UseTokenUsageOptions = {},
): UseTokenUsageResult {
  const {
    startDate = todayIso(-7),
    endDate = todayIso(0),
    model,
    provider,
    refreshMs,
  } = options;

  const [summary, setSummary] = useState<TokenUsageSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reqIdRef = useRef(0);

  const load = useCallback(async () => {
    const reqId = ++reqIdRef.current;
    setLoading(true);
    setError(null);
    try {
      const data = await tokenUsageApi.getTokenUsage({
        start_date: startDate,
        end_date: endDate,
        model,
        provider,
      });
      if (reqId === reqIdRef.current) setSummary(data);
    } catch (e) {
      if (reqId === reqIdRef.current) {
        setError(e instanceof Error ? e.message : "Failed to load token usage");
      }
    } finally {
      if (reqId === reqIdRef.current) setLoading(false);
    }
  }, [startDate, endDate, model, provider]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!refreshMs || refreshMs <= 0) return undefined;
    const id = window.setInterval(() => void load(), refreshMs);
    return () => window.clearInterval(id);
  }, [refreshMs, load]);

  const byModelBuckets = useMemo<UsageBucket[]>(() => {
    if (!summary) return [];
    return Object.entries(summary.by_model).map(([key, stats]) =>
      statsToBucket(stats.model ?? key, stats),
    );
  }, [summary]);

  const byDateBuckets = useMemo<UsageBucket[]>(() => {
    if (!summary) return [];
    return Object.entries(summary.by_date)
      .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
      .map(([key, stats]) => statsToBucket(key, stats));
  }, [summary]);

  const dailySeries = useMemo<number[]>(
    () => byDateBuckets.map((b) => b.promptTokens + b.completionTokens),
    [byDateBuckets],
  );

  return {
    summary,
    loading,
    error,
    byModelBuckets,
    byDateBuckets,
    dailySeries,
    refresh: () => void load(),
  };
}