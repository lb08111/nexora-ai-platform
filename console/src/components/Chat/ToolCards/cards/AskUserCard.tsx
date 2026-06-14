import React, { useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  AgentCommunicationCard,
  type AgentCommunicationChoice,
  type AgentCommunicationKind,
  type AgentCommunicationStatus,
} from "../../../AgentCommunicationCard";
import type { ToolCallContent } from "../shared/types";

/**
 * AskUserCard — adapter that renders <AgentCommunicationCard /> from a
 * ToolCallContent payload. Registered against tool names that represent
 * agent ⇄ user interaction (ask_user, ask_human, request_user_input, …).
 *
 * Expected tool params shape (all optional):
 *  - message:        string                — the question to show the user
 *  - prompt:         string                — alias for message
 *  - kind:           "text"|"choices"|"confirm"|"info"
 *  - choices:        AgentCommunicationChoice[]
 *  - title:          string
 *  - placeholder:    string
 *  - agent_id:       string
 *  - agent_name:     string
 *  - agent_role:     string
 *  - agent_avatar:   string
 *  - timeout_seconds:number
 *  - required:       boolean
 */
export interface AskUserCardProps {
  content: ToolCallContent;
  isStreaming?: boolean;
}

const asString = (value: unknown, fallback = ""): string =>
  typeof value === "string" ? value : fallback;

const asNumber = (value: unknown): number | undefined =>
  typeof value === "number" && Number.isFinite(value) ? value : undefined;

const asBoolean = (value: unknown): boolean =>
  typeof value === "boolean" ? value : false;

const isKind = (value: unknown): value is AgentCommunicationKind =>
  value === "text" ||
  value === "choices" ||
  value === "confirm" ||
  value === "info";

const normalizeChoices = (
  raw: unknown,
): AgentCommunicationChoice[] | undefined => {
  if (!Array.isArray(raw)) return undefined;
  const out: AgentCommunicationChoice[] = [];
  for (const item of raw) {
    if (typeof item === "string") {
      out.push({ value: item, label: item });
      continue;
    }
    if (item && typeof item === "object") {
      const rec = item as Record<string, unknown>;
      const value = asString(rec.value ?? rec.id ?? rec.key);
      const label = asString(rec.label ?? rec.title ?? value);
      if (!value) continue;
      out.push({
        value,
        label: label || value,
        type:
          rec.type === "primary" ||
          rec.type === "default" ||
          rec.type === "dashed" ||
          rec.type === "link" ||
          rec.type === "text"
            ? rec.type
            : undefined,
        danger: asBoolean(rec.danger),
      });
    }
  }
  return out.length > 0 ? out : undefined;
};

const AskUserCard: React.FC<AskUserCardProps> = ({ content, isStreaming }) => {
  const { t } = useTranslation();
  const params = useMemo(() => content.params || {}, [content.params]);

  const message = useMemo(() => {
    return (
      asString(params.message) ||
      asString(params.prompt) ||
      asString(params.question) ||
      ""
    );
  }, [params]);

  const kind: AgentCommunicationKind = isKind(params.kind)
    ? params.kind
    : Array.isArray(params.choices)
    ? "choices"
    : "text";

  const status: AgentCommunicationStatus = (() => {
    if (content.status === "error") return "error";
    if (content.status === "done") return "done";
    if (isStreaming) return "thinking";
    return "waiting";
  })();

  const choices = useMemo(
    () => normalizeChoices(params.choices),
    [params.choices],
  );

  return (
    <AgentCommunicationCard
      agentId={asString(params.agent_id) || undefined}
      agentName={asString(params.agent_name) || undefined}
      agentRole={asString(params.agent_role) || undefined}
      agentAvatarUrl={asString(params.agent_avatar) || undefined}
      title={asString(params.title) || t("tool.askUser", "Ask user")}
      message={message || t("agentComm.title", "Agent message")}
      kind={kind}
      choices={choices}
      placeholder={asString(params.placeholder) || undefined}
      timeoutSeconds={asNumber(params.timeout_seconds)}
      required={asBoolean(params.required)}
      status={status}
      copyable
      disabled={content.status !== "calling"}
    />
  );
};

export default AskUserCard;
