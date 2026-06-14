/**
 * Public type definitions for the TokenUsage components.
 */

export interface ModelPrice {
  /** USD per 1M prompt tokens. */
  promptPer1M: number;
  /** USD per 1M completion tokens. */
  completionPer1M: number;
}

/** Map model id → pricing. Used to compute cost from token counts. */
export type ModelPriceMap = Record<string, ModelPrice>;

export interface UsageBucket {
  /** Bucket key (e.g. model id, provider id, date YYYY-MM-DD, agent id). */
  key: string;
  /** Human-readable label. Defaults to `key`. */
  label?: string;
  promptTokens: number;
  completionTokens: number;
  callCount?: number;
  /** Pre-computed cost in USD. If omitted, derived from prices map. */
  costUsd?: number;
}

export interface TokenUsageMeterProps {
  promptTokens: number;
  completionTokens: number;
  /** Optional cap (e.g. session budget). Drives the progress bar. */
  budgetTokens?: number;
  /** Optional explicit cost. If omitted and `costUsd` undefined, no cost shown. */
  costUsd?: number;
  /** Optional sparkline data (most recent point last). */
  sparkline?: number[];
  callCount?: number;
  /** Time label (e.g. "Last 24h"). */
  windowLabel?: string;
  className?: string;
  style?: React.CSSProperties;
  compact?: boolean;
}

export type CostBreakdownChartKind = "donut" | "stackedBar";

export interface CostBreakdownChartProps {
  buckets: UsageBucket[];
  /** Optional pricing map used when `bucket.costUsd` is missing. */
  prices?: ModelPriceMap;
  /** Visualization style. Default: "donut". */
  kind?: CostBreakdownChartKind;
  /** Total height. Default: 260. */
  height?: number | string;
  /** Top-N buckets shown; rest grouped as "Other". Default: 8. */
  topN?: number;
  title?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  /** What the buckets represent — only used for the legend hint. */
  dimension?: "model" | "provider" | "agent" | "date" | "custom";
}
