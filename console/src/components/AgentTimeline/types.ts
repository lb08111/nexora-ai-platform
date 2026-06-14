/**
 * Public type definitions for the AgentTimeline component.
 */

export type TimelineSpanKind =
  | "thought"
  | "tool_call"
  | "llm_call"
  | "task"
  | "wait"
  | "error"
  | "message"
  | "custom";

export type TimelineSpanStatus = "running" | "success" | "error" | "cancelled";

export interface TimelineSpan {
  id: string;
  /** Owning agent id. Spans are grouped into one row per agent id. */
  agentId: string;
  /** Display label (e.g. tool name, step description). */
  label: string;
  /** Start time as ms epoch OR ISO string. */
  start: number | string;
  /** End time. If omitted, span is considered still running (uses `now()`). */
  end?: number | string | null;
  kind?: TimelineSpanKind;
  status?: TimelineSpanStatus;
  /** Optional details rendered in the tooltip / side panel. */
  details?: string;
  /** Optional override color. */
  color?: string;
  /** Free-form metadata bag (e.g. tokens, cost). */
  meta?: Record<string, unknown>;
}

export interface TimelineAgentRow {
  id: string;
  name: string;
  /** Optional emoji / single char avatar. */
  avatar?: string;
  color?: string;
}

export interface AgentTimelineProps {
  agents: TimelineAgentRow[];
  spans: TimelineSpan[];
  /** Total height of the component. Default: 420. */
  height?: number | string;
  /** Pixels per millisecond at zoom 1. Default: auto-fit. */
  pxPerMs?: number;
  /** Initial zoom level. Default: 1. */
  initialZoom?: number;
  /** Fix the viewport to this start (ms). Default: min(spans). */
  viewStart?: number;
  /** Fix the viewport to this end (ms). Default: max(spans, or now if running). */
  viewEnd?: number;
  /** Auto-follow newest spans (useful for live mode). Default: false. */
  follow?: boolean;
  onSpanClick?: (span: TimelineSpan) => void;
  className?: string;
  style?: React.CSSProperties;
  title?: React.ReactNode;
}