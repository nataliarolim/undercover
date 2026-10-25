import { useApi, type Instructions } from "./api";

export function InstructionsPage() {
  const { data, error } = useApi<Instructions>("/api/instructions");

  if (error) return <p role="alert">{error}</p>;
  if (!data) return <p>Loading the instructions</p>;

  return (
    <>
      <h1>Agent instructions</h1>
      <p className="muted">
        What the UnderCover Agent is told before every claim. Read only.
      </p>
      <pre className="panel instructions">{data.instructions}</pre>
    </>
  );
}
