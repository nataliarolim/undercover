import type { Step } from "./api";

/** The reason in a refusal from the backend, such as {"detail":"..."}. */
function refusal(content: string): string | undefined {
  if (!content.startsWith('{"detail":')) return undefined;
  const { detail } = JSON.parse(content) as { detail: unknown };
  return typeof detail === "string" ? detail : content;
}

function StepItem({ step }: Readonly<{ step: Step }>) {
  if (step.kind === "message") {
    return <blockquote className="quote">{step.content}</blockquote>;
  }
  if (step.kind === "tool_call") {
    return (
      <p>
        Called <span className="mono">{step.name}</span>{" "}
        <span className="mono muted">{step.content}</span>
      </p>
    );
  }
  const refused = refusal(step.content);
  if (refused) {
    return (
      <p>
        <span className="badge alert">Refused</span> {refused}
      </p>
    );
  }
  return (
    <details>
      <summary>
        Result of <span className="mono">{step.name}</span>
      </summary>
      <pre className="result">{step.content}</pre>
    </details>
  );
}

export function Steps({
  steps,
  working,
}: Readonly<{ steps: Step[]; working: boolean }>) {
  return (
    <section className="panel" aria-label="Agent steps">
      <h2>Agent steps</h2>
      {working && <p className="muted">The agent is working on this claim.</p>}
      {steps.length === 0 ? (
        <p className="muted">No steps yet.</p>
      ) : (
        <ol className="steps">
          {steps.map((step) => (
            <li key={step.step_id}>
              <StepItem step={step} />
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
