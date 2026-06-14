// Shared TypeScript shape that mirrors the Python `DiscoveryAgentState`
// pydantic model in ../copilotkit_adapter.py. Kept in this file so every
// component imports the same canonical type.
export type CompanyProfile = {
  name?: string | null;
  segment?: string | null;
  cnae?: string | null;
  size?: string | null;
  business_model?: string | null;
  pains?: string[];
};

export type OpenArea = {
  id: string;
  topic: string;
  confidence: number;
  priority: number;
  notes?: string;
};

export type Integration = {
  kind: string;
  name: string;
  data_location?: string;
  confidence?: number;
};

export type Transcript = { role: "user" | "assistant"; text: string };

export type TeamBlueprint = {
  company_profile: CompanyProfile;
  process_map: { name: string; description?: string }[];
  detected_integrations: Integration[];
  proposed_team: {
    name: string;
    role: string;
    objective: string;
    tasks?: string[];
    tools_integrations?: string[];
    talks_to?: string[];
  }[];
  roadmap: { order: number; title: string; rationale?: string }[];
  open_questions?: string[];
};

export type DiscoveryAgentState = {
  session_id: string;
  status: "in_progress" | "done" | "error";
  question?: string | null;
  company: CompanyProfile;
  open_areas: OpenArea[];
  integrations: Integration[];
  transcript: Transcript[];
  blueprint: TeamBlueprint | null;
  turn_index: number;
  rendered_components: string[];
};
