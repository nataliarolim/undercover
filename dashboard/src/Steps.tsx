import type { SectionRead, Step } from "./api";
import { DOCUMENT_LABELS } from "./format";

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
  if (step.kind === "error") {
    return (
      <p>
        <span className="badge alert">Failed</span> {step.name}: {step.content}
      </p>
    );
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

/** The sections the agent read, once each, from its read_section results. */
function sectionsRead(steps: Step[]): SectionRead[] {
  const read = new Map<string, SectionRead>();
  for (const step of steps) {
    if (
      step.kind === "tool_result" &&
      step.name === "read_section" &&
      !refusal(step.content)
    ) {
      const section = JSON.parse(step.content) as SectionRead;
      read.set(`${section.document} ${String(section.section)}`, section);
    }
  }
  return [...read.values()];
}

export function SectionsRead({ steps }: Readonly<{ steps: Step[] }>) {
  const read = sectionsRead(steps);
  return (
    <section className="panel" aria-label="What the agent read">
      <h2>What the agent read</h2>
      {read.length === 0 ? (
        <p className="muted">No sections read yet.</p>
      ) : (
        <ul className="history">
          {read.map((section) => (
            <li key={`${section.document} ${String(section.section)}`}>
              {DOCUMENT_LABELS[section.document]}, {section.section}.{" "}
              {section.title}
            </li>
          ))}
        </ul>
      )}
    </section>
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
