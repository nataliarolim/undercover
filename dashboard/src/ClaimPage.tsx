import {
  paths,
  useApi,
  type Claim,
  type ClaimHistory,
  type Policy,
  type Step,
} from "./api";
import { StatusBadge } from "./Badge";
import { DecisionPanel } from "./DecisionPanel";
import { day, dollars, label } from "./format";
import { Steps } from "./Steps";

function PolicyPanel({ policyId }: Readonly<{ policyId: string }>) {
  const { data: policy } = useApi<Policy>(paths.policy(policyId));
  if (!policy) return null;

  return (
    <section className="panel" aria-label="Policy">
      <h2>
        Policy <span className="mono muted">{policy.policy_id}</span>
      </h2>
      <dl>
        <dt>Plan</dt>
        <dd>{label(policy.plan)}</dd>
        <dt>Add-ons</dt>
        <dd>{policy.add_ons.map(label).join(", ") || "None"}</dd>
        <dt>Trip</dt>
        <dd>
          {policy.trip.destination}, {day(policy.trip.departs_on)} to{" "}
          {day(policy.trip.returns_on)}
        </dd>
        <dt>Trip cost</dt>
        <dd className="mono">{dollars(policy.trip.trip_cost)}</dd>
        <dt>Travelers</dt>
        <dd>{policy.travelers.join(", ")}</dd>
        <dt>Bought</dt>
        <dd>{day(policy.purchased_on)}</dd>
      </dl>
    </section>
  );
}

function HistoryPanel({ customerId }: Readonly<{ customerId: string }>) {
  const { data: history } = useApi<ClaimHistory>(paths.history(customerId));
  if (!history) return null;

  return (
    <section className="panel" aria-label="Claim history">
      <h2>{history.name}</h2>
      <p className="muted">Customer since {day(history.customer_since)}</p>
      {history.previous_claims.length === 0 ? (
        <p>No earlier claims.</p>
      ) : (
        <ul className="history">
          {history.previous_claims.map((previous) => (
            <li key={previous.claim_id}>
              <span className="mono">{previous.claim_id}</span>{" "}
              {previous.summary}.{" "}
              <span className="muted">
                {label(previous.outcome)}, {dollars(previous.amount_paid)},
                filed {day(previous.filed_on)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ClaimDetails({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <>
      <section className="panel" aria-label="Story">
        <h2>The customer&apos;s story</h2>
        <p>{claim.story}</p>
      </section>
      <section className="panel" aria-label="Items claimed">
        <h2>Items claimed</h2>
        <div className="scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Item</th>
                <th scope="col">Category</th>
                <th scope="col" className="amount">
                  Amount
                </th>
              </tr>
            </thead>
            <tbody>
              {claim.items.map((item) => (
                <tr key={item.description}>
                  <td>{item.description}</td>
                  <td>{label(item.category)}</td>
                  <td className="mono amount">{dollars(item.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="panel" aria-label="Documents">
        <h2>Documents</h2>
        {claim.documents.map((doc) => (
          <article className="document" key={doc.name}>
            <h3>{doc.name}</h3>
            <p className="muted">{label(doc.type)}</p>
            <p>{doc.content}</p>
          </article>
        ))}
      </section>
    </>
  );
}

export function ClaimPage({ claimId }: Readonly<{ claimId: string }>) {
  const claim = useApi<Claim>(paths.claim(claimId), true);
  const steps = useApi<Step[]>(paths.steps(claimId), true);

  if (claim.error) return <p role="alert">{claim.error}</p>;
  if (!claim.data) return <p>Loading the claim</p>;
  const { data } = claim;

  return (
    <>
      <p>
        <a href="#/">Claims queue</a>
      </p>
      <h1 className="claim-title">
        <span className="mono">{data.claim_id}</span>{" "}
        <StatusBadge status={data.status} />
      </h1>
      <p className="lead">{data.summary}</p>
      <p className="muted">
        {label(data.claim_type)} in {data.incident_location} on{" "}
        {day(data.incident_date)}. Submitted {day(data.submitted_on)}. Claimed{" "}
        <span className="mono">{dollars(data.amount_claimed)}</span>.
      </p>
      <div className="columns">
        <div className="stack">
          <ClaimDetails claim={data} />
        </div>
        <div className="stack">
          <DecisionPanel
            claim={data}
            onChange={() => {
              claim.reload();
              steps.reload();
            }}
          />
          <Steps
            steps={steps.data ?? []}
            working={data.status === "in_progress"}
          />
          <PolicyPanel policyId={data.policy_id} />
          <HistoryPanel customerId={data.customer_id} />
        </div>
      </div>
    </>
  );
}
