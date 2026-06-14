import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Tooltip } from "antd";
import { ZoomIn, ZoomOut, Maximize2, Pause, Play } from "lucide-react";
import type {
  AgentTimelineProps,
  TimelineSpan,
  TimelineSpanKind,
  TimelineSpanStatus,
} from "./types";
import styles from "./index.module.less";

const ROW_HEIGHT = 36;
const HEADER_HEIGHT = 28;
const LABEL_WIDTH = 160;
const MIN_SPAN_PX = 4;

const KIND_COLOR: Record<TimelineSpanKind, string> = {
  thought: "#722ed1",
  tool_call: "#1677ff",
  llm_call: "#13c2c2",
  task: "#52c41a",
  wait: "#bfbfbf",
  error: "#ff4d4f",
  message: "#faad14",
  custom: "#8c8c8c",
};

const STATUS_OVERLAY: Record<TimelineSpanStatus, string> = {
  running: "rgba(22, 119, 255, 0.5)",
  success: "transparent",
  error: "#ff4d4f",
  cancelled: "#8c8c8c",
};

function toMs(value: number | string | null | undefined): number {
  if (value == null) return Number.NaN;
  if (typeof value === "number") return value;
  const t = Date.parse(value);
  return Number.isNaN(t) ? Number.NaN : t;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(2)}s`;
  const m = Math.floor(ms / 60_000);
  const s = Math.round((ms % 60_000) / 1000);
  return `${m}m ${s}s`;
}

function formatRelative(ms: number, origin: number): string {
  const delta = ms - origin;
  if (delta < 1000) return `+${Math.round(delta)}ms`;
  return `+${(delta / 1000).toFixed(2)}s`;
}

interface NormalizedSpan extends TimelineSpan {
  _start: number;
  _end: number;
  _running: boolean;
}

const AgentTimeline: React.FC<AgentTimelineProps> = ({
  agents,
  spans,
  height = 420,
  pxPerMs,
  initialZoom = 1,
  viewStart,
  viewEnd,
  follow = false,
  onSpanClick,
  className,
  style,
  title,
}) => {
  const [zoom, setZoom] = useState(initialZoom);
  const [paused, setPaused] = useState(!follow);
  const [now, setNow] = useState(() => Date.now());
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(800);

  // Tick clock for running spans / follow mode
  useEffect(() => {
    if (paused) return;
    const id = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(id);
  }, [paused]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () => setContainerWidth(el.clientWidth);
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const normalized: NormalizedSpan[] = useMemo(() => {
    return spans
      .map((s) => {
        const start = toMs(s.start);
        const rawEnd = s.end == null ? null : toMs(s.end);
        const running = rawEnd == null || Number.isNaN(rawEnd);
        const end = running ? now : (rawEnd as number);
        if (Number.isNaN(start)) return null;
        return { ...s, _start: start, _end: end, _running: running };
      })
      .filter((s): s is NormalizedSpan => s !== null)
      .sort((a, b) => a._start - b._start);
  }, [spans, now]);

  const bounds = useMemo(() => {
    if (normalized.length === 0) {
      const t = now;
      return { start: t - 60_000, end: t };
    }
    const start =
      viewStart != null
        ? viewStart
        : Math.min(...normalized.map((s) => s._start));
    const end =
      viewEnd != null ? viewEnd : Math.max(...normalized.map((s) => s._end));
    const span = Math.max(end - start, 1000);
    return { start, end: start + span };
  }, [normalized, now, viewStart, viewEnd]);

  const usableWidth = Math.max(containerWidth - LABEL_WIDTH - 24, 200);
  const totalMs = bounds.end - bounds.start || 1;
  const basePxPerMs = pxPerMs ?? usableWidth / totalMs;
  const effectivePxPerMs = basePxPerMs * zoom;
  const innerWidth = totalMs * effectivePxPerMs;

  const xFor = useCallback(
    (ms: number) => (ms - bounds.start) * effectivePxPerMs,
    [bounds.start, effectivePxPerMs],
  );

  // Auto-scroll when following
  useEffect(() => {
    if (!follow || paused) return;
    const el = scrollRef.current;
    if (!el) return;
    el.scrollLeft = el.scrollWidth;
  }, [follow, paused, normalized.length, now]);

  // Group spans by agent
  const byAgent = useMemo(() => {
    const map = new Map<string, NormalizedSpan[]>();
    agents.forEach((a) => map.set(a.id, []));
    normalized.forEach((s) => {
      if (!map.has(s.agentId)) map.set(s.agentId, []);
      map.get(s.agentId)!.push(s);
    });
    return map;
  }, [agents, normalized]);

  // Build axis ticks (about 1 per 100px)
  const ticks = useMemo(() => {
    const targetTickCount = Math.max(4, Math.floor(innerWidth / 120));
    const rawStep = totalMs / targetTickCount;
    const niceSteps = [
      100, 250, 500, 1000, 2000, 5000, 10_000, 30_000, 60_000, 300_000, 600_000,
      1_800_000, 3_600_000,
    ];
    const step = niceSteps.find((s) => s >= rawStep) ?? rawStep;
    const out: { x: number; label: string; ms: number }[] = [];
    for (let t = 0; t <= totalMs; t += step) {
      out.push({
        x: t * effectivePxPerMs,
        label: formatRelative(bounds.start + t, bounds.start),
        ms: bounds.start + t,
      });
    }
    return out;
  }, [innerWidth, totalMs, effectivePxPerMs, bounds.start]);

  const selected = useMemo(
    () => normalized.find((s) => s.id === selectedId) ?? null,
    [normalized, selectedId],
  );

  const handleZoomIn = () => setZoom((z) => Math.min(z * 1.5, 64));
  const handleZoomOut = () => setZoom((z) => Math.max(z / 1.5, 0.1));
  const handleFit = () => setZoom(1);

  return (
    <div
      ref={containerRef}
      className={`${styles.root}${className ? ` ${className}` : ""}`}
      style={{ height, ...style }}
    >
      <div className={styles.toolbar}>
        <div className={styles.toolbarTitle}>{title ?? "Agent Timeline"}</div>
        <div className={styles.toolbarStats}>
          <span>
            <strong>{agents.length}</strong> agents
          </span>
          <span>
            <strong>{normalized.length}</strong> spans
          </span>
          <span>
            <strong>{formatDuration(totalMs)}</strong> window
          </span>
        </div>
        <div className={styles.toolbarActions}>
          {follow && (
            <button
              className={styles.iconBtn}
              onClick={() => setPaused((p) => !p)}
              title={paused ? "Resume follow" : "Pause follow"}
            >
              {paused ? <Play size={14} /> : <Pause size={14} />}
            </button>
          )}
          <button
            className={styles.iconBtn}
            onClick={handleZoomOut}
            title="Zoom out"
          >
            <ZoomOut size={14} />
          </button>
          <button className={styles.iconBtn} onClick={handleFit} title="Fit">
            <Maximize2 size={14} />
          </button>
          <button
            className={styles.iconBtn}
            onClick={handleZoomIn}
            title="Zoom in"
          >
            <ZoomIn size={14} />
          </button>
        </div>
      </div>

      <div className={styles.body}>
        <div className={styles.labelCol} style={{ width: LABEL_WIDTH }}>
          <div className={styles.labelHeader} style={{ height: HEADER_HEIGHT }}>
            Agent
          </div>
          {agents.map((a) => (
            <div
              key={a.id}
              className={styles.labelRow}
              style={{ height: ROW_HEIGHT }}
            >
              <span
                className={styles.labelAvatar}
                style={{ background: a.color || "#1677ff" }}
              >
                {a.avatar || a.name.charAt(0).toUpperCase()}
              </span>
              <span className={styles.labelName} title={a.name}>
                {a.name}
              </span>
            </div>
          ))}
        </div>

        <div ref={scrollRef} className={styles.scroller}>
          <div
            className={styles.canvas}
            style={{
              width: Math.max(innerWidth, usableWidth),
              height: HEADER_HEIGHT + agents.length * ROW_HEIGHT,
            }}
          >
            {/* axis */}
            <div className={styles.axis} style={{ height: HEADER_HEIGHT }}>
              {ticks.map((t, i) => (
                <div
                  key={i}
                  className={styles.tick}
                  style={{ left: t.x }}
                  title={new Date(t.ms).toLocaleTimeString()}
                >
                  <span className={styles.tickLabel}>{t.label}</span>
                </div>
              ))}
            </div>

            {/* gridlines */}
            <svg
              className={styles.grid}
              width="100%"
              height={agents.length * ROW_HEIGHT}
              style={{ top: HEADER_HEIGHT }}
            >
              {ticks.map((t, i) => (
                <line
                  key={i}
                  x1={t.x}
                  x2={t.x}
                  y1={0}
                  y2={agents.length * ROW_HEIGHT}
                  stroke="currentColor"
                  strokeWidth={1}
                  opacity={0.08}
                />
              ))}
            </svg>

            {/* swimlanes */}
            {agents.map((a, rowIdx) => {
              const rowSpans = byAgent.get(a.id) || [];
              const top = HEADER_HEIGHT + rowIdx * ROW_HEIGHT;
              return (
                <div
                  key={a.id}
                  className={styles.row}
                  style={{
                    top,
                    height: ROW_HEIGHT,
                  }}
                >
                  {rowSpans.map((s) => {
                    const left = xFor(s._start);
                    const widthRaw = (s._end - s._start) * effectivePxPerMs;
                    const width = Math.max(widthRaw, MIN_SPAN_PX);
                    const accent =
                      s.color ||
                      (s.status === "error"
                        ? KIND_COLOR.error
                        : KIND_COLOR[s.kind ?? "custom"]);
                    const duration = formatDuration(s._end - s._start);
                    const isSelected = s.id === selectedId;
                    return (
                      <Tooltip
                        key={s.id}
                        title={
                          <div className={styles.tooltipBody}>
                            <div className={styles.tooltipTitle}>{s.label}</div>
                            <div>
                              {s.kind || "custom"}
                              {s.status ? ` · ${s.status}` : ""}
                            </div>
                            <div>{duration}</div>
                            {s.details && (
                              <div className={styles.tooltipDetails}>
                                {s.details}
                              </div>
                            )}
                          </div>
                        }
                      >
                        <div
                          className={`${styles.span} ${
                            s._running ? styles.spanRunning : ""
                          } ${isSelected ? styles.spanSelected : ""}`}
                          style={{
                            left,
                            width,
                            background: accent,
                            outline:
                              s.status && s.status !== "success"
                                ? `2px solid ${STATUS_OVERLAY[s.status]}`
                                : undefined,
                          }}
                          onClick={() => {
                            setSelectedId(s.id);
                            onSpanClick?.(s);
                          }}
                        >
                          {width > 48 && (
                            <span className={styles.spanLabel}>{s.label}</span>
                          )}
                        </div>
                      </Tooltip>
                    );
                  })}
                </div>
              );
            })}

            {/* live "now" line */}
            {follow && !paused && (
              <div
                className={styles.nowLine}
                style={{
                  left: xFor(now),
                  height: HEADER_HEIGHT + agents.length * ROW_HEIGHT,
                }}
              />
            )}
          </div>
        </div>
      </div>

      {selected && (
        <div className={styles.detailBar}>
          <div className={styles.detailBarRow}>
            <strong>{selected.label}</strong>
            <span className={styles.detailMeta}>
              {selected.kind || "custom"}
              {selected.status ? ` · ${selected.status}` : ""} ·{" "}
              {formatDuration(selected._end - selected._start)}
            </span>
            <button
              className={styles.detailClose}
              onClick={() => setSelectedId(null)}
              aria-label="Close"
            >
              ×
            </button>
          </div>
          {selected.details && (
            <div className={styles.detailText}>{selected.details}</div>
          )}
        </div>
      )}

      {normalized.length === 0 && (
        <div className={styles.emptyOverlay}>No spans to display</div>
      )}
    </div>
  );
};

export default AgentTimeline;
