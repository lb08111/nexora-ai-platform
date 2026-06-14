import React from "react";
import { useCoAgentStateRender } from "@copilotkit/react-core";
import type { DiscoveryAgentState, CompanyProfile } from "./types";

/**
 * Renders the company profile slice of the discovery CoAgent state.
 *
 * Bound by DiscoveryAgentPanel via useCoAgentStateRender({ name: "discovery",
 * render: ({ state }) => <CompanyProfileCard company={state.company} /> }).
 */
export function CompanyProfileCard({ company }: { company: CompanyProfile }) {
  if (!company || Object.keys(company).length === 0) return null;
  return (
    <section
      className="ck-discovery-company"
      data-testid="discovery-company-profile"
    >
      <h3>Perfil da empresa</h3>
      <dl>
        {company.segment && (
          <>
            <dt>Segmento</dt>
            <dd>{company.segment}</dd>
          </>
        )}
        {company.size && (
          <>
            <dt>Porte</dt>
            <dd>{company.size}</dd>
          </>
        )}
        {company.business_model && (
          <>
            <dt>Modelo</dt>
            <dd>{company.business_model}</dd>
          </>
        )}
      </dl>
      {company.pains && company.pains.length > 0 && (
        <ul className="ck-discovery-pains">
          {company.pains.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

// Hook helper used by DiscoveryAgentPanel; kept here so the binding lives
// next to the component it renders (mirrors CopilotKit examples).
export function useCompanyProfileRender() {
  useCoAgentStateRender<DiscoveryAgentState>({
    name: "discovery",
    render: ({ state }) =>
      state?.company ? <CompanyProfileCard company={state.company} /> : null,
  });
}
