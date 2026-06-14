import React, { useMemo } from "react";
import { Progress, Tooltip } from "antd";
import type { WorkflowAgent, WorkflowPlan, WorkflowTask } from "./types";
import styles from "./index.module.less";

interface PlanViewProps {
  plan?: WorkflowPlan | null;
  agents: WorkflowAgent[];
  onTaskClick?: (task: WorkflowTask) => void;
}

const STATE_ICON: Record<string, string> = {
  todo: "⬜",
  in_progress: "🔄",
  done: "✅",
  blocked: "⛔",
  abandoned: "✖️",
};

const STATE_CLASS: Record<string, string> = {
  todo: styles.taskStateTodo,
  in_progress: styles.taskStateInProgress,
  done: styles.taskStateDone,
  blocked: styles.taskStateBlocked,
  abandoned: styles.taskStateAbandoned,
};

const PlanView: React.FC<PlanViewProps> = ({ plan, agents, onTaskClick }) => {
  const agentById = useMemo(() => {
    const map = new Map<string, WorkflowAgent>();
    agents.forEach((a) => map.set(a.id, a));
    return map;
  }, [agents]);

  if (!plan) {
    return (
      <div className={styles.planEmpty}>
        <div className={styles.planEmptyIcon}>📋</div>
        <div>No active plan</div>
        <div className={styles.planEmptyHint}>
          Pass a <code>plan</code> prop to visualize plan progress.
        </div>
      </div>
    );
  }

  const tasks = plan.tasks || [];
  const done = tasks.filter(
    (t) => t.state === "done" || t.state === "abandoned",
  ).length;
  const total = tasks.length;
  const percent = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <div className={styles.planView}>
      <div className={styles.planHeader}>
        <div className={styles.planTitleRow}>
          <span className={styles.planTitle}>{plan.name}</span>
          <span
            className={`${styles.taskState} ${
              STATE_CLASS[plan.state] || ""
            }`}
          >
            {plan.state}
          </span>
        </div>
        {plan.description && (
          <div className={styles.planDesc}>{plan.description}</div>
        )}
        <div className={styles.planProgress}>
          <div className={styles.planProgressLabel}>
            Progress — {done}/{total}
          </div>
          <Progress
            percent={percent}
            size="small"
            status={plan.state === "abandoned" ? "exception" : "active"}
            showInfo={false}
          />
        </div>
      </div>

      <ul className={styles.taskList}>
        {tasks.length === 0 && (
          <li className={styles.taskEmpty}>No tasks yet.</li>
        )}
        {tasks.map((task) => {
          const assignee = task.assignedTo
            ? agentById.get(task.assignedTo)
            : undefined;
          return (
            <li
              key={task.id}
              className={styles.taskItem}
              onClick={() => onTaskClick?.(task)}
              style={{ cursor: onTaskClick ? "pointer" : "default" }}
            >
              <span className={styles.taskIcon}>
                {STATE_ICON[task.state] || "⬜"}
              </span>
              <div className={styles.taskBody}>
                <div className={styles.taskNameRow}>
                  <span className={styles.taskName}>{task.name}</span>
                  {assignee && (
                    <Tooltip title={assignee.name}>
                      <span
                        className={styles.taskAssignee}
                        style={{
                          background:
                            assignee.color || "rgba(22, 119, 255, 0.12)",
                        }}
                      >
                        {assignee.avatar ||
                          assignee.name.charAt(0).toUpperCase()}
                      </span>
                    </Tooltip>
                  )}
                </div>
                {task.description && (
                  <div className={styles.taskDesc}>{task.description}</div>
                )}
                {task.outcome && (
                  <div className={styles.taskOutcome}>✓ {task.outcome}</div>
                )}
              </div>
            </li>
          );
        })}
      </ul>

      {plan.outcome && (
        <div className={styles.planOutcome}>
          <strong>Outcome:</strong> {plan.outcome}
        </div>
      )}
    </div>
  );
};

export default PlanView;
