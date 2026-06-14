import React from "react";
import { Workflow } from "lucide-react";
import AgentGraph from "./AgentGraph";
import PlanView from "./PlanView";
import CommunicationLog from "./CommunicationLog";
import type { AgentWorkflowProps } from "./types";
import styles from "./index.module.less";

/**
 * AgentWorkflow visualises a set of AI agents, the plan they are executing,
 * the tasks assigned to them, and the messages flowing between them.
 *
 * It is intentionally self-contained — pass props from any data source
 * (REST polling, SSE, websocket, mock data). For the built-in wiring to
 * the existing /agents and /plan APIs, use `useLiveAgentWorkflow`.
 *
 * @example
 * ```tsx
 * import AgentWorkflow, { useLiveAgentWorkflow } from "@/components/AgentWorkflow";
 *
 * export default function Page() {
 *   const { agents, plan, messages } = useLiveAgentWorkflow();
 *   return (
 *     <AgentWorkflow
 *       agents={agents}
 *       plan={plan}
 *       messages={messages}
 *       height={640}
 *     />
 *   );
 * }
 * ```
 */
const AgentWorkflow: React.FC<AgentWorkflowProps> = ({
  agents,
  plan = null,
  messages = [],
  height = 560,
  layout = "auto",
  hidePlan = false,
  hideCommunicationLog = false,
  liveEdgeCount = 5,
  onAgentClick,
  onTaskClick,
  className,
  style,
  title,
}) => {
  return (
    <div
      className={`${styles.root}${className ? ` ${className}` : ""}`}
      style={{ height, ...style }}
    >
      <div className={styles.toolbar}>
        <div className={styles.toolbarTitle}>
          <Workflow size={16} />
          <span>{title ?? "Agent Workflow"}</span>
        </div>
        <div className={styles.toolbarStats}>
          <span>
            <strong>{agents.length}</strong> agents
          </span>
          <span>
            <strong>{plan?.tasks?.length ?? 0}</strong> tasks
          </span>
          <span>
            <strong>{messages.length}</strong> messages
          </span>
        </div>
      </div>

      <div className={styles.body}>
        <div className={styles.graphPane}>
          <AgentGraph
            agents={agents}
            messages={messages}
            layout={layout}
            liveEdgeCount={liveEdgeCount}
            onAgentClick={onAgentClick}
          />
        </div>
        {!hidePlan && (
          <div className={styles.planPane}>
            <PlanView plan={plan} agents={agents} onTaskClick={onTaskClick} />
          </div>
        )}
      </div>

      {!hideCommunicationLog && (
        <div className={styles.logPane}>
          <CommunicationLog messages={messages} agents={agents} />
        </div>
      )}
    </div>
  );
};

export default AgentWorkflow;
