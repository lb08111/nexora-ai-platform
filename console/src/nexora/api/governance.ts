import { request } from "../../api/request";

export type GovernanceSource =
  | "builtin_tool"
  | "mcp"
  | "skill"
  | "plugin"
  | "api"
  | "cli";
export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface GovernancePolicy {
  id: string;
  source: GovernanceSource;
  resource_id: string;
  display_name: string;
  description: string;
  risk_level: RiskLevel;
  allowed_agents?: string[];
  allowed_roles?: string[];
  approval_required: boolean;
  audit_enabled: boolean;
  enabled: boolean;
  updated_at: number;
}

export type GovernancePolicyPayload = Omit<
  GovernancePolicy,
  "id" | "updated_at"
>;

export type ApprovalAction =
  | "mcp.create"
  | "mcp.delete"
  | "skill.create"
  | "skill.delete"
  | "plugin.install"
  | "plugin.uninstall"
  | "tool.create";

export interface ApprovalPolicy {
  id: string;
  action: ApprovalAction;
  display_name: string;
  description: string;
  enabled: boolean;
  approver_roles: string[];
  allow_self_approval: boolean;
  updated_at: number;
}

export type ApprovalPolicyPayload = Omit<ApprovalPolicy, "id" | "updated_at">;

export type ApprovalRequestStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "applied"
  | "failed";

export interface ApprovalRequest {
  id: string;
  action: ApprovalAction;
  status: ApprovalRequestStatus;
  requester: string;
  approver: string;
  resource_type: string;
  resource_id: string;
  resource_name: string;
  summary: string;
  reason: string;
  payload: Record<string, unknown>;
  result: Record<string, unknown>;
  created_at: number;
  updated_at: number;
}

export const governanceApi = {
  listPolicies: () =>
    request<GovernancePolicy[]>("/nexora/governance/policies"),
  savePolicy: (payload: GovernancePolicyPayload) =>
    request<GovernancePolicy>("/nexora/governance/policies", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deletePolicy: (policyId: string) =>
    request<{ deleted: boolean }>(
      `/nexora/governance/policies/${encodeURIComponent(policyId)}`,
      {
        method: "DELETE",
      },
    ),
  listApprovalPolicies: () =>
    request<ApprovalPolicy[]>("/nexora/governance/approval-policies"),
  saveApprovalPolicy: (payload: ApprovalPolicyPayload) =>
    request<ApprovalPolicy>("/nexora/governance/approval-policies", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listApprovalRequests: (query?: {
    status?: ApprovalRequestStatus;
    action?: ApprovalAction;
  }) => {
    const params = new URLSearchParams();
    if (query?.status) params.set("status", query.status);
    if (query?.action) params.set("action", query.action);
    const suffix = params.toString() ? `?${params.toString()}` : "";
    return request<ApprovalRequest[]>(`/nexora/approval-requests${suffix}`);
  },
  approveApprovalRequest: (requestId: string, reason = "") =>
    request<ApprovalRequest>(
      `/nexora/approval-requests/${encodeURIComponent(requestId)}/approve`,
      {
        method: "POST",
        body: JSON.stringify({ reason }),
      },
    ),
  rejectApprovalRequest: (requestId: string, reason = "") =>
    request<ApprovalRequest>(
      `/nexora/approval-requests/${encodeURIComponent(requestId)}/reject`,
      {
        method: "POST",
        body: JSON.stringify({ reason }),
      },
    ),
};
