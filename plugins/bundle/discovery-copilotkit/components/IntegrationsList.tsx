import React from "react";
import { useCoAgentStateRender } from "@copilotkit/react-core";
import type { DiscoveryAgentState, Integration } from "./types";

export function IntegrationsList({ items }: { items: Integration[] }) {
  if (!items || items.length === 0) return null;
  return (
    <section
      className="ck-discovery-integrations"
      data-testid="discovery-integrations"
    >
      <h3>Integrações detectadas</h3>
      <ul>
        {items.map((i) => (
          <li key={`${i.kind}:${i.name}`}>
            <span className="ck-kind">{i.kind}</span> — {i.name}
            {i.data_location ? (
              <em className="ck-loc"> ({i.data_location})</em>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function useIntegrationsRender() {
  useCoAgentStateRender<DiscoveryAgentState>({
    name: "discovery",
    render: ({ state }) =>
      state?.integrations?.length ? (
        <IntegrationsList items={state.integrations} />
      ) : null,
  });
}
