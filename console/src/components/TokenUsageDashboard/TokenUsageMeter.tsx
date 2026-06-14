import React, { useMemo } from "react";
import { Coins } from "lucide-react";
import type { TokenUsageMeterProps } from "./types";
import { formatTokens, formatUsd } from "./utils";
import styles from "./index.module.less";

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
}

const Sparkline: React.FC<SparklineProps> = ({
  data,
  width = 120,
  height = 32,
  color = "#1677ff",
}) => {
  if (!data.length) return null;
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;
  const step = width / Math.max(data.length - 1, 1);
  const points = data
    .map((v, i) => {
      const x = i * step;
      const y = height - ((v - min) / range) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const areaPath = `M0,${height} L${points
    .split(" ")
    .map((p) => p)
    .join(" L")} L${width},${height} Z`;
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={styles.spark}
    >
      <path d={areaPath} fill={color} opacity={0.15} />
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
};

const TokenUsageMeter: React.FC<TokenUsageMeterProps> = ({
  promptTokens,
  completionTokens,
  budgetTokens,
  costUsd,
  sparkline,
  callCount,
  windowLabel,
  className,
  style,
  compact = false,
}) => {
  const total = promptTokens + completionTokens;
  const promptPct = total > 0 ? (promptTokens / total) * 100 : 0;
  const completionPct = total > 0 ? (completionTokens / total) * 100 : 0;
  const budgetPct = useMemo(() => {
    if (!budgetTokens || budgetTokens <= 0) return null;
    return Math.min((total / budgetTokens) * 100, 999);
  }, [total, budgetTokens]);

  const budgetClass =
    budgetPct == null
      ? ""
      : budgetPct >= 100
        ? styles.budgetOver
        : budgetPct >= 80
          ? styles.budgetWarn
          : styles.budgetOk;

  return (
    <div
      className={`${styles.meterRoot}${compact ? ` ${styles.meterCompact}` : ""}${
        className ? ` ${className}` : ""
      }`}
      style={style}
    >
      <div className={styles.meterHeader}>
        <Coins size={14} className={styles.meterIcon} />
        <span className={styles.meterTitle}>Token usage</span>
        {windowLabel && (
          <span className={styles.meterWindow}>{windowLabel}</span>
        )}
      </div>

      <div className={styles.meterMainRow}>
        <div className={styles.meterTotal}>
          <span className={styles.meterTotalValue}>{formatTokens(total)}</span>
          <span className={styles.meterTotalLabel}>tokens</span>
        </div>
        {typeof costUsd === "number" && (
          <div className={styles.meterCost}>
            <span className={styles.meterCostValue}>{formatUsd(costUsd)}</span>
            <span className={styles.meterCostLabel}>est. cost</span>
          </div>
        )}
        {sparkline && sparkline.length > 1 && (
          <div className={styles.meterSpark}>
            <Sparkline data={sparkline} />
          </div>
        )}
      </div>

      <div className={styles.meterSplit}>
        <div
          className={styles.meterSplitPrompt}
          style={{ width: `${promptPct}%` }}
          title={`${formatTokens(promptTokens)} prompt`}
        />
        <div
          className={styles.meterSplitCompletion}
          style={{ width: `${completionPct}%` }}
          title={`${formatTokens(completionTokens)} completion`}
        />
      </div>
      <div className={styles.meterLegend}>
        <span>
          <i className={styles.dotPrompt} /> Prompt {formatTokens(promptTokens)}
        </span>
        <span>
          <i className={styles.dotCompletion} /> Completion{" "}
          {formatTokens(completionTokens)}
        </span>
        {typeof callCount === "number" && (
          <span className={styles.meterCallCount}>
            {callCount.toLocaleString()} calls
          </span>
        )}
      </div>

      {budgetPct != null && (
        <div className={styles.budgetRow}>
          <div className={styles.budgetTrack}>
            <div
              className={`${styles.budgetFill} ${budgetClass}`}
              style={{ width: `${Math.min(budgetPct, 100)}%` }}
            />
          </div>
          <div className={styles.budgetLabel}>
            {budgetPct.toFixed(0)}% of {formatTokens(budgetTokens!)} budget
          </div>
        </div>
      )}
    </div>
  );
};

export default TokenUsageMeter;