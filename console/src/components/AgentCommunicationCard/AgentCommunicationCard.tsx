import {
  useState,
  useEffect,
  useCallback,
  useMemo,
  useRef,
  type ReactNode,
} from "react";
import { Avatar, Button, Card, Input, Space, Tag, Typography } from "antd";
import {
  Bot,
  Check,
  Clock,
  Copy,
  MessageSquare,
  Send,
  Sparkles,
  X,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import styles from "./AgentCommunicationCard.module.less";

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

/* ────────────────────────────────────────────────────────────────────────── */
/* Public types                                                               */
/* ────────────────────────────────────────────────────────────────────────── */

export type AgentCommunicationKind = "text" | "choices" | "confirm" | "info";

export type AgentCommunicationStatus =
  | "waiting"
  | "thinking"
  | "done"
  | "error";

export interface AgentCommunicationChoice {
  /** Stable key returned via onSubmit. */
  value: string;
  /** Human-readable label shown on the button. */
  label: string;
  /** Optional Ant Design button type override. */
  type?: "primary" | "default" | "dashed" | "link" | "text";
  /** Mark as destructive (red) action. */
  danger?: boolean;
  /** Optional leading icon. */
  icon?: ReactNode;
}

export interface AgentCommunicationSubmitPayload {
  /** Discriminates the response shape. */
  kind: AgentCommunicationKind;
  /** Free-text response (kind = "text"). */
  text?: string;
  /** Choice value (kind = "choices" | "confirm"). */
  value?: string;
}

export interface AgentCommunicationCardProps {
  /** Identifier of the agent that originated the message. */
  agentId?: string;
  /** Display name shown in the header. */
  agentName?: string;
  /** Optional avatar URL. Falls back to a Bot icon. */
  agentAvatarUrl?: string;
  /** Optional role / tag (e.g. "Researcher", "Reviewer"). */
  agentRole?: string;

  /** Message body. Either string or fully-rendered ReactNode. */
  message: ReactNode;

  /** Interaction mode. */
  kind?: AgentCommunicationKind;

  /** Choices for kind="choices". */
  choices?: AgentCommunicationChoice[];

  /** Custom placeholder for the textarea (kind="text"). */
  placeholder?: string;
  /** Pre-filled textarea value. */
  defaultValue?: string;
  /** Max length for the textarea. */
  maxLength?: number;
  /** Require a value before submit is enabled (kind="text"). */
  required?: boolean;

  /** Header title override. Defaults to a translated "Agent message". */
  title?: string;
  /** Status badge in the header. */
  status?: AgentCommunicationStatus;

  /** Unix seconds. When provided the card shows a countdown until timeoutSeconds. */
  createdAt?: number;
  /** Seconds until the interaction expires. */
  timeoutSeconds?: number;

  /** Render a copy button on the message body. */
  copyable?: boolean;

  /** Disable all controls (read-only). */
  disabled?: boolean;
  /** External loading state, applied to action buttons. */
  loading?: boolean;

  /** Called when the user submits. */
  onSubmit?: (payload: AgentCommunicationSubmitPayload) => void | Promise<void>;
  /** Called when the user dismisses / cancels. Hides the cancel button when omitted. */
  onCancel?: () => void;

  /** Extra className on the outer Card. */
  className?: string;
}

/* ────────────────────────────────────────────────────────────────────────── */
/* Component                                                                  */
/* ────────────────────────────────────────────────────────────────────────── */

export function AgentCommunicationCard({
  agentId,
  agentName,
  agentAvatarUrl,
  agentRole,
  message,
  kind = "text",
  choices,
  placeholder,
  defaultValue = "",
  maxLength = 4000,
  required = false,
  title,
  status = "waiting",
  createdAt,
  timeoutSeconds,
  copyable = false,
  disabled = false,
  loading = false,
  onSubmit,
  onCancel,
  className,
}: AgentCommunicationCardProps) {
  const { t } = useTranslation();

  const [value, setValue] = useState<string>(defaultValue);
  const [submitting, setSubmitting] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [remaining, setRemaining] = useState<number | null>(
    typeof timeoutSeconds === "number" ? timeoutSeconds : null,
  );
  const textareaRef = useRef<React.ElementRef<typeof TextArea> | null>(null);

  /* Countdown ──────────────────────────────────────────────────────────── */
  useEffect(() => {
    if (typeof timeoutSeconds !== "number") return;
    const base = typeof createdAt === "number" ? createdAt : Date.now() / 1000;
    const tick = () => {
      const elapsed = Date.now() / 1000 - base;
      setRemaining(Math.max(0, Math.floor(timeoutSeconds - elapsed)));
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [createdAt, timeoutSeconds]);

  const isTimedOut = remaining !== null && remaining <= 0;
  const isInteractive = !disabled && !isTimedOut && kind !== "info";

  /* Derived display ────────────────────────────────────────────────────── */
  const headerTitle = useMemo(() => {
    if (title) return title;
    return t("agentComm.title", "Agent message");
  }, [title, t]);

  const displayName = useMemo(() => {
    if (agentName) return agentName;
    if (agentId) return agentId;
    return t("agentComm.defaultAgentName", "Agent");
  }, [agentName, agentId, t]);

  const statusMeta = useMemo(() => {
    switch (status) {
      case "thinking":
        return {
          color: "processing" as const,
          label: t("agentComm.status.thinking", "Thinking…"),
        };
      case "done":
        return {
          color: "success" as const,
          label: t("agentComm.status.done", "Done"),
        };
      case "error":
        return {
          color: "error" as const,
          label: t("agentComm.status.error", "Error"),
        };
      case "waiting":
      default:
        return {
          color: "default" as const,
          label: t("agentComm.status.waiting", "Waiting for you"),
        };
    }
  }, [status, t]);

  /* Handlers ───────────────────────────────────────────────────────────── */
  const handleCopy = useCallback(async () => {
    if (typeof message !== "string") return;
    try {
      await navigator.clipboard.writeText(message);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  }, [message]);

  const runSubmit = useCallback(
    async (
      payload: AgentCommunicationSubmitPayload,
      loadingKey: string,
    ): Promise<void> => {
      if (!onSubmit) return;
      setSubmitting(loadingKey);
      try {
        await onSubmit(payload);
      } finally {
        setSubmitting(null);
      }
    },
    [onSubmit],
  );

  const handleTextSubmit = useCallback(() => {
    const text = value.trim();
    if (required && !text) {
      textareaRef.current?.focus();
      return;
    }
    void runSubmit({ kind: "text", text }, "text");
  }, [value, required, runSubmit]);

  const handleChoice = useCallback(
    (choiceValue: string) => {
      const responseKind: AgentCommunicationKind =
        kind === "confirm" ? "confirm" : "choices";
      void runSubmit({ kind: responseKind, value: choiceValue }, choiceValue);
    },
    [kind, runSubmit],
  );

  const handleTextareaKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
      const isSubmitCombo =
        event.key === "Enter" && (event.metaKey || event.ctrlKey);
      if (isSubmitCombo) {
        event.preventDefault();
        handleTextSubmit();
      }
    },
    [handleTextSubmit],
  );

  /* Choices (with confirm shorthand) ───────────────────────────────────── */
  const effectiveChoices: AgentCommunicationChoice[] | undefined =
    useMemo(() => {
      if (kind === "confirm") {
        return (
          choices ?? [
            {
              value: "no",
              label: t("agentComm.no", "No"),
              type: "default",
              icon: <X size={14} />,
            },
            {
              value: "yes",
              label: t("agentComm.yes", "Yes"),
              type: "primary",
              icon: <Check size={14} />,
            },
          ]
        );
      }
      return choices;
    }, [kind, choices, t]);

  /* Render ─────────────────────────────────────────────────────────────── */
  return (
    <Card
      className={`${styles.commCard}${className ? ` ${className}` : ""}`}
      data-agent-id={agentId}
      data-kind={kind}
      data-status={status}
      variant="borderless"
    >
      <div className={styles.header}>
        <Space size={10} align="center" className={styles.identity}>
          {agentAvatarUrl ? (
            <Avatar src={agentAvatarUrl} size={28} />
          ) : (
            <Avatar
              size={28}
              icon={<Bot size={16} />}
              className={styles.avatarFallback}
            />
          )}
          <div className={styles.identityText}>
            <Space size={6} align="center">
              <Text className={styles.agentName}>{displayName}</Text>
              {agentRole ? (
                <Tag className={styles.roleTag} color="blue">
                  {agentRole}
                </Tag>
              ) : null}
            </Space>
            <Space size={6} align="center" className={styles.subtitle}>
              <MessageSquare size={12} className={styles.subtitleIcon} />
              <Text className={styles.subtitleText}>{headerTitle}</Text>
            </Space>
          </div>
        </Space>

        <Space size={6} align="center" className={styles.meta}>
          <Tag color={statusMeta.color} className={styles.statusTag}>
            {status === "thinking" ? (
              <Sparkles size={10} className={styles.statusIcon} />
            ) : null}
            {statusMeta.label}
          </Tag>
          {remaining !== null ? (
            <Space size={4} align="center" className={styles.timer}>
              <Clock size={12} className={styles.timerIcon} />
              <Text className={styles.timerText}>
                {Math.floor(remaining / 60)}:
                {String(remaining % 60).padStart(2, "0")}
              </Text>
            </Space>
          ) : null}
        </Space>
      </div>

      <div className={styles.body}>
        <div className={styles.messageBox}>
          {typeof message === "string" ? (
            <Paragraph className={styles.messageText}>{message}</Paragraph>
          ) : (
            <div className={styles.messageNode}>{message}</div>
          )}
          {copyable && typeof message === "string" ? (
            <button
              type="button"
              className={`${styles.copyButton} ${copied ? styles.copied : ""}`}
              onClick={handleCopy}
              title={t("common.copy", "Copy")}
              aria-label={t("common.copy", "Copy")}
            >
              <Copy size={12} />
            </button>
          ) : null}
        </div>

        {kind === "text" && isInteractive ? (
          <div className={styles.inputArea}>
            <TextArea
              ref={textareaRef}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={handleTextareaKeyDown}
              placeholder={
                placeholder ??
                t("agentComm.placeholder", "Reply to the agent…")
              }
              autoSize={{ minRows: 2, maxRows: 8 }}
              maxLength={maxLength}
              disabled={submitting !== null || loading}
              className={styles.textarea}
            />
            <Text className={styles.hint}>
              {t("agentComm.submitHint", "Press Ctrl/Cmd + Enter to send")}
            </Text>
          </div>
        ) : null}
      </div>

      {(kind !== "info" || onCancel) && (
        <div className={styles.actions}>
          {isTimedOut ? (
            <Text className={styles.timeoutHint}>
              {t("agentComm.timedOut", "This request has timed out.")}
            </Text>
          ) : null}

          {onCancel ? (
            <Button
              type="default"
              onClick={onCancel}
              disabled={submitting !== null || loading}
            >
              {t("agentComm.dismiss", "Dismiss")}
            </Button>
          ) : null}

          {kind === "text" && isInteractive ? (
            <Button
              type="primary"
              icon={<Send size={14} />}
              onClick={handleTextSubmit}
              loading={submitting === "text" || loading}
              disabled={
                (required && !value.trim()) ||
                submitting !== null ||
                loading
              }
            >
              {t("agentComm.send", "Send")}
            </Button>
          ) : null}

          {(kind === "choices" || kind === "confirm") &&
          isInteractive &&
          effectiveChoices?.length
            ? effectiveChoices.map((choice) => (
                <Button
                  key={choice.value}
                  type={choice.type ?? "default"}
                  danger={choice.danger}
                  icon={choice.icon}
                  onClick={() => handleChoice(choice.value)}
                  loading={submitting === choice.value}
                  disabled={submitting !== null || loading}
                >
                  {choice.label}
                </Button>
              ))
            : null}
        </div>
      )}
    </Card>
  );
}

export default AgentCommunicationCard;
