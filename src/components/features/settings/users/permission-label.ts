import { I18nKey } from "#/i18n/declaration";
import {
  APP_USERS_MANAGE,
  type AppPermission,
} from "#/types/app-login-rbac";

const PERMISSION_I18N: Record<AppPermission, I18nKey> = {
  [APP_USERS_MANAGE]: I18nKey.SETTINGS$PERM_APP_USERS_MANAGE,
  "pentest.workspace.create": I18nKey.SETTINGS$PERM_PENTEST_WORKSPACE_CREATE,
  "pentest.engagement.create": I18nKey.SETTINGS$PERM_PENTEST_ENGAGEMENT_CREATE,
  "pentest.engagement.view": I18nKey.SETTINGS$PERM_PENTEST_ENGAGEMENT_VIEW,
  "pentest.recon.run": I18nKey.SETTINGS$PERM_PENTEST_RECON_RUN,
  "pentest.scan.passive": I18nKey.SETTINGS$PERM_PENTEST_SCAN_PASSIVE,
  "pentest.scan.active": I18nKey.SETTINGS$PERM_PENTEST_SCAN_ACTIVE,
  "pentest.sast.run": I18nKey.SETTINGS$PERM_PENTEST_SAST_RUN,
  "pentest.exploit.active": I18nKey.SETTINGS$PERM_PENTEST_EXPLOIT_ACTIVE,
  "pentest.findings.view": I18nKey.SETTINGS$PERM_PENTEST_FINDINGS_VIEW,
  "pentest.findings.triage": I18nKey.SETTINGS$PERM_PENTEST_FINDINGS_TRIAGE,
  "pentest.findings.export_dd": I18nKey.SETTINGS$PERM_PENTEST_FINDINGS_EXPORT_DD,
  "pentest.mobile.dynamic": I18nKey.SETTINGS$PERM_PENTEST_MOBILE_DYNAMIC,
  "pentest.autonomy.autonomous":
    I18nKey.SETTINGS$PERM_PENTEST_AUTONOMY_AUTONOMOUS,
  "pentest.admin.users": I18nKey.SETTINGS$PERM_PENTEST_ADMIN_USERS,
  "pentest.admin.scope": I18nKey.SETTINGS$PERM_PENTEST_ADMIN_SCOPE,
};

export function permissionI18nKey(id: string): I18nKey | null {
  return (PERMISSION_I18N as Record<string, I18nKey>)[id] ?? null;
}
