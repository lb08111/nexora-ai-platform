import React, { useMemo, useState } from "react";
import { Tooltip } from "antd";
import type { CostBreakdownChartProps, UsageBucket } from "./types";
import {
  DEFAULT_PRICES,
  colorFor,
  computeBucketCost,
  formatTokens,
  formatUsd,
} from "./utils";
import styles from "./index.module.less";

interface ResolvedBucket extends UsageBucket {
  cost: number;
  color: string;
}

function resolveBuckets(
  buckets: UsageBucket[],
  prices: Record<string, { promptPer1M: number; completionPer1M: number }>,
  topN: number,
): ResolvedBucket[] {
  const enriched = buckets.map<ResolvedBucket>((b) => ({
    ...b,
    cost: computeBucketCost(b, prices),
    color: colorFor(b.key),
  }));
  enriched.sort((a, b) => b.cost - a.cost || b.promptTokens + b.completionTokens - (a.promptTokens + a.completionTokens));
  if (enriched.length <= topN) return enriched;
  const head = enriched.slice(0, topN);
  const tail = enriched.slice(topN);
  const other: ResolvedBucket = {
    key: "__other__",
    label: `Other (${tail.length})`,
    promptTokens: tail.reduce((s, x) => s + x.promptTokens, 0),
    completionTokens: tail.reduce((s, x) => s + x.completionTokens, 0),
    callCount: tail.reduce((s, x) => s + (x.callCount ?? 0), 0),
    cost: tail.reduce((s, x) => s + x.cost, 0),
    color: "var(--colorTextTertiary, #8c8c8c)",
  };
  return [...head, other];
}

interface DonutProps {
  data: ResolvedBucket[];
  size: number;
  metric: "cost" | "tokens";
}

const Donut: React.FC<DonutProps> = ({ data, size, metric }) => {
  const radius = size / 2;
  const inner = radius * 0.6;
  const total = data.reduce(
    (s, d) => s + (metric === "cost" ? d.cost : d.promptTokens + d.completionTokens),
    0,
  );
  let cumulative = 0;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <g transform={`translate(${radius},${radius})`}>
        {total <= 0 ? (
          <circle
            r={radius - 1}
            fill="none"
            stroke="var(--colorBorderSecondary)"
            strokeWidth={radius - inner}
          />
        ) : (
          data.map((d) => {
            const value =
              metric === "cost" ? d.cost : d.promptTokens + d.completionTokens;
            if (value <= 0) return null;
            const startAngle = (cumulative / total) * Math.PI * 2;
            cumulative += value;
            const endAngle = (cumulative / total) * Math.PI * 2;
            const largeArc = endAngle - startAngle > Math.PI ? 1 : 0;
            const x1 = Math.sin(startAngle) * radius;
            const y1 = -Math.cos(startAngle) * radius;
            const x2 = Math.sin(endAngle) * radius;
            const y2 = -Math.cos(endAngle) * radius;
            const xi2 = Math.sin(endAngle) * inner;
            const yi2 = -Math.cos(endAngle) * inner;
            const xi1 = Math.sin(startAngle) * inner;
            const yi1 = -Math.cos(startAngle) * inner;
            const path = [
              `M ${x1} ${y1}`,
              `A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}`,
              `L ${xi2} ${yi2}`,
              `A ${inner} ${inner} 0 ${largeArc} 0 ${xi1} ${yi1}`,
              "Z",
            ].join(" ");
            const tip = (
              <div className={styles.tooltipBody}>
                <div className={styles.tooltipTitle}>{d.label ?? d.key}</div>
                <div>{formatUsd(d.cost)} est.</div>
                <div>
                  {formatTokens(d.promptTokens + d.completionTokens)} tokens
                </div>
                {typeof d.callCount === "number" && (
                  <div>{d.callCount.toLocaleString()} calls</div>
                )}
              </div>
            );
            return (
              <Tooltip key={d.key} title={tip}>
                <path
                  d={path}
                  fill={d.color}
                  stroke="var(--colorBgContainer)"
                  strokeWidth={1.5}
                  className={styles.donutSlice}
                />
              </Tooltip>
            );
          })
        )}
        <text
          textAnchor="middle"
          dominantBaseline="central"
          className={styles.donutCenterValue}
          y={-6}
        >
          {metric === "cost" ? formatUsd(total) : formatTokens(total)}
        </text>
        <text
          textAnchor="middle"
          dominantBaseline="central"
          className={styles.donutCenterLabel}
          y={12}
        >
          {metric === "cost" ? "total cost" : "total tokens"}
        </text>
      </g>
    </svg>
  );
};

interface StackedBarProps {
  data: ResolvedBucket[];
  height: number;
  metric: "cost" | "tokens";
}

const StackedBar: React.FC<StackedBarProps> = ({ data, height, metric }) => {
  const max = Math.max(
    ...data.map((d) =>
      metric === "cost" ? d.cost : d.promptTokens + d.completionTokens,
    ),
    1,
  );
  return (
    <div className={styles.barWrap} style={{ height }}>
      {data.map((d) => {
        const value =
          metric === "cost" ? d.cost : d.promptTokens + d.completionTokens;
        const pct = (value / max) * 100;
        const promptPct =
          value > 0 ? (d.promptTokens / (d.promptTokens + d.completionTokens || 1)) * 100 : 0;
        const tip = (
          <div className={styles.tooltipBody}>
            <div className={styles.tooltipTitle}>{d.label ?? d.key}</div>
            <div>{formatUsd(d.cost)} est.</div>
            <div>
              {formatTokens(d.promptTokens)} prompt /{" "}
              {formatTokens(d.completionTokens)} completion
            </div>
            {typeof d.callCount === "number" && (
              <div>{d.callCount.toLocaleString()} calls</div>
            )}
          </div>
        );
        return (
          <div className={styles.barRow} key={d.key}>
            <div className={styles.barLabel} title={d.label ?? d.key}>
              {d.label ?? d.key}
            </div>
            <Tooltip title={tip}>
              <div className={styles.barTrack}>
                <div
                  className={styles.barFill}
                  style={{ width: `${pct}%`, background: d.color }}
                >
                  <div
                    className={styles.barPrompt}
                    style={{ width: `${promptPct}%` }}
                  />
                </div>
              </div>
            </Tooltip>
            <div className={styles.barValue}>
              {metric === "cost"
                ? formatUsd(d.cost)
                : formatTokens(d.promptTokens + d.completionTokens)}
            </div>
          </div>
        );
      })}
    </div>
  );
};

const CostBreakdownChart: React.FC<CostBreakdownChartProps> = ({
  buckets,
  prices,
  kind = "donut",
  height = 260,
  topN = 8,
  title,
  className,
  style,
  dimension = "model",
}) => {
  const [metric, setMetric] = useState<"cost" | "tokens">("cost");
  const mergedPrices = useMemo(
    () => ({ ...DEFAULT_PRICES, ...(prices ?? {}) }),
    [prices],
  );
  const resolved = useMemo(
    () => resolveBuckets(buckets, mergedPrices, topN),
    [buckets, mergedPrices, topN],
  );

  const empty = resolved.length === 0;
  const dimensionLabel = {
    model: "Model",
    provider: "Provider",
    agent: "Agent",
    date: "Date",
    custom: "Item",
  }[dimension];

  return (
    <div
      className={`${styles.chartRoot}${className ? ` ${className}` : ""}`}
      style={{ ...style, minHeight: height }}
    >
      <div className={styles.chartHeader}>
        <div className={styles.chartTitle}>
          {title ?? `Cost breakdown by ${dimensionLabel.toLowerCase()}`}
        </div>
        <div className={styles.chartToggle} role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={metric === "cost"}
            className={metric === "cost" ? styles.toggleActive : ""}
            onClick={() => setMetric("cost")}
          >
            Cost
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={metric === "tokens"}
            className={metric === "tokens" ? styles.toggleActive : ""}
            onClick={() => setMetric("tokens")}
          >
            Tokens
          </button>
        </div>
      </div>

      {empty ? (
        <div className={styles.chartEmpty}>No usage data</div>
      ) : kind === "donut" ? (
        <div className={styles.donutLayout}>
          <Donut data={resolved} size={Math.min(220, Number(height) - 60)} metric={metric} />
          <ul className={styles.legend}>
            {resolved.map((d) => {
              const value =
                metric === "cost"
                  ? d.cost
                  : d.promptTokens + d.completionTokens;
              return (
                <li key={d.key} className={styles.legendItem}>
                  <i
                    className={styles.legendSwatch}
                    style={{ background: d.color }}
                  />
                  <span className={styles.legendLabel} title={d.label ?? d.key}>
                    {d.label ?? d.key}
                  </span>
                  <span className={styles.legendValue}>
                    {metric === "cost" ? formatUsd(d.cost) : formatTokens(value)}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      ) : (
        <StackedBar data={resolved} height={Number(height) - 48} metric={metric} />
      )}
    </div>
  );
};

export default CostBreakdownChart;