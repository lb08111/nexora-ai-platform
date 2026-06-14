import type { GovernancePolicy, GovernanceSource } from "../api/governance";

export function canAgentUseResource(
  policies: GovernancePolicy[],
  source: GovernanceSource,
  resourceId: string,
  agentId?: string | null,
) {
  if (!agentId) return true;
  const policy = policies.find(
    (item) => item.source === source && item.resource_id === resourceId,
  );
  if (!policy) return true;
  if (!policy.enabled) return false;

  const allowedAgents =
    policy.allowed_agents && policy.allowed_agents.length > 0
      ? policy.allowed_agents
      : policy.allowed_roles?.filter(
          (id) => !["admin", "operator"].includes(id),
        ) || [];

  if (allowedAgents.length === 0) return true;
  return allowedAgents.includes(agentId);
}

export function filterResourcesByAgent<T>(
  items: T[],
  policies: GovernancePolicy[],
  source: GovernanceSource,
  getResourceId: (item: T) => string,
  agentId?: string | null,
) {
  return items.filter((item) =>
    canAgentUseResource(policies, source, getResourceId(item), agentId),
  );
}
