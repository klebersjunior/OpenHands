/**
 * Client API for the internal app-login gate served by static-server/ingress.
 * These routes are NOT agent-server endpoints — they live on the canvas proxy.
 */

import type {
  AppLoginGroup,
  AppLoginSession,
  AppLoginUser,
  AppPermission,
} from "#/types/app-login-rbac";

const APP_LOGIN_BASE = "/api/app-login";

export type AppLoginStatus = {
  enabled: boolean;
};

export type { AppLoginGroup, AppLoginSession, AppLoginUser };

async function parseJson<T>(response: Response): Promise<T> {
  try {
    return (await response.json()) as T;
  } catch {
    throw new Error(`Unexpected response (${response.status})`);
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<
  | { ok: true; data: T; status: number }
  | { ok: false; error: string; status: number }
> {
  const response = await fetch(`${APP_LOGIN_BASE}${path}`, {
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
    ...init,
  });

  const data = await parseJson<T & { error?: string }>(response);
  if (!response.ok) {
    return {
      ok: false,
      status: response.status,
      error:
        typeof data?.error === "string" && data.error
          ? data.error
          : `Request failed (${response.status})`,
    };
  }
  return { ok: true, status: response.status, data };
}

function unwrap<T>(
  result: Awaited<ReturnType<typeof request<T>>>,
): T {
  if (!result.ok) {
    throw new Error(result.error);
  }
  return result.data;
}

export class AppLoginService {
  static async getStatus(): Promise<AppLoginStatus> {
    const result = await request<AppLoginStatus>("/status");
    if (!result.ok) {
      return { enabled: false };
    }
    return result.data;
  }

  static async getSession(): Promise<AppLoginSession> {
    const result = await request<AppLoginSession>("/me");
    if (!result.ok) {
      return { authenticated: false };
    }
    return result.data;
  }

  static async login(
    username: string,
    password: string,
  ): Promise<{ ok: true; username: string } | { ok: false; error: string }> {
    const result = await request<AppLoginSession>("/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    if (!result.ok) {
      return { ok: false, error: result.error };
    }
    return {
      ok: true,
      username: result.data.username ?? username,
    };
  }

  static async logout(): Promise<void> {
    await request("/logout", { method: "POST" });
  }

  static async listUsers(): Promise<AppLoginUser[]> {
    return unwrap(await request<{ users: AppLoginUser[] }>("/users")).users;
  }

  static async createUser(input: {
    username: string;
    password: string;
    groupId?: string;
  }): Promise<AppLoginUser> {
    return unwrap(
      await request<AppLoginUser>("/users", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    );
  }

  static async updateUserGroup(
    username: string,
    groupId: string,
  ): Promise<AppLoginUser> {
    return unwrap(
      await request<AppLoginUser>(`/users/${encodeURIComponent(username)}`, {
        method: "PATCH",
        body: JSON.stringify({ groupId }),
      }),
    );
  }

  static async deleteUser(username: string): Promise<void> {
    unwrap(
      await request<{ deleted: string }>(
        `/users/${encodeURIComponent(username)}`,
        { method: "DELETE" },
      ),
    );
  }

  static async listGroups(): Promise<AppLoginGroup[]> {
    return unwrap(await request<{ groups: AppLoginGroup[] }>("/groups"))
      .groups;
  }

  static async createGroup(input: {
    name: string;
    permissions: AppPermission[];
  }): Promise<AppLoginGroup> {
    return unwrap(
      await request<AppLoginGroup>("/groups", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    );
  }

  static async updateGroup(
    groupId: string,
    input: { name?: string; permissions?: AppPermission[] },
  ): Promise<AppLoginGroup> {
    return unwrap(
      await request<AppLoginGroup>(`/groups/${encodeURIComponent(groupId)}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    );
  }

  static async deleteGroup(groupId: string): Promise<void> {
    unwrap(
      await request<{ deleted: string }>(
        `/groups/${encodeURIComponent(groupId)}`,
        { method: "DELETE" },
      ),
    );
  }
}
