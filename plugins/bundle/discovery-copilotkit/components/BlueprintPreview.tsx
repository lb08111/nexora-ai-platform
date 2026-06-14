import React from "react";
import { useCoAgentStateRender } from "@copilotkit/react-core";
import type { DiscoveryAgentState, TeamBlueprint } from "./types";

/**
 * Final blueprint preview. Rendered only when the CoAgent has emitted a
 * TeamBlueprint (state.blueprint != null and state.status === "done").
 */
export function BlueprintPreview({ blueprint }: { blueprint: TeamBlueprint }) {
  if (!blueprint) return null;
  return (
    <section
      className="ck-discovery-blueprint"
      data-testid="discovery-blueprint-preview"
    >
      <h2>Blueprint do time</h2>
      <h3>Time proposto</h3>
      <ul>
        {blueprint.proposed_team.map((a) => (
          <li key={a.name}>
            <strong>{a.name}</strong> — <em>{a.role}</em>
            <p>{a.objective}</p>
            {a.tools_integrations?.length ? (
              <small>Integrações: {a.tools_integrations.join(", ")}</small>
            ) : null}
          </li>
        ))}
      </ul>
      {blueprint.roadmap?.length ? (
        <>
          <h3>Roadmap</h3>
          <ol>
            {[...blueprint.roadmap]
              .sort((a, b) => a.order - b.order)
              .map((r) => (
                <li key={r.order}>
                  <strong>{r.title}</strong>
                  {r.rationale ? <em> — {r.rationale}</em> : null}
                </li>
              ))}
          </ol>
        </>
      ) : null}
      {blueprint.open_questions?.length ? (
        <details>
          <summary>Perguntas em aberto</summary>
          <ul>
            {blueprint.open_questions.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}

export function useBlueprintRender() {
  useCoAgentStateRender<DiscoveryAgentState>({
    name: "discovery",
    render: ({ state }) =>
      state?.blueprint ? (
        <BlueprintPreview blueprint={state.blueprint} />
      ) : null,
  });
}
