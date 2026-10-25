import { useSyncExternalStore } from "react";

function subscribe(onChange: () => void) {
  window.addEventListener("hashchange", onChange);
  return () => {
    window.removeEventListener("hashchange", onChange);
  };
}

/** The route after the # in the address, such as /claims/CLM-1001. */
export function useHashRoute(): string {
  return useSyncExternalStore(
    subscribe,
    () => window.location.hash.slice(1) || "/",
  );
}
