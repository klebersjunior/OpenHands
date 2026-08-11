import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { permissionI18nKey } from "./permission-label";

const VISIBLE_CHIPS = 2;

export function PermissionChips({
  permissions,
}: {
  permissions: readonly string[];
}) {
  const { t } = useTranslation("openhands");
  const labels = permissions.map((id) => {
    const key = permissionI18nKey(id);
    return key ? t(key) : id;
  });
  const visible = labels.slice(0, VISIBLE_CHIPS);
  const extra = labels.length - visible.length;
  const full = labels.join(", ");

  if (labels.length === 0) {
    return <span className="text-muted">—</span>;
  }

  return (
    <div className="flex min-w-0 flex-wrap items-center gap-1.5" title={full}>
      {visible.map((label) => (
        <span
          key={label}
          className="inline-flex max-w-full truncate rounded-full border border-[var(--oh-border)] bg-[var(--oh-interactive-hover-low)] px-2 py-0.5 text-xs text-foreground"
        >
          {label}
        </span>
      ))}
      {extra > 0 && (
        <span className="text-xs text-muted">
          {t(I18nKey.SETTINGS$USERS_MORE_PERMISSIONS, { count: extra })}
        </span>
      )}
    </div>
  );
}
