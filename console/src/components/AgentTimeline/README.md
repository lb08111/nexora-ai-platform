# AgentTimeline

Gantt-style horizontal timeline for AI agents. One swimlane per agent, one
colored span per execution step (thought / tool call / LLM call / task /
wait / message / error / custom).

Pairs naturally with `AgentWorkflow`: that component shows **who talks to
whom**, this one shows **when** and **how long** each thing took.

## Quick start

```tsx
import AgentTimeline from "@/components/AgentTimeline";

const agents = [
  { id: "planner", name: "Planner", avatar: "🧠", color: "#722ed1" },
  { id: "coder",   name: "Coder",   avatar: "💻", color: "#1677ff" },
  { id: "qa",      name: "QA",      avatar: "🔍", color: "#52c41a" },
];

const t0 = Date.now() - 30_000;
const spans = [
  { id: "1", agentId: "planner", label: "Draft plan",    kind: "thought",   status: "success", start: t0,         end: t0 + 4000 },
  { id: "2", agentId: "coder",   label: "read_file",     kind: "tool_call", status: "success", start: t0 + 5000,  end: t0 + 6200 },
  { id: "3", agentId: "coder",   label: "gpt-4o",        kind: "llm_call",  status: "success", start: t0 + 6300,  end: t0 + 11_000,
    details: "Generated AgentWorkflow.tsx (2.4k tokens, $0.012)" },
  { id: "4", agentId: "qa",      label: "run tests",     kind: "tool_call", status: "error",   start: t0 + 12_000, end: t0 + 14_500,
    details: "FAIL: AgentGraph.test.tsx — selector not found" },
  { id: "5", agentId: "coder",   label: "edit_file",     kind: "tool_call", status: "running", start: t0 + 15_000 },
];

export default function Page() {
  return <AgentTimeline agents={agents} spans={spans} follow height={420} />;
}
```

## Props

| Prop          | Type                                       | Default | Notes                                              |
| ------------- | ------------------------------------------ | ------- | -------------------------------------------------- |
| `agents`      | `TimelineAgentRow[]`                       | —       | One swimlane row per agent.                        |
| `spans`       | `TimelineSpan[]`                           | —       | Execution segments. `end: null` ⇒ still running.   |
| `height`      | `number \| string`                         | `420`   | Component height.                                  |
| `pxPerMs`     | `number`                                   | auto    | Overrides automatic fit-to-width scaling.          |
| `initialZoom` | `number`                                   | `1`     | Zoom multiplier (zoom buttons multiply by 1.5).    |
| `viewStart`   | `number` (ms)                              | min     | Force viewport start.                              |
| `viewEnd`     | `number` (ms)                              | max     | Force viewport end.                                |
| `follow`      | `boolean`                                  | `false` | Tick clock + auto-scroll right + pause button.     |
| `onSpanClick` | `(span) => void`                           | —       | Fires when a span is clicked.                      |
| `title`       | `ReactNode`                                | —       | Override toolbar title.                            |

### Span kinds → default color

`thought` `#722ed1` · `tool_call` `#1677ff` · `llm_call` `#13c2c2` ·
`task` `#52c41a` · `wait` `#bfbfbf` · `error` `#ff4d4f` ·
`message` `#faad14` · `custom` `#8c8c8c`

`status: "running"` adds an animated stripe overlay; `status: "error"` adds a
red outline. `color` on a span overrides the kind color.