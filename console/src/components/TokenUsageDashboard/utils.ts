import type { ModelPriceMap, UsageBucket } from "./types";

/** Best-effort default pricing in USD per 1M tokens (Nov 2024 list prices). */
export const DEFAULT_PRICES: ModelPriceMap = {
  "gpt-4o": { promptPer1M: 2.5, completionPer1M: 10.0 },
  "gpt-4o-mini": { promptPer1M: 0.15, completionPer1M: 0.6 },
  "gpt-4-turbo": { promptPer1M: 10.0, completionPer1M: 30.0 },
  "gpt-3.5-turbo": { promptPer1M: 0.5, completionPer1M: 1.5 },
  o1: { promptPer1M: 15.0, completionPer1M: 60.0 },
  "o1-mini": { promptPer1M: 3.0, completionPer1M: 12.0 },
  "claude-3-5-sonnet": { promptPer1M: 3.0, completionPer1M: 15.0 },
  "claude-3-5-haiku": { promptPer1M: 0.8, completionPer1M: 4.0 },
  "claude-3-opus": { promptPer1M: 15.0, completionPer1M: 75.0 },
  "gemini-1.5-pro": { promptPer1M: 1.25, completionPer1M: 5.0 },
  "gemini-1.5-flash": { promptPer1M: 0.075, completionPer1M: 0.3 },
  "qwen-max": { promptPer1M: 1.6, completionPer1M: 6.4 },
  "qwen-plus": { promptPer1M: 0.4, completionPer1M: 1.2 },
  "qwen-turbo": { promptPer1M: 0.3, completionPer1M: 0.6 },
};

export function lookupPrice(
  model: string,
  prices: ModelPriceMap,
): { promptPer1M: number; completionPer1M: number } {
  if (prices[model]) return prices[model];
  // Try lowercased / known prefix match
  const lower = model.toLowerCase();
  const hit = Object.keys(prices).find((k) => lower.includes(k.toLowerCase()));
  if (hit) return prices[hit];
  return { promptPer1M: 0, completionPer1M: 0 };
}

export function computeBucketCost(
  bucket: UsageBucket,
  prices: ModelPriceMap,
): number {
  if (typeof bucket.costUsd === "number") return bucket.costUsd;
  const p = lookupPrice(bucket.key, prices);
  return (
    (bucket.promptTokens * p.promptPer1M) / 1_000_000 +
    (bucket.completionTokens * p.completionPer1M) / 1_000_000
  );
}

export function formatTokens(n: number): string {
  if (!Number.isFinite(n)) return "—";
  const abs = Math.abs(n);
  if (abs >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2)}B`;
  if (abs >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toLocaleString();
}

export function formatUsd(n: number): string {
  if (!Number.isFinite(n)) return "—";
  if (Math.abs(n) >= 100) return `$${n.toFixed(0)}`;
  if (Math.abs(n) >= 1) return `$${n.toFixed(2)}`;
  if (Math.abs(n) >= 0.01) return `$${n.toFixed(3)}`;
  return `$${n.toFixed(4)}`;
}

/** Deterministic color from string (hash → HSL). */
export function colorFor(key: string): string {
  let h = 0;
  for (let i = 0; i < key.length; i += 1) {
    h = (h * 31 + key.charCodeAt(i)) | 0;
  }
  const hue = Math.abs(h) % 360;
  return `hsl(${hue}, 65%, 55%)`;
}
