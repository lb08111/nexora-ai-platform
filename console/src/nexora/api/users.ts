import { request } from "../../api/request";

export interface PlatformUser {
  id: string;
  username: string;
  roles: string[];
  status: "active" | "disabled";
  created_at: number;
  updated_at: number;
}

export interface PlatformRole {
  id: string;
  name: string;
  description: string;
  permissions: string[];
  builtin: boolean;
}

export interface CurrentUser {
  username: string;
  roles: string[];
  permissions: string[];
}

export const usersApi = {
  me: () => request<CurrentUser>("/auth/me"),
  listUsers: () => request<PlatformUser[]>("/auth/users"),
  listRoles: () => request<PlatformRole[]>("/auth/roles"),
  listPermissions: () => request<string[]>("/auth/permissions"),
  createUser: (payload: {
    username: string;
    password: string;
    roles: string[];
  }) =>
    request<PlatformUser>("/auth/users", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateUser: (
    username: string,
    payload: {
      roles?: string[];
      status?: "active" | "disabled";
      password?: string;
    },
  ) =>
    request<PlatformUser>(`/auth/users/${encodeURIComponent(username)}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteUser: (username: string) =>
    request<{ deleted: boolean }>(
      `/auth/users/${encodeURIComponent(username)}`,
      {
        method: "DELETE",
      },
    ),
  createRole: (payload: {
    id: string;
    name: string;
    description?: string;
    permissions: string[];
  }) =>
    request<PlatformRole>("/auth/roles", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateRole: (
    roleId: string,
    payload: {
      name?: string;
      description?: string;
      permissions?: string[];
    },
  ) =>
    request<PlatformRole>(`/auth/roles/${encodeURIComponent(roleId)}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteRole: (roleId: string) =>
    request<{ deleted: boolean }>(`/auth/roles/${encodeURIComponent(roleId)}`, {
      method: "DELETE",
    }),
};
