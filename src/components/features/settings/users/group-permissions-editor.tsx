import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { ALL_APP_PERMISSIONS, type AppPermission } from "#/types/app-login-rbac";
import { permissionI18nKey } from "./permission-label";

export function GroupPermissionsEditor({
  selected,
  onChange,
  disabled = false,
}: {
  selected: readonly AppPermission[];
  onChange: (next: AppPermission[]) => void;
  disabled?: boolean;
}) {
  const { t } = useTranslation("openhands");

  const toggle = (id: AppPermission) => {
    if (disabled) return;
    if (selected.includes(id)) {
      onChange(selected.filter((item) => item !== id));
      return;
    }
    onChange([...selected, id]);
  };

  return (
    <fieldset
      disabled={disabled}
      className="grid gap-2 sm:grid-cols-2"
      data-testid="users-settings-permission-editor"
    >
      <legend className="sr-only">
        {t(I18nKey.SETTINGS$USERS_PERMISSIONS)}
      </legend>
      {ALL_APP_PERMISSIONS.map((id) => {
        const key = permissionI18nKey(id);
        const label = key ? t(key) : id;
        return (
          <label
            key={id}
            className="flex cursor-pointer items-start gap-2 text-sm"
          >
            <input
              type="checkbox"
              className="mt-0.5"
              checked={selected.includes(id)}
              onChange={() => toggle(id)}
              disabled={disabled}
            />
            <span>{label}</span>
          </label>
        );
      })}
    </fieldset>
  );
}
