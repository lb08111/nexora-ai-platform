import { request } from "../../api/request";

export interface AgentGrant {
  agent_id: string;
  username: string;
  granted_by: string;
  granted_at: number;
}

export type AddPolicy = "none" | "approval";
export type RemovePolicy = "none" | "log" | "approval";

export interface CapabilityApprovalConfig {
  capability_type: string;
  add_policy: AddPolicy;
  remove_policy: RemovePolicy;
  approver_roles: string[];
  updated_at: number;
}

export interface AgentTemplate {
  template_id: string;
  name: string;
  description: string;
  capabilities: Record<string, string[]>;
  builtin: boolean;
  created_at: number;
  updated_at: number;
}

export const multiTenantApi = {
  // Agent Grants
  listGrantsForAgent: (agentId: string) =>
    request<AgentGrant[]>(
      `/nexora/agent-grants/${encodeURIComponent(agentId)}`,
    ),
  listGrantsForUser: (username: string) =>
    request<AgentGrant[]>(
      `/nexora/agent-grants/user/${encodeURIComponent(username)}`,
    ),
  batchGrant: (agentId: string, usernames: string[]) =>
    request<{ granted: number }>(
      `/nexora/agent-grants/${encodeURIComponent(agentId)}`,
      {
        method: "POST",
        body: JSON.stringify({ usernames }),
      },
    ),
  batchRevoke: (agentId: string, usernames: string[]) =>
    request<{ revoked: number }>(
      `/nexora/agent-grants/${encodeURIComponent(agentId)}`,
      {
        method: "DELETE",
        body: JSON.stringify({ usernames }),
      },
    ),

  // Capability Approval Config
  listApprovalConfigs: () =>
    request<CapabilityApprovalConfig[]>("/nexora/capability-approval-config"),
  updateApprovalConfig: (
    capType: string,
    payload: Partial<CapabilityApprovalConfig>,
  ) =>
    request<CapabilityApprovalConfig>(
      `/nexora/capability-approval-config/${encodeURIComponent(capType)}`,
      {
        method: "PUT",
        body: JSON.stringify(payload),
      },
    ),

  // Agent Templates
  listTemplates: () => request<AgentTemplate[]>("/nexora/agent-templates"),
  createTemplate: (
    payload: Omit<AgentTemplate, "builtin" | "created_at" | "updated_at">,
  ) =>
    request<AgentTemplate>("/nexora/agent-templates", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getTemplate: (templateId: string) =>
    request<AgentTemplate>(
      `/nexora/agent-templates/${encodeURIComponent(templateId)}`,
    ),
  updateTemplate: (templateId: string, payload: Partial<AgentTemplate>) =>
    request<AgentTemplate>(
      `/nexora/agent-templates/${encodeURIComponent(templateId)}`,
      {
        method: "PUT",
        body: JSON.stringify(payload),
      },
    ),
  deleteTemplate: (templateId: string) =>
    request<{ deleted: boolean }>(
      `/nexora/agent-templates/${encodeURIComponent(templateId)}`,
      {
        method: "DELETE",
      },
    ),
};
