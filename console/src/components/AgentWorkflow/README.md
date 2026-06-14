# AgentWorkflow

A self-contained React component that visualizes a multi-agent system:

- **Agents** as nodes in an interactive graph (auto / circle / horizontal / grid layout)
- **Plan & tasks** in a side panel, with progress and per-task assignee
- **Communication** between agents as animated edges and a chronological log

## Quick start

```tsx
import AgentWorkflow from "@/components/AgentWorkflow";

const agents = [
  { id: "planner", name: "Planner", role: "Architect", status: "thinking", avatar: "🧠" },
  { id: "coder",   name: "Coder",   role: "Implementer", status: "working", avatar: "💻" },
  { id: "qa",      name: "QA",      role: "Reviewer", status: "waiting",  avatar: "🔍" },
];

const plan = {
  id: "p1",
  name: "Ship new dashboard",
  description: "Implement the agents workflow dashboard end-to-end.",
  state: "in_progress",
  tasks: [
    { id: "t1", name: "Draft plan",  state: "done",        assignedTo: "planner" },
    { id: "t2", name: "Build UI",    state: "in_progress", assignedTo: "coder" },
    { id: "t3", name: "Write tests", state: "todo",        assignedTo: "qa" },
  ],
};

const messages = [
  { id: "m1", from: "planner", to: "coder", type: "handoff",
    content: "Use AgentGraph as the canvas.", timestamp: Date.now() - 30000 },
  { id: "m2", from: "coder",   to: "qa",    type: "request",
    content: "Ready for review.",           timestamp: Date.now() - 5000 },
];

export default function Page() {
  return <AgentWorkflow agents={agents} plan={plan} messages={messages} height={640} />;
}
```

## Live mode (existing backend)

If you want to bind to the existing `/agents` and `/plan` APIs that the console
already exposes, use the included hook:

```tsx
import AgentWorkflow, { useLiveAgentWorkflow } from "@/components/AgentWorkflow";

export default function LivePage() {
  const { agents, plan, messages, pushMessage } = useLiveAgentWorkflow();

  // Pipe your own SSE / websocket / chat events here:
  // pushMessage({ id, from, to, content, timestamp, type })

  return <AgentWorkflow agents={agents} plan={plan} messages={messages} />;
}
```

The hook polls the agents list every 15s and subscribes to the existing plan
SSE stream. Messages are kept in a rolling buffer (default 500) and are not
fetched automatically — feed them through `pushMessage` from your own source.

## Props

| Prop                    | Type                                     | Default | Description                                   |
| ----------------------- | ---------------------------------------- | ------- | --------------------------------------------- |
| `agents`                | `WorkflowAgent[]`                        | —       | Required. List of agents to render.           |
| `plan`                  | `WorkflowPlan \| null`                   | `null`  | Optional plan with tasks.                     |
| `messages`              | `WorkflowMessage[]`                      | `[]`    | Inter-agent messages (also drives edges).     |
| `height`                | `number \| string`                       | `560`   | Component height.                             |
| `layout`                | `"auto" \| "circle" \| "horizontal" \| "grid"` | `"auto"` | Graph layout. `auto` = horizontal if ≤3 agents, else circle. |
| `hidePlan`              | `boolean`                                | `false` | Hide the plan side panel.                     |
| `hideCommunicationLog`  | `boolean`                                | `false` | Hide the bottom message log.                  |
| `liveEdgeCount`         | `number`                                 | `5`     | Number of recent messages drawn as live edges.|
| `onAgentClick`          | `(agent) => void`                        | —       | Click handler for agent nodes.                |
| `onTaskClick`           | `(task) => void`                         | —       | Click handler for task rows.                  |
| `title`                 | `ReactNode`                              | —       | Override toolbar title.                       |

### Status values

`AgentStatus`: `"idle" | "thinking" | "working" | "waiting" | "done" | "error"`

### Task states

`WorkflowTaskState`: `"todo" | "in_progress" | "done" | "blocked" | "abandoned"`

### Message types (drive edge / chip color)

`WorkflowMessageType`: `"request" | "response" | "broadcast" | "tool_call" | "tool_result" | "handoff" | "info"`

Senders/receivers can also be the literal strings `"user"`, `"system"`, or
`"broadcast"` (only as a receiver) — these are rendered with a special style
in the log and are excluded from the graph edges.
