import { request } from "../../api/request";

export interface AuditEvent {
  id: string;
  timestamp: number;
  actor: string;
  action: string;
  resource_type: string;
  resource_id: string;
  status: string;
  ip: string;
  user_agent: string;
  detail: Record<string, unknown>;
}

export interface AuditQuery {
  limit?: number;
  actor?: string;
  action?: string;
  status?: string;
  start_time?: number;
  end_time?: number;
}

function buildQuery(params: AuditQuery = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  });
  const query = search.toString();
  return query ? `?${query}` : "";
}

export const auditApi = {
  listEvents: (params?: AuditQuery) =>
    request<AuditEvent[]>(`/jotaduo/audit/events${buildQuery(params)}`),
  exportEventsUrl: (params?: AuditQuery) =>
    `/api/jotaduo/audit/events/export${buildQuery(params)}`,
  recordPageView: (path: string, title: string) =>
    request<{ recorded: boolean }>("/jotaduo/audit/page-view", {
      method: "POST",
      body: JSON.stringify({ path, title }),
    }),
};
