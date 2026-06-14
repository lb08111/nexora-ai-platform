import React, { useEffect, useMemo, useRef } from "react";
import { ArrowRight, Radio } from "lucide-react";
import type { WorkflowAgent, WorkflowMessage } from "./types";
import styles from "./index.module.less";

interface CommunicationLogProps {
  messages: WorkflowMessage[];
  agents: WorkflowAgent[];
  /** Auto-scroll to newest message. Default: true. */
  autoScroll?: boolean;
  maxItems?: number;
}

const TYPE_CLASS: Record<string, string> = {
  request: styles.msgRequest,
  response: styles.msgResponse,
  broadcast: styles.msgBroadcast,
  tool_call: styles.msgToolCall,
  tool_result: styles.msgToolResult,
  handoff: styles.msgHandoff,
  info: styles.msgInfo,
};

function formatTime(ts: string | number): string {
  const date = typeof ts === "number" ? new Date(ts) : new Date(ts);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString();
}

const CommunicationLog: React.FC<CommunicationLogProps> = ({
  messages,
  agents,
  autoScroll = true,
  maxItems = 200,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  const agentById = useMemo(() => {
    const map = new Map<string, WorkflowAgent>();
    agents.forEach((a) => map.set(a.id, a));
    return map;
  }, [agents]);

  const items = useMemo(
    () => messages.slice(-Math.max(maxItems, 1)),
    [messages, maxItems],
  );

  useEffect(() => {
    if (!autoScroll) return;
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [items, autoScroll]);

  const renderParty = (id: string) => {
    if (id === "broadcast")
      return (
        <span className={styles.partyBroadcast}>
          <Radio size={11} /> broadcast
        </span>
      );
    if (id === "user") return <span className={styles.partyUser}>user</span>;
    if (id === "system")
      return <span className={styles.partySystem}>system</span>;
    const agent = agentById.get(id);
    if (!agent) return <span className={styles.partyUnknown}>{id}</span>;
    return (
      <span className={styles.partyAgent}>
        <span
          className={styles.partyAvatar}
          style={{ background: agent.color || "#1677ff" }}
        >
          {agent.avatar || agent.name.charAt(0).toUpperCase()}
        </span>
        {agent.name}
      </span>
    );
  };

  return (
    <div className={styles.logRoot}>
      <div className={styles.logHeader}>
        <span>Communication</span>
        <span className={styles.logCount}>{messages.length}</span>
      </div>
      <div ref={scrollRef} className={styles.logScroll}>
        {items.length === 0 && (
          <div className={styles.logEmpty}>No messages yet.</div>
        )}
        {items.map((m) => (
          <div key={m.id} className={styles.logItem}>
            <div className={styles.logItemHeader}>
              {renderParty(m.from)}
              <ArrowRight size={12} className={styles.logArrow} />
              {renderParty(m.to)}
              {m.type && (
                <span
                  className={`${styles.msgType} ${TYPE_CLASS[m.type] || ""}`}
                >
                  {m.type}
                </span>
              )}
              <span className={styles.logTime}>{formatTime(m.timestamp)}</span>
            </div>
            <div className={styles.logItemBody}>{m.content}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CommunicationLog;
