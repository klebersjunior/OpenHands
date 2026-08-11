import React from "react";
import { useTranslation } from "react-i18next";
import { Pencil, Trash2 } from "lucide-react";
import { I18nKey } from "#/i18n/declaration";
import { BrandButton } from "#/components/features/settings/brand-button";
import { SettingsInput } from "#/components/features/settings/settings-input";
import { ConfirmationModal } from "#/components/shared/modals/confirmation-modal";
import { Typography } from "#/ui/typography";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import {
  settingsListIconActionButtonClassName,
  settingsListScrollContainerClassName,
  settingsListTableCellClassName,
  settingsListTableHeadClassName,
  settingsListTableHeaderCellClassName,
  settingsListTableRowClassName,
} from "#/utils/settings-list-classes";
import { extensionModuleEmptyStateClassName } from "#/utils/extension-module-card-classes";
import { formControlSettingsFieldClassName } from "#/utils/form-control-classes";
import { cn } from "#/utils/utils";
import { useAppLoginSession, useAppLoginStatus } from "#/hooks/query/use-app-login";
import {
  useAppLoginGroups,
  useAppLoginUsers,
  useCreateAppLoginGroup,
  useCreateAppLoginUser,
  useDeleteAppLoginGroup,
  useDeleteAppLoginUser,
  useUpdateAppLoginGroup,
  useUpdateAppLoginUserGroup,
} from "#/hooks/query/use-app-login-users";
import { AppLoginService } from "#/api/app-login-service";
import { useNavigate } from "react-router";
import { useQueryClient } from "@tanstack/react-query";
import { APP_LOGIN_QUERY_KEYS } from "#/hooks/query/query-keys";
import { useInvalidatePentestCapabilities } from "#/hooks/use-pentest-capabilities";
import { APP_USERS_MANAGE, type AppPermission } from "#/types/app-login-rbac";
import { PermissionChips } from "#/components/features/settings/users/permission-chips";
import { GroupPermissionsEditor } from "#/components/features/settings/users/group-permissions-editor";

export const handle = { hideTitle: false };

function GroupSelect({
  value,
  groups,
  onChange,
  disabled,
  testId,
  name,
  label,
}: {
  value: string;
  groups: Array<{ id: string; name: string }>;
  onChange: (groupId: string) => void;
  disabled?: boolean;
  testId: string;
  name: string;
  label?: string;
}) {
  return (
    <label className="flex min-w-0 flex-col gap-1">
      {label ? (
        <span className="text-sm font-medium text-foreground">{label}</span>
      ) : null}
      <select
        data-testid={testId}
        name={name}
        className={formControlSettingsFieldClassName}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        aria-label={label}
      >
        {groups.map((group) => (
          <option key={group.id} value={group.id}>
            {group.name}
          </option>
        ))}
      </select>
    </label>
  );
}

export function UsersSettingsScreen() {
  const { t } = useTranslation("openhands");
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const invalidatePentestCapabilities = useInvalidatePentestCapabilities();
  const statusQuery = useAppLoginStatus();
  const enabled = statusQuery.data?.enabled === true;
  const sessionQuery = useAppLoginSession(enabled);
  const usersQuery = useAppLoginUsers(enabled);
  const groupsQuery = useAppLoginGroups(enabled);
  const createUser = useCreateAppLoginUser();
  const updateUserGroup = useUpdateAppLoginUserGroup();
  const deleteUser = useDeleteAppLoginUser();
  const createGroup = useCreateAppLoginGroup();
  const updateGroup = useUpdateAppLoginGroup();
  const deleteGroup = useDeleteAppLoginGroup();

  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [newUserGroupId, setNewUserGroupId] = React.useState("pentester");
  const [pendingDelete, setPendingDelete] = React.useState<string | null>(null);
  const [pendingGroupDelete, setPendingGroupDelete] = React.useState<{
    id: string;
    name: string;
  } | null>(null);
  const [groupName, setGroupName] = React.useState("");
  const [groupPermissions, setGroupPermissions] = React.useState<
    AppPermission[]
  >([]);
  const [editingGroupId, setEditingGroupId] = React.useState<string | null>(
    null,
  );

  const canManage = Boolean(
    sessionQuery.data?.permissions?.includes(APP_USERS_MANAGE),
  );

  React.useEffect(() => {
    if (statusQuery.isSuccess && !enabled) {
      navigate("/settings/app");
    }
  }, [enabled, navigate, statusQuery.isSuccess]);

  const groups = groupsQuery.data ?? [];
  const users = usersQuery.data ?? [];

  React.useEffect(() => {
    if (groups.some((group) => group.id === "pentester")) {
      setNewUserGroupId((current) =>
        groups.some((group) => group.id === current) ? current : "pentester",
      );
    }
  }, [groups]);

  const canCreate =
    username.trim().length > 0 &&
    password.length >= 4 &&
    Boolean(newUserGroupId) &&
    canManage &&
    !createUser.isPending;

  const toastError = (err: unknown) => {
    displayErrorToast(
      err instanceof Error ? err.message : t(I18nKey.APP_LOGIN$ERROR),
    );
  };

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canCreate) return;
    try {
      await createUser.mutateAsync({
        username: username.trim(),
        password,
        groupId: newUserGroupId,
      });
      displaySuccessToast(t(I18nKey.SETTINGS$USERS_CREATED));
      setUsername("");
      setPassword("");
    } catch (err) {
      toastError(err);
    }
  };

  const handleConfirmDelete = async () => {
    if (!pendingDelete) return;
    try {
      await deleteUser.mutateAsync(pendingDelete);
      displaySuccessToast(t(I18nKey.SETTINGS$USERS_DELETED));
    } catch (err) {
      toastError(err);
    } finally {
      setPendingDelete(null);
    }
  };

  const handleGroupSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canManage || !groupName.trim()) return;
    try {
      if (editingGroupId) {
        await updateGroup.mutateAsync({
          groupId: editingGroupId,
          name: groupName.trim(),
          permissions: groupPermissions,
        });
        displaySuccessToast(t(I18nKey.SETTINGS$USERS_GROUP_UPDATED));
      } else {
        await createGroup.mutateAsync({
          name: groupName.trim(),
          permissions: groupPermissions,
        });
        displaySuccessToast(t(I18nKey.SETTINGS$USERS_GROUP_CREATED));
      }
      setGroupName("");
      setGroupPermissions([]);
      setEditingGroupId(null);
    } catch (err) {
      toastError(err);
    }
  };

  const handleConfirmGroupDelete = async () => {
    if (!pendingGroupDelete) return;
    try {
      await deleteGroup.mutateAsync(pendingGroupDelete.id);
      displaySuccessToast(t(I18nKey.SETTINGS$USERS_GROUP_DELETED));
      if (editingGroupId === pendingGroupDelete.id) {
        setEditingGroupId(null);
        setGroupName("");
        setGroupPermissions([]);
      }
    } catch (err) {
      toastError(err);
    } finally {
      setPendingGroupDelete(null);
    }
  };

  const handleLogout = async () => {
    await AppLoginService.logout();
    invalidatePentestCapabilities();
    await queryClient.invalidateQueries({
      queryKey: APP_LOGIN_QUERY_KEYS.session,
    });
  };

  if (
    statusQuery.isPending ||
    (enabled && (usersQuery.isPending || groupsQuery.isPending))
  ) {
    return (
      <div className="flex justify-center py-10">
        <LoadingSpinner size="small" />
      </div>
    );
  }

  if (!enabled) {
    return null;
  }

  return (
    <div data-testid="users-settings-screen" className="flex flex-col gap-8">
      {!canManage && (
        <p className="text-sm text-muted">{t(I18nKey.SETTINGS$USERS_NO_PERMISSION)}</p>
      )}

      <form
        className="flex flex-col gap-4 rounded-xl border border-[var(--oh-border)] p-4"
        onSubmit={handleCreate}
      >
        <Typography.H3>{t(I18nKey.SETTINGS$USERS_ADD)}</Typography.H3>
        <div className="grid gap-4 md:grid-cols-3">
          <SettingsInput
            testId="users-settings-username"
            name="new-username"
            label={t(I18nKey.SETTINGS$USERS_USERNAME)}
            type="text"
            value={username}
            onChange={setUsername}
            required
            isDisabled={!canManage}
          />
          <SettingsInput
            testId="users-settings-password"
            name="new-password"
            label={t(I18nKey.SETTINGS$USERS_PASSWORD)}
            type="password"
            value={password}
            onChange={setPassword}
            required
            isDisabled={!canManage}
          />
          <GroupSelect
            testId="users-settings-group"
            name="new-group"
            label={t(I18nKey.SETTINGS$USERS_GROUP)}
            value={newUserGroupId}
            groups={groups}
            onChange={setNewUserGroupId}
            disabled={!canManage}
          />
        </div>
        <div className="flex justify-end">
          <BrandButton
            testId="users-settings-create"
            type="submit"
            variant="primary"
            isDisabled={!canCreate}
          >
            {t(I18nKey.SETTINGS$USERS_CREATE)}
          </BrandButton>
        </div>
      </form>

      <div className={settingsListScrollContainerClassName}>
        <table className="w-full min-w-[40rem] table-fixed">
          <thead className={settingsListTableHeadClassName}>
            <tr>
              <th
                className={cn(settingsListTableHeaderCellClassName, "w-[22%]")}
              >
                {t(I18nKey.SETTINGS$USERS_USERNAME)}
              </th>
              <th
                className={cn(settingsListTableHeaderCellClassName, "w-[22%]")}
              >
                {t(I18nKey.SETTINGS$USERS_GROUP)}
              </th>
              <th className={settingsListTableHeaderCellClassName}>
                {t(I18nKey.SETTINGS$USERS_PERMISSIONS)}
              </th>
              <th
                className={cn(
                  settingsListTableHeaderCellClassName,
                  "w-16 text-right",
                )}
              >
                {t(I18nKey.SETTINGS$ACTIONS)}
              </th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 ? (
              <tr>
                <td
                  colSpan={4}
                  data-testid="users-settings-empty"
                  className={extensionModuleEmptyStateClassName}
                >
                  {t(I18nKey.SETTINGS$USERS_EMPTY)}
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr
                  key={user.username}
                  data-testid={`users-settings-row-${user.username}`}
                  className={settingsListTableRowClassName}
                >
                  <td className={settingsListTableCellClassName}>
                    <span className="font-medium">{user.username}</span>
                  </td>
                  <td className={settingsListTableCellClassName}>
                    <GroupSelect
                      testId={`users-settings-row-group-${user.username}`}
                      name={`group-${user.username}`}
                      value={user.groupId}
                      groups={groups}
                      disabled={!canManage || updateUserGroup.isPending}
                      onChange={async (groupId) => {
                        if (groupId === user.groupId) return;
                        try {
                          await updateUserGroup.mutateAsync({
                            username: user.username,
                            groupId,
                          });
                          displaySuccessToast(t(I18nKey.SETTINGS$USERS_UPDATED));
                        } catch (err) {
                          toastError(err);
                        }
                      }}
                    />
                  </td>
                  <td
                    className={cn(
                      settingsListTableCellClassName,
                      "h-auto min-h-12 py-2",
                    )}
                  >
                    <PermissionChips permissions={user.permissions} />
                  </td>
                  <td
                    className={cn(
                      settingsListTableCellClassName,
                      "text-right",
                    )}
                  >
                    <button
                      type="button"
                      data-testid={`users-settings-delete-${user.username}`}
                      className={settingsListIconActionButtonClassName}
                      aria-label={t(I18nKey.SETTINGS$USERS_DELETE)}
                      onClick={() => setPendingDelete(user.username)}
                      disabled={
                        !canManage ||
                        users.length <= 1 ||
                        deleteUser.isPending
                      }
                    >
                      <Trash2 className="size-4" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <section className="flex flex-col gap-4">
        <div>
          <Typography.H3>{t(I18nKey.SETTINGS$USERS_GROUPS)}</Typography.H3>
          <p className="mt-1 text-sm text-muted">
            {t(I18nKey.SETTINGS$USERS_GROUPS_HELP)}
          </p>
        </div>

        <div className={settingsListScrollContainerClassName}>
          <table className="w-full min-w-[36rem] table-fixed">
            <thead className={settingsListTableHeadClassName}>
              <tr>
                <th
                  className={cn(settingsListTableHeaderCellClassName, "w-1/3")}
                >
                  {t(I18nKey.SETTINGS$USERS_GROUP_NAME)}
                </th>
                <th className={settingsListTableHeaderCellClassName}>
                  {t(I18nKey.SETTINGS$USERS_PERMISSIONS)}
                </th>
                <th
                  className={cn(
                    settingsListTableHeaderCellClassName,
                    "w-24 text-right",
                  )}
                >
                  {t(I18nKey.SETTINGS$ACTIONS)}
                </th>
              </tr>
            </thead>
            <tbody>
              {groups.map((group) => (
                <tr
                  key={group.id}
                  data-testid={`users-settings-group-row-${group.id}`}
                  className={settingsListTableRowClassName}
                >
                  <td className={settingsListTableCellClassName}>
                    <div className="flex min-w-0 flex-col">
                      <span className="font-medium">{group.name}</span>
                      {group.builtin ? (
                        <span className="text-xs text-muted">
                          {t(I18nKey.SETTINGS$USERS_GROUP_BUILTIN)}
                        </span>
                      ) : null}
                    </div>
                  </td>
                  <td
                    className={cn(
                      settingsListTableCellClassName,
                      "h-auto min-h-12 py-2",
                    )}
                  >
                    <PermissionChips permissions={group.permissions} />
                  </td>
                  <td
                    className={cn(
                      settingsListTableCellClassName,
                      "text-right",
                    )}
                  >
                    <div className="flex justify-end gap-1">
                      <button
                        type="button"
                        data-testid={`users-settings-group-edit-${group.id}`}
                        className={settingsListIconActionButtonClassName}
                        aria-label={t(I18nKey.SETTINGS$USERS_GROUP_EDIT)}
                        disabled={!canManage || group.builtin}
                        onClick={() => {
                          setEditingGroupId(group.id);
                          setGroupName(group.name);
                          setGroupPermissions(group.permissions);
                        }}
                      >
                        <Pencil className="size-4" />
                      </button>
                      <button
                        type="button"
                        data-testid={`users-settings-group-delete-${group.id}`}
                        className={settingsListIconActionButtonClassName}
                        aria-label={t(I18nKey.SETTINGS$USERS_GROUP_DELETE)}
                        disabled={!canManage || group.builtin}
                        onClick={() =>
                          setPendingGroupDelete({
                            id: group.id,
                            name: group.name,
                          })
                        }
                      >
                        <Trash2 className="size-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <form
          className="flex flex-col gap-4 rounded-xl border border-[var(--oh-border)] p-4"
          onSubmit={handleGroupSubmit}
        >
          <Typography.H3>
            {editingGroupId
              ? t(I18nKey.SETTINGS$USERS_GROUP_EDIT)
              : t(I18nKey.SETTINGS$USERS_GROUP_ADD)}
          </Typography.H3>
          <SettingsInput
            testId="users-settings-group-name"
            name="group-name"
            label={t(I18nKey.SETTINGS$USERS_GROUP_NAME)}
            type="text"
            value={groupName}
            onChange={setGroupName}
            required
            isDisabled={!canManage}
          />
          <GroupPermissionsEditor
            selected={groupPermissions}
            onChange={setGroupPermissions}
            disabled={!canManage}
          />
          <div className="flex justify-end gap-2">
            {editingGroupId ? (
              <BrandButton
                testId="users-settings-group-cancel"
                type="button"
                variant="secondary"
                onClick={() => {
                  setEditingGroupId(null);
                  setGroupName("");
                  setGroupPermissions([]);
                }}
              >
                {t(I18nKey.BUTTON$CANCEL)}
              </BrandButton>
            ) : null}
            <BrandButton
              testId="users-settings-group-save"
              type="submit"
              variant="primary"
              isDisabled={
                !canManage ||
                !groupName.trim() ||
                createGroup.isPending ||
                updateGroup.isPending
              }
            >
              {editingGroupId
                ? t(I18nKey.SETTINGS$USERS_GROUP_SAVE)
                : t(I18nKey.SETTINGS$USERS_GROUP_CREATE)}
            </BrandButton>
          </div>
        </form>
      </section>

      <div className="flex justify-end">
        <BrandButton
          testId="users-settings-logout"
          type="button"
          variant="secondary"
          onClick={handleLogout}
        >
          {t(I18nKey.SETTINGS$USERS_LOGOUT)}
        </BrandButton>
      </div>

      {pendingDelete && (
        <ConfirmationModal
          text={t(I18nKey.SETTINGS$USERS_DELETE_CONFIRM, {
            username: pendingDelete,
          })}
          onConfirm={handleConfirmDelete}
          onCancel={() => setPendingDelete(null)}
          isConfirming={deleteUser.isPending}
        />
      )}
      {pendingGroupDelete && (
        <ConfirmationModal
          text={t(I18nKey.SETTINGS$USERS_GROUP_DELETE_CONFIRM, {
            name: pendingGroupDelete.name,
          })}
          onConfirm={handleConfirmGroupDelete}
          onCancel={() => setPendingGroupDelete(null)}
          isConfirming={deleteGroup.isPending}
        />
      )}
    </div>
  );
}

export default UsersSettingsScreen;
