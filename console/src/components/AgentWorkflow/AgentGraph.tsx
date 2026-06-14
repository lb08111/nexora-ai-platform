import React, { useEffect, useMemo, useRef, useState } from "react";
import { Bot, Cpu, Brain, Zap, CheckCircle2, AlertCircle } from "lucide-react";
import type {
  AgentStatus,
  AgentWorkflowLayout,
  WorkflowAgent,
  WorkflowMessage,
} from "./types";
import styles from "./index.module.less";

interface AgentGraphProps {
  agents: WorkflowAgent[];
  messages: WorkflowMessage[];
  layout: AgentWorkflowLayout;
  liveEdgeCount: number;
  onAgentClick?: (agent: WorkflowAgent) => void;
}

interface NodePosition {
  x: number;
  y: number;
}

const STATUS_COLOR: Record<AgentStatus, string> = {
  idle: "#8c8c8c",
  thinking: "#722ed1",
  working: "#1677ff",
  waiting: "#faad14",
  done: "#52c41a",
  error: "#ff4d4f",
};

const STATUS_LABEL: Record<AgentStatus, string> = {
  idle: "Idle",
  thinking: "Thinking",
  working: "Working",
  waiting: "Waiting",
  done: "Done",
  error: "Error",
};

function StatusIcon({ status }: { status: AgentStatus }) {
  const props = { size: 12, strokeWidth: 2.5 };
  switch (status) {
    case "thinking":
      return <Brain {...props} />;
    case "working":
      return <Cpu {...props} />;
    case "waiting":
      return <Zap {...props} />;
    case "done":
      return <CheckCircle2 {...props} />;
    case "error":
      return <AlertCircle {...props} />;
    default:
      return <Bot {...props} />;
  }
}

function computePositions(
  agents: WorkflowAgent[],
  width: number,
  height: number,
  layout: AgentWorkflowLayout,
): NodePosition[] {
  const n = agents.length;
  if (n === 0) return [];

  const effective: AgentWorkflowLayout =
    layout === "auto" ? (n <= 3 ? "horizontal" : "circle") : layout;

  const padX = 120;
  const padY = 100;

  if (effective === "horizontal") {
    const usable = Math.max(width - padX * 2, 1);
    const step = n === 1 ? 0 : usable / (n - 1);
    const y = height / 2;
    return agents.map((_, i) => ({
      x: padX + step * i,
      y,
    }));
  }

  if (effective === "grid") {
    const cols = Math.ceil(Math.sqrt(n));
    const rows = Math.ceil(n / cols);
    const cellW = (width - padX * 2) / Math.max(cols, 1);
    const cellH = (height - padY * 2) / Math.max(rows, 1);
    return agents.map((_, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      return {
        x: padX + cellW * col + cellW / 2,
        y: padY + cellH * row + cellH / 2,
      };
    });
  }

  // circle
  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.max(Math.min(width, height) / 2 - padY, 80);
  return agents.map((_, i) => {
    const angle = (2 * Math.PI * i) / n - Math.PI / 2;
    return {
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    };
  });
}

interface Edge {
  fromId: string;
  toId: string;
  count: number;
  /** 0..1 — recency weight (1 = newest). */
  recency: number;
  lastType?: string;
}

function buildEdges(
  agents: WorkflowAgent[],
  messages: WorkflowMessage[],
  liveEdgeCount: number,
): Edge[] {
  const ids = new Set(agents.map((a) => a.id));
  const agentMessages = messages.filter(
    (m) => ids.has(m.from) && ids.has(m.to),
  );
  if (agentMessages.length === 0) return [];

  const recent = agentMessages.slice(-Math.max(liveEdgeCount, 1));
  const map = new Map<string, Edge>();

  agentMessages.forEach((m) => {
    const key = `${m.from}->${m.to}`;
    const recencyIdx = recent.indexOf(m);
    const recency = recencyIdx === -1 ? 0 : (recencyIdx + 1) / recent.length;
    const existing = map.get(key);
    if (existing) {
      existing.count += 1;
      existing.recency = Math.max(existing.recency, recency);
      if (recencyIdx !== -1) existing.lastType = m.type;
    } else {
      map.set(key, {
        fromId: m.from,
        toId: m.to,
        count: 1,
        recency,
        lastType: recencyIdx !== -1 ? m.type : undefined,
      });
    }
  });

  return Array.from(map.values());
}

const AgentGraph: React.FC<AgentGraphProps> = ({
  agents,
  messages,
  layout,
  liveEdgeCount,
  onAgentClick,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 720, height: 420 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () => {
      const rect = el.getBoundingClientRect();
      setSize({
        width: Math.max(rect.width, 320),
        height: Math.max(rect.height, 240),
      });
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const positions = useMemo(
    () => computePositions(agents, size.width, size.height, layout),
    [agents, size.width, size.height, layout],
  );

  const positionById = useMemo(() => {
    const map = new Map<string, NodePosition>();
    agents.forEach((a, i) => {
      if (positions[i]) map.set(a.id, positions[i]);
    });
    return map;
  }, [agents, positions]);

  const edges = useMemo(
    () => buildEdges(agents, messages, liveEdgeCount),
    [agents, messages, liveEdgeCount],
  );

  return (
    <div ref={containerRef} className={styles.graphCanvas}>
      <svg
        className={styles.graphSvg}
        width={size.width}
        height={size.height}
        viewBox={`0 0 ${size.width} ${size.height}`}
      >
        <defs>
          <marker
            id="agentwf-arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor" />
          </marker>
          <marker
            id="agentwf-arrow-active"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#1677ff" />
          </marker>
        </defs>

        {edges.map((edge) => {
          const from = positionById.get(edge.fromId);
          const to = positionById.get(edge.toId);
          if (!from || !to) return null;

          const dx = to.x - from.x;
          const dy = to.y - from.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const nodeRadius = 56;
          const sx = from.x + (dx / dist) * nodeRadius;
          const sy = from.y + (dy / dist) * nodeRadius;
          const tx = to.x - (dx / dist) * nodeRadius;
          const ty = to.y - (dy / dist) * nodeRadius;

          const isActive = edge.recency > 0;
          const opacity = 0.25 + Math.min(edge.recency, 1) * 0.6;

          const mx = (sx + tx) / 2;
          const my = (sy + ty) / 2;
          const nx = -dy / dist;
          const ny = dx / dist;
          const curve = 18;
          const cx = mx + nx * curve;
          const cy = my + ny * curve;

          return (
            <g
              key={`${edge.fromId}->${edge.toId}`}
              className={isActive ? styles.edgeActive : styles.edge}
              style={{ color: isActive ? "#1677ff" : "#bfbfbf", opacity }}
            >
              <path
                d={`M ${sx} ${sy} Q ${cx} ${cy} ${tx} ${ty}`}
                fill="none"
                stroke="currentColor"
                strokeWidth={isActive ? 2 : 1.5}
                strokeDasharray={isActive ? "6 4" : undefined}
                markerEnd={
                  isActive
                    ? "url(#agentwf-arrow-active)"
                    : "url(#agentwf-arrow)"
                }
              />
              {edge.count > 1 && (
                <text
                  x={cx}
                  y={cy}
                  textAnchor="middle"
                  fontSize={10}
                  fill="currentColor"
                  dy="-4"
                >
                  ×{edge.count}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {agents.map((agent, i) => {
        const pos = positions[i];
        if (!pos) return null;
        const accent = agent.color || STATUS_COLOR[agent.status];
        return (
          <div
            key={agent.id}
            className={`${styles.agentNode} ${
              agent.status === "working" || agent.status === "thinking"
                ? styles.agentNodePulse
                : ""
            }`}
            style={{
              left: pos.x,
              top: pos.y,
              borderColor: accent,
              cursor: onAgentClick ? "pointer" : "default",
            }}
            onClick={() => onAgentClick?.(agent)}
            title={agent.description || agent.name}
          >
            <div className={styles.agentAvatar} style={{ background: accent }}>
              {agent.avatar || agent.name.charAt(0).toUpperCase()}
            </div>
            <div className={styles.agentBody}>
              <div className={styles.agentName} title={agent.name}>
                {agent.name}
              </div>
              {agent.role && (
                <div className={styles.agentRole}>{agent.role}</div>
              )}
              <div
                className={styles.agentStatus}
                style={{ color: STATUS_COLOR[agent.status] }}
              >
                <StatusIcon status={agent.status} />
                <span>{STATUS_LABEL[agent.status]}</span>
              </div>
              {agent.currentTask && (
                <div
                  className={styles.agentCurrentTask}
                  title={agent.currentTask}
                >
                  {agent.currentTask}
                </div>
              )}
            </div>
          </div>
        );
      })}

      {agents.length === 0 && (
        <div className={styles.graphEmpty}>
          <Bot size={32} />
          <div>No agents to display</div>
        </div>
      )}
    </div>
  );
};

export default AgentGraph;
