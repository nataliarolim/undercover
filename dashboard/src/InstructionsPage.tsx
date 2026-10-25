import { paths, useApi, type Instructions } from "./api";

export function InstructionsPage() {
  const { data, error } = useApi<Instructions>(paths.instructions);

  if (error) return <p role="alert">{error}</p>;
  if (!data) return <p>Loading the instructions</p>;

  return (
    <>
      <h1>Agent instructions</h1>
      <p className="muted">What the UnderCover Agent is told. Read only.</p>
      <section className="panel" aria-label="Working a claim">
        <h2>Working a claim</h2>
        <pre className="instructions">{data.claim}</pre>
      </section>
    </>
  );
}
