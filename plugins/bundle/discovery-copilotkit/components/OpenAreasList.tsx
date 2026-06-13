import React from "react";
import { useCoAgentStateRender } from "@copilotkit/react-core";
import type { DiscoveryAgentState, OpenArea } from "./types";

/** Generative UI for the discovery agent's open ramifications. */
export function OpenAreasList({ areas }: { areas: OpenArea[] }) {
  if (!areas || areas.length === 0) return null;
  const sorted = [...areas].sort(
    (a, b) => a.confidence - b.confidence || b.priority - a.priority,
  );
  return (
    <section className="ck-discovery-areas" data-testid="discovery-open-areas">
      <h3>Áreas em aberto</h3>
      <ul>
        {sorted.map((a) => (
          <li key={a.id} className={`ck-prio-${a.priority}`}>
            <strong>{a.topic}</strong>
            <span className="ck-confidence" aria-label="confiança">
              {Math.round((a.confidence ?? 0) * 100)}%
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function useOpenAreasRender() {
  useCoAgentStateRender<DiscoveryAgentState>({
    name: "discovery",
    render: ({ state }) =>
      state?.open_areas?.length ? (
        <OpenAreasList areas={state.open_areas} />
      ) : null,
  });
}
