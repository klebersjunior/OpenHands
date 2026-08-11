/**
 * Local app-login RBAC — keep ids aligned with scripts/app-login-rbac.mjs.
 */

import {
  ALL_PENTEST_CAPABILITIES,
  type PentestCapability,
} from "#/types/pentest-rbac";

export const APP_USERS_MANAGE = "app.users.manage" as const;

export type AppPermission = typeof APP_USERS_MANAGE | PentestCapability;

export const ALL_APP_PERMISSIONS: readonly AppPermission[] = [
  APP_USERS_MANAGE,
  ...ALL_PENTEST_CAPABILITIES,
];

export function isPentestPermission(id: string): id is PentestCapability {
  return (ALL_PENTEST_CAPABILITIES as readonly string[]).includes(id);
}

export function isAppPermission(id: string): id is AppPermission {
  return (ALL_APP_PERMISSIONS as readonly string[]).includes(id);
}

export type AppLoginGroup = {
  id: string;
  name: string;
  builtin: boolean;
  permissions: AppPermission[];
};

export type AppLoginUser = {
  username: string;
  groupId: string;
  groupName: string;
  permissions: AppPermission[];
};

export type AppLoginSession = {
  authenticated: boolean;
  username?: string;
  groupId?: string;
  groupName?: string;
  permissions?: AppPermission[];
};
