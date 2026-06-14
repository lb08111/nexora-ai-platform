# TokenUsageDashboard

Reusable visual components for showing LLM token consumption and cost.

Includes:

- **`TokenUsageMeter`** — compact summary card with prompt/completion split, optional cost, optional sparkline and optional budget bar.
- **`CostBreakdownChart`** — donut or stacked-bar showing cost (or tokens) per model / provider / agent / date.
- **`useTokenUsage`** — convenience hook that calls `tokenUsageApi.getTokenUsage` and shapes the data for both components.

All components are self-contained: only `react`, `antd`, and `lucide-react`. No chart library required.

---

## Quick start

```tsx
import {
  TokenUsageMeter,
  CostBreakdownChart,
  useTokenUsage,
} from "@/components/TokenUsageDashboard";

export function UsagePanel() {
  const usage = useTokenUsage({ refreshMs: 30_000 });

  if (!usage.summary) return <div>Loading…</div>;

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <TokenUsageMeter
        promptTokens={usage.summary.total_prompt_tokens}
        completionTokens={usage.summary.total_completion_tokens}
        callCount={usage.summary.total_calls}
        sparkline={usage.dailySeries}
        windowLabel="Last 7 days"
        budgetTokens={5_000_000}
      />
      <CostBreakdownChart
        buckets={usage.byModelBuckets}
        dimension="model"
        kind="donut"
      />
      <CostBreakdownChart
        buckets={usage.byDateBuckets}
        dimension="date"
        kind="stackedBar"
        height={300}
      />
    </div>
  );
}
```

## Standalone usage (no API hook)

You can drive the components with any data — just shape it into `UsageBucket`:

```tsx
<CostBreakdownChart
  buckets={[
    { key: "gpt-4o", promptTokens: 12_000, completionTokens: 3_200, callCount: 42 },
    { key: "claude-3-5-sonnet", promptTokens: 7_400, completionTokens: 1_500 },
  ]}
/>
```

## Pricing

Cost is computed automatically using a built-in default pricing table
(`DEFAULT_PRICES`) when the bucket has no `costUsd`. Override or extend:

```tsx
<CostBreakdownChart
  buckets={byModel}
  prices={{
    "my-private-model": { promptPer1M: 0.10, completionPer1M: 0.20 },
  }}
/>
```

Or pre-compute and pass `costUsd` on each bucket to skip the lookup entirely.

## Props

### `TokenUsageMeter`

| Prop | Type | Description |
| --- | --- | --- |
| `promptTokens` | `number` | required |
| `completionTokens` | `number` | required |
| `costUsd` | `number?` | shows a $-value column |
| `budgetTokens` | `number?` | enables the progress bar |
| `sparkline` | `number[]?` | small inline trend chart |
| `callCount` | `number?` | shown in legend |
| `windowLabel` | `string?` | e.g. `"Last 24h"` |
| `compact` | `boolean?` | tighter padding |

### `CostBreakdownChart`

| Prop | Type | Description |
| --- | --- | --- |
| `buckets` | `UsageBucket[]` | required |
| `kind` | `"donut" \| "stackedBar"` | default `donut` |
| `prices` | `ModelPriceMap?` | merged on top of `DEFAULT_PRICES` |
| `topN` | `number?` | rest grouped as "Other". Default 8 |
| `height` | `number \| string?` | default 260 |
| `dimension` | `"model" \| "provider" \| "agent" \| "date" \| "custom"` | label hint only |

A built-in **Cost / Tokens** toggle lets the user switch metrics.

## Dark mode

Inherits `--colorBgContainer`, `--colorBorderSecondary`, `--colorText*`, `--colorPrimary`, `--colorSuccess` etc.
Adapts automatically when the root has the `dark-mode` class.