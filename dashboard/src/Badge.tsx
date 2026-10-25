import type { DecisionKind, RunStatus, Status, TodoStatus } from "./api";
import {
  DECISION_LABELS,
  RUN_LABELS,
  STATUS_LABELS,
  TODO_LABELS,
} from "./format";

export function StatusBadge({ status }: Readonly<{ status: Status }>) {
  return (
    <span className={`badge status-${status}`}>{STATUS_LABELS[status]}</span>
  );
}

export function DecisionBadge({
  decision,
}: Readonly<{ decision: DecisionKind }>) {
  return (
    <span className={`badge decision-${decision}`}>
      {DECISION_LABELS[decision]}
    </span>
  );
}

export function TodoBadge({ status }: Readonly<{ status: TodoStatus }>) {
  return <span className={`badge todo-${status}`}>{TODO_LABELS[status]}</span>;
}

export function RunBadge({ status }: Readonly<{ status: RunStatus }>) {
  return <span className={`badge run-${status}`}>{RUN_LABELS[status]}</span>;
}
