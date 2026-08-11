/**
 * Local app-login RBAC catalog.
 * Pentest capability ids stay aligned with src/types/pentest-rbac.ts.
 */

export const APP_USERS_MANAGE = "app.users.manage";

export const PENTEST_PERMISSIONS = [
  "pentest.workspace.create",
  "pentest.engagement.create",
  "pentest.engagement.view",
  "pentest.recon.run",
  "pentest.scan.passive",
  "pentest.scan.active",
  "pentest.sast.run",
  "pentest.exploit.active",
  "pentest.findings.view",
  "pentest.findings.triage",
  "pentest.findings.export_dd",
  "pentest.mobile.dynamic",
  "pentest.autonomy.autonomous",
  "pentest.admin.users",
  "pentest.admin.scope",
];

export const ALL_APP_PERMISSIONS = [APP_USERS_MANAGE, ...PENTEST_PERMISSIONS];

const PERMISSION_SET = new Set(ALL_APP_PERMISSIONS);

/** @type {Record<string, string[]>} */
export const BUILTIN_GROUP_PERMISSIONS = {
  admin: [...ALL_APP_PERMISSIONS],
  pentester: PENTEST_PERMISSIONS.filter(
    (id) => id !== "pentest.admin.users" && id !== "pentest.admin.scope",
  ),
  analyst: [
    "pentest.engagement.view",
    "pentest.findings.view",
    "pentest.findings.triage",
  ],
  client: ["pentest.engagement.view", "pentest.findings.view"],
};

/** @type {Record<string, string>} */
export const BUILTIN_GROUP_NAMES = {
  admin: "Administrators",
  pentester: "Pentesters",
  analyst: "Analysts",
  client: "Clients",
};

export function isKnownPermission(id) {
  return typeof id === "string" && PERMISSION_SET.has(id);
}

export function normalizePermissions(ids) {
  if (!Array.isArray(ids)) return [];
  const seen = new Set();
  /** @type {string[]} */
  const out = [];
  for (const id of ids) {
    if (!isKnownPermission(id) || seen.has(id)) continue;
    seen.add(id);
    out.push(id);
  }
  return out;
}

export function builtinGroups() {
  return Object.keys(BUILTIN_GROUP_PERMISSIONS).map((id) => ({
    id,
    name: BUILTIN_GROUP_NAMES[id],
    builtin: true,
    permissions: [...BUILTIN_GROUP_PERMISSIONS[id]],
  }));
}

/**
 * @param {string} name
 */
export function slugifyGroupId(name) {
  const slug = String(name ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40);
  return slug || `group-${Date.now().toString(36)}`;
}
