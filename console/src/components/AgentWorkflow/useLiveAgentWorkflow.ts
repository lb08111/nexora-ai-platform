import { useCallback, useEffect, useRef, useState } from "react";
import { agentsApi } from "../../api/modules/agents";
import {
  planApi,
  subscribePlanUpdates,
  type PlanStateResponse,
} from "../../api/modules/plan";
import type {
  WorkflowAgent,
  WorkflowMessage,
  WorkflowPlan,
  WorkflowTask,
} from "./types";

/**
 * Optional hook that wires the AgentWorkflow component into the existing
 * backend APIs (agents list + plan state). Communication messages are not
 * fetched automatically — pass them through `pushMessage` from your own
 * source (chat stream, SSE, websocket, etc.).
 */
export interface UseLiveAgentWorkflowOptions {
  /** Poll interval for the agent list in ms. Default: 15_000. */
  agentPollInterval?: number;
  /** Cap on the rolling messages buffer. Default: 500. */
  messageBufferSize?: number;
  /** If false, the hook does nothing. Useful for conditional mounting. */
  enabled?: boolean;
}

export interface UseLiveAgentWorkflowResult {
  agents: WorkflowAgent[];
  plan: WorkflowPlan | null;
  messages: WorkflowMessage[];
  loading: boolean;
  error: unknown;
  /** Append a message to the live buffer (e.g. from your chat SSE). */
  pushMessage: (msg: WorkflowMessage) => void;
  /** Replace the buffered messages entirely. */
  setMessages: (msgs: WorkflowMessage[]) => void;
  refresh: () => Promise<void>;
}

function planFromResponse(p: PlanStateResponse | null): WorkflowPlan | null {
  if (!p) return null;
  const tasks: WorkflowTask[] = (p.subtasks || []).map((s, i) => ({
    id: `${p.id}-${i}`,
    name: s.name,
    description: s.description,
    state: s.state,
    outcome: s.outcome ?? undefined,
    createdAt: s.created_at ?? undefined,
    finishedAt: s.finished_at ?? undefined,
  }));
  return {
    id: p.id,
    name: p.name,
    description: p.description,
    state: p.state,
    tasks,
    outcome: p.outcome ?? undefined,
  };
}

export function useLiveAgentWorkflow(
  options: UseLiveAgentWorkflowOptions = {},
): UseLiveAgentWorkflowResult {
  const {
    agentPollInterval = 15_000,
    messageBufferSize = 500,
    enabled = true,
  } = options;

  const [agents, setAgents] = useState<WorkflowAgent[]>([]);
  const [plan, setPlan] = useState<WorkflowPlan | null>(null);
  const [messages, setMessagesState] = useState<WorkflowMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const messagesRef = useRef<WorkflowMessage[]>([]);

  const setMessages = useCallback(
    (msgs: WorkflowMessage[]) => {
      const trimmed = msgs.slice(-messageBufferSize);
      messagesRef.current = trimmed;
      setMessagesState(trimmed);
    },
    [messageBufferSize],
  );

  const pushMessage = useCallback(
    (msg: WorkflowMessage) => {
      const next = [...messagesRef.current, msg].slice(-messageBufferSize);
      messagesRef.current = next;
      setMessagesState(next);
    },
    [messageBufferSize],
  );

  const fetchAgents = useCallback(async () => {
    try {
      const data = await agentsApi.listAgents();
      const mapped: WorkflowAgent[] = data.agents.map((a) => ({
        id: a.id,
        name: a.name,
        description: a.description,
        status: a.enabled ? "idle" : "waiting",
      }));
      setAgents(mapped);
    } catch (err) {
      setError(err);
    }
  }, []);

  const fetchPlan = useCallback(async () => {
    try {
      const sid = (window as unknown as { currentSessionId?: string })
        .currentSessionId;
      const data = await planApi.getCurrentPlan(sid || undefined);
      setPlan(planFromResponse(data));
    } catch (err) {
      setError(err);
    }
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      await Promise.all([fetchAgents(), fetchPlan()]);
    } finally {
      setLoading(false);
    }
  }, [fetchAgents, fetchPlan]);

  useEffect(() => {
    if (!enabled) return;
    refresh();
    const interval = setInterval(fetchAgents, agentPollInterval);
    return () => clearInterval(interval);
  }, [enabled, refresh, fetchAgents, agentPollInterval]);

  useEffect(() => {
    if (!enabled) return;
    const unsub = subscribePlanUpdates((updated) => {
      setPlan(planFromResponse(updated));
    });
    return () => unsub();
  }, [enabled]);

  return {
    agents,
    plan,
    messages,
    loading,
    error,
    pushMessage,
    setMessages,
    refresh,
  };
}

export default useLiveAgentWorkflow;
