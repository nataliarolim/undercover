import { STATUSES, paths, useApi, type ClaimSummary } from "./api";
import { DecisionBadge, StatusBadge } from "./Badge";
import { dollars, label } from "./format";
import { RunPanel } from "./RunPanel";

export function QueuePage() {
  const { data: claims, error } = useApi<ClaimSummary[]>(paths.claims, true);

  if (error) return <p role="alert">{error}</p>;
  if (!claims) return <p>Loading the queue</p>;

  return (
    <>
      <h1>Claims queue</h1>
      <ul className="tiles" aria-label="Claims by status">
        {STATUSES.map((status) => (
          <li className="panel tile" key={status}>
            <StatusBadge status={status} />
            <span className="count">
              {claims.filter((claim) => claim.status === status).length}
            </span>
          </li>
        ))}
      </ul>
      <RunPanel />
      <div className="panel table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">Claim</th>
              <th scope="col">Summary</th>
              <th scope="col">Type</th>
              <th scope="col" className="amount">
                Claimed
              </th>
              <th scope="col">Status</th>
              <th scope="col">Decision</th>
              <th scope="col" className="amount">
                Payout
              </th>
            </tr>
          </thead>
          <tbody>
            {claims.map((claim) => (
              <tr key={claim.claim_id}>
                <td className="mono">
                  <a href={`#/claims/${claim.claim_id}`}>{claim.claim_id}</a>
                </td>
                <td>{claim.summary}</td>
                <td>{label(claim.claim_type)}</td>
                <td className="mono amount">{dollars(claim.amount_claimed)}</td>
                <td>
                  <StatusBadge status={claim.status} />
                </td>
                <td>
                  {claim.decision && (
                    <DecisionBadge decision={claim.decision} />
                  )}
                </td>
                <td className="mono amount">
                  {claim.payout === null ? "" : dollars(claim.payout)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
