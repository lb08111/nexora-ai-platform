/**
 * Public type definitions for the AgentWorkflow visualization component.
 *
 * Consumers can import these to shape their own data sources before passing
 * them to <AgentWorkflow />.
 */

export type AgentStatus =
  | "idle"
  | "thinking"
  | "working"
  | "waiting"
  | "done"
  | "error";

export interface WorkflowAgent {
  id: string;
  name: string;
  /** Short role description (e.g. "Planner", "Researcher", "Coder"). */
  role?: string;
  description?: string;
  status: AgentStatus;
  /** Free-form text shown under the agent: current task / thought / tool. */
  currentTask?: string;
  /** Optional emoji or single character used as avatar. */
  avatar?: string;
  /** Override accent color (any valid CSS color). */
  color?: string;
}

export type WorkflowTaskState =
  | "todo"
  | "in_progress"
  | "done"
  | "blocked"
  | "abandoned";

export interface WorkflowTask {
  id: string;
  name: string;
  description?: string;
  state: WorkflowTaskState;
  /** Agent id this task is assigned to. */
  assignedTo?: string;
  outcome?: string;
  /** Parent task id, for sub-tasks. */
  parentId?: string;
  createdAt?: string | number;
  finishedAt?: string | number;
}

export interface WorkflowPlan {
  id: string;
  name: string;
  description?: string;
  state: WorkflowTaskState;
  tasks: WorkflowTask[];
  outcome?: string;
}

export type WorkflowMessageType =
  | "request"
  | "response"
  | "broadcast"
  | "tool_call"
  | "tool_result"
  | "handoff"
  | "info";

export interface WorkflowMessage {
  id: string;
  /** Source agent id. Use "user" or "system" for non-agent senders. */
  from: string;
  /** Destination agent id, or "broadcast" / "user". */
  to: string;
  content: string;
  timestamp: string | number;
  type?: WorkflowMessageType;
}

export type AgentWorkflowLayout = "auto" | "circle" | "horizontal" | "grid";

export interface AgentWorkflowProps {
  agents: WorkflowAgent[];
  plan?: WorkflowPlan | null;
  messages?: WorkflowMessage[];
  /** Total visual height of the component. Default: 560. */
  height?: number | string;
  /** Graph layout strategy. Default: "auto". */
  layout?: AgentWorkflowLayout;
  /** Hide the plan side panel. Default: false. */
  hidePlan?: boolean;
  /** Hide the communication log. Default: false. */
  hideCommunicationLog?: boolean;
  /** How many recent messages are highlighted as live edges. Default: 5. */
  liveEdgeCount?: number;
  onAgentClick?: (agent: WorkflowAgent) => void;
  onTaskClick?: (task: WorkflowTask) => void;
  className?: string;
  style?: React.CSSProperties;
  /** Optional title shown in the toolbar. */
  title?: React.ReactNode;
}
