import React from "react";
import { CopilotKit, useCoAgent } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import type { DiscoveryAgentState } from "./types";
import { useCompanyProfileRender } from "./CompanyProfileCard";
import { useOpenAreasRender } from "./OpenAreasList";
import { useIntegrationsRender } from "./IntegrationsList";
import { useBlueprintRender } from "./BlueprintPreview";

/**
 * Top-level panel that wires the discovery CoAgent into CopilotKit.
 *
 * - Provides the CopilotKit context (runtime URL is the plugin router
 *   mounted at /api/discovery-copilotkit by plugin.py).
 * - Initialises the discovery CoAgent with empty state.
 * - Mounts every renderer hook so each state slice gets its component.
 */
export function DiscoveryAgentPanel({
  runtimeUrl = "/api/discovery-copilotkit",
}: {
  runtimeUrl?: string;
}) {
  return (
    <CopilotKit runtimeUrl={runtimeUrl} agent="discovery">
      <DiscoveryAgentInner />
    </CopilotKit>
  );
}

function DiscoveryAgentInner() {
  // useCoAgent gives the React tree a typed handle to the shared state
  // that the Python router pushes through /sessions/{id} updates.
  const { state } = useCoAgent<DiscoveryAgentState>({
    name: "discovery",
    initialState: {
      session_id: "",
      status: "in_progress",
      company: {},
      open_areas: [],
      integrations: [],
      transcript: [],
      blueprint: null,
      turn_index: 0,
      rendered_components: [],
    },
  });

  // Mount one renderer per generative-UI component. Each hook calls
  // useCoAgentStateRender so CopilotKit re-renders the slice whenever
  // the agent pushes a new state delta — no manual prop-drilling needed.
  useCompanyProfileRender();
  useOpenAreasRender();
  useIntegrationsRender();
  useBlueprintRender();

  return (
    <div
      className="ck-discovery-panel"
      data-testid="discovery-agent-panel"
      data-status={state?.status ?? "in_progress"}
    >
      <CopilotChat
        labels={{
          title: "Discovery",
          initial: "Olá! Vou te ajudar a desenhar o time de agentes.",
        }}
      />
    </div>
  );
}

export default DiscoveryAgentPanel;
