import { useState, type SubmitEvent } from "react";
import { postJson, useApi, type Claim, type Handler } from "./api";
import { DecisionBadge } from "./Badge";
import { dollars } from "./format";

function SignOff({
  claim,
  payout,
  handlers,
  onSignedOff,
}: Readonly<{
  claim: Claim;
  payout: number;
  handlers: Handler[];
  onSignedOff: () => void;
}>) {
  const [handlerId, setHandlerId] = useState("");
  const [error, setError] = useState<string>();

  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    postJson(`/api/claims/${claim.claim_id}/sign-off`, {
      handler_id: handlerId,
    }).then(onSignedOff, (failure: unknown) => {
      setError((failure as Error).message);
    });
  };

  return (
    <form className="sign-off" onSubmit={submit}>
      <label>
        Handler{" "}
        <select
          value={handlerId}
          onChange={(event) => {
            setHandlerId(event.target.value);
          }}
        >
          <option value="">Choose a handler</option>
          {handlers.map((handler) => (
            <option key={handler.handler_id} value={handler.handler_id}>
              {handler.name}
            </option>
          ))}
        </select>
      </label>
      <button type="submit" disabled={!handlerId}>
        Sign off and pay {dollars(payout)}
      </button>
      {error && (
        <p className="alert-text" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}

function Payment({
  claim,
  handlers,
}: Readonly<{ claim: Claim; handlers: Handler[] }>) {
  if (claim.paid_amount === null) {
    return <p>Not paid</p>;
  }
  const signer = handlers.find(
    (handler) => handler.handler_id === claim.signed_off_by,
  );
  return (
    <p>
      Paid <span className="mono">{dollars(claim.paid_amount)}</span>
      {signer && `, signed off by ${signer.name}`}
    </p>
  );
}

export function DecisionPanel({
  claim,
  onChange,
}: Readonly<{ claim: Claim; onChange: () => void }>) {
  const { data: handlers = [] } = useApi<Handler[]>("/api/handlers");

  if (claim.decision === null) {
    return (
      <section className="panel" aria-label="Decision">
        <h2>Decision</h2>
        <p className="muted">No decision yet.</p>
      </section>
    );
  }

  return (
    <section className="panel" aria-label="Decision">
      <h2>Decision</h2>
      <p className="decision">
        <DecisionBadge decision={claim.decision} />
        {claim.decision === "approve" && claim.payout !== null && (
          <span className="mono payout">{dollars(claim.payout)}</span>
        )}
      </p>
      <p>{claim.rationale}</p>
      <p className="muted">{claim.policy_section}</p>
      {claim.decision === "approve" &&
        (claim.status === "waiting_for_sign_off" && claim.payout !== null ? (
          <SignOff
            claim={claim}
            payout={claim.payout}
            handlers={handlers}
            onSignedOff={onChange}
          />
        ) : (
          <Payment claim={claim} handlers={handlers} />
        ))}
    </section>
  );
}
