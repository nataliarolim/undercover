import { ClaimPage } from "./ClaimPage";
import { InstructionsPage } from "./InstructionsPage";
import { QueuePage } from "./QueuePage";
import { useHashRoute } from "./router";

function Page({ route }: Readonly<{ route: string }>) {
  if (route === "/instructions") return <InstructionsPage />;
  const claimId = /^\/claims\/([^/]+)$/.exec(route)?.[1];
  if (claimId) return <ClaimPage key={claimId} claimId={claimId} />;
  return <QueuePage />;
}

export function App() {
  const route = useHashRoute();

  return (
    <>
      <header className="header">
        <a className="brand" href="#/">
          UnderCover <span className="tagline">Claims desk</span>
        </a>
        <nav aria-label="Main">
          <a href="#/" aria-current={route === "/" ? "page" : undefined}>
            Queue
          </a>
          <a
            href="#/instructions"
            aria-current={route === "/instructions" ? "page" : undefined}
          >
            Instructions
          </a>
        </nav>
      </header>
      <main>
        <Page route={route} />
      </main>
    </>
  );
}
