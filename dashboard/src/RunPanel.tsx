import { paths, useApi, type Run } from "./api";
import { RunBadge, TodoBadge } from "./Badge";

export function RunPanel() {
  const { data: run, error } = useApi<Run | null>(paths.latestRun, true);

  if (error) return <p role="alert">{error}</p>;
  if (run === undefined) return null;
  if (run === null) {
    return (
      <section className="panel run" aria-label="Current run">
        <h2>Current run</h2>
        <p className="muted">No runs yet.</p>
      </section>
    );
  }

  return (
    <section className="panel run" aria-label="Current run">
      <h2 className="run-title">
        Run <span className="mono">{run.run_id}</span>{" "}
        <RunBadge status={run.status} />
      </h2>
      <p className="muted">Takes at most {run.cap} claims.</p>
      {run.todos.length === 0 ? (
        <p className="muted">No to-do list yet.</p>
      ) : (
        <ol className="todos" aria-label="To-do list">
          {run.todos.map((todo) => (
            <li key={todo.content}>
              <TodoBadge status={todo.status} /> {todo.content}
            </li>
          ))}
        </ol>
      )}
      {run.summary && <p className="summary">{run.summary}</p>}
    </section>
  );
}
