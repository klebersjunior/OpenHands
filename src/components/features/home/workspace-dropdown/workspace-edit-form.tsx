import React from "react";
import { useTranslation } from "react-i18next";

import { BrandButton } from "#/components/features/settings/brand-button";
import { SettingsInput } from "#/components/features/settings/settings-input";
import { WorkspaceTypeSelector } from "#/components/features/pentest/workspace-type-selector";
import { PentestWorkspaceFields } from "#/components/features/pentest/pentest-workspace-fields";
import { usePentestEngagements } from "#/hooks/use-pentest-capabilities";
import { I18nKey } from "#/i18n/declaration";
import type { LocalWorkspace } from "#/types/workspace";
import type { AutonomyMode, WorkspaceType } from "#/types/workspace-types";
import type { PentestAsset } from "#/components/features/pentest/pentest-assets";
import { syncPentestWorkspaceScope } from "#/api/pentest/sync-pentest-scope";
import {
  hasUnauthorizedScope,
  isPentestCreationBlocked,
} from "#/components/features/pentest/pentest-creation-validation";
import { useWorkspaceProfile } from "#/hooks/query/use-workspace-profile";
import { useSaveWorkspaceBundle } from "#/hooks/mutation/use-save-workspace-bundle";
import { useRenameWorkspace } from "#/hooks/mutation/use-local-workspaces-mutations";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import { retrieveAxiosErrorMessage } from "#/utils/retrieve-axios-error-message";
import {
  isValidEnvVarKey,
  type WorkspaceEnvVar,
} from "./workspace-dotenv";
import { DEFAULT_WORKSPACE_PROFILE } from "./workspace-profile";

interface WorkspaceEditFormProps {
  workspace: LocalWorkspace;
  onClose: () => void;
}

export function WorkspaceEditForm({
  workspace,
  onClose,
}: WorkspaceEditFormProps) {
  const { t } = useTranslation("openhands");
  const { data: bundle, isLoading, isError } = useWorkspaceProfile(
    workspace.path,
  );
  const { mutate: saveBundle, isPending: isSavingBundle } =
    useSaveWorkspaceBundle();
  const { mutate: renameWorkspace, isPending: isRenaming } =
    useRenameWorkspace();
  const { engagements, isLoading: isLoadingEngagements } =
    usePentestEngagements();

  const [name, setName] = React.useState(workspace.name);
  const [workspaceType, setWorkspaceType] = React.useState<WorkspaceType>(
    DEFAULT_WORKSPACE_PROFILE.workspaceType,
  );
  const [engagementId, setEngagementId] = React.useState<string | null>(
    DEFAULT_WORKSPACE_PROFILE.engagementId,
  );
  const [autonomyMode, setAutonomyMode] = React.useState<AutonomyMode>(
    DEFAULT_WORKSPACE_PROFILE.autonomyMode,
  );
  const [envVars, setEnvVars] = React.useState<WorkspaceEnvVar[]>([]);
  const [assets, setAssets] = React.useState<PentestAsset[]>([]);
  const [hydratedPath, setHydratedPath] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (hydratedPath === workspace.path) return;
    if (isLoading) return;
    setName(workspace.name);
    const profile = bundle?.profile ?? DEFAULT_WORKSPACE_PROFILE;
    setWorkspaceType(profile.workspaceType);
    setEngagementId(profile.engagementId);
    setAutonomyMode(profile.autonomyMode);
    setAssets(profile.assets);
    const vars = bundle?.envVars ?? [];
    setEnvVars(vars.length > 0 ? vars : [{ key: "", value: "" }]);
    setHydratedPath(workspace.path);
  }, [bundle, hydratedPath, isError, isLoading, workspace.name, workspace.path]);

  const pentestState = { workspaceType, engagementId, autonomyMode, assets };
  const scopeUnauthorized = hasUnauthorizedScope(pentestState, engagements);
  const scopeError = scopeUnauthorized
    ? t(I18nKey.WORKSPACE_TYPE$SCOPE_NEEDS_ASSETS)
    : null;
  const pentestBlocked = isPentestCreationBlocked(pentestState, engagements);

  const handleTypeChange = (type: WorkspaceType) => {
    setWorkspaceType(type);
    setAutonomyMode("semi_autonomous");
    if (type === "code") {
      setEngagementId(null);
      setAssets([]);
    }
  };

  const updateEnv = (index: number, patch: Partial<WorkspaceEnvVar>) => {
    setEnvVars((current) =>
      current.map((entry, entryIndex) =>
        entryIndex === index ? { ...entry, ...patch } : entry,
      ),
    );
  };

  const handleSave = () => {
    const trimmedName = name.trim();
    if (!trimmedName) {
      displayErrorToast(t(I18nKey.HOME$WORKSPACE_NAME_REQUIRED));
      return;
    }
    if (workspaceType === "pentest" && pentestBlocked) {
      return;
    }

    const cleanedEnv = envVars
      .map((entry) => ({ key: entry.key.trim(), value: entry.value }))
      .filter((entry) => entry.key.length > 0);
    const invalid = cleanedEnv.find((entry) => !isValidEnvVarKey(entry.key));
    if (invalid) {
      displayErrorToast(t(I18nKey.HOME$WORKSPACE_ENV_INVALID_KEY));
      return;
    }

    const persistOptions = () => {
      saveBundle(
        {
          workspacePath: workspace.path,
          bundle: {
            profile: { workspaceType, engagementId, autonomyMode, assets },
            envVars: cleanedEnv,
          },
        },
        {
          onSuccess: () => {
            const finish = () => {
              displaySuccessToast(t(I18nKey.HOME$WORKSPACE_SAVED));
              onClose();
            };
            if (workspaceType !== "pentest") {
              finish();
              return;
            }
            void syncPentestWorkspaceScope({
              workspacePath: workspace.path,
              engagementId,
              autonomyMode,
              assets,
            })
              .then(finish)
              .catch(() => finish());
          },
          onError: (error) => {
            displayErrorToast(
              retrieveAxiosErrorMessage(error) ||
                t(I18nKey.HOME$WORKSPACE_SAVE_FAILED),
            );
          },
        },
      );
    };

    if (trimmedName !== workspace.name) {
      renameWorkspace(
        { path: workspace.path, name: trimmedName },
        {
          onSuccess: persistOptions,
          onError: (error) => {
            displayErrorToast(
              retrieveAxiosErrorMessage(error) ||
                t(I18nKey.HOME$WORKSPACE_SAVE_FAILED),
            );
          },
        },
      );
      return;
    }

    persistOptions();
  };

  const isBusy = isLoading || isSavingBundle || isRenaming;

  return (
    <div
      className="flex flex-col gap-4 px-5 py-4"
      data-testid="workspace-edit-form"
    >
      <SettingsInput
        testId="workspace-edit-name"
        label={t(I18nKey.HOME$WORKSPACE_NAME)}
        type="text"
        value={name}
        onChange={setName}
        className="w-full min-w-0"
      />
      <SettingsInput
        testId="workspace-edit-path"
        label={t(I18nKey.HOME$WORKSPACE_PATH)}
        type="text"
        value={workspace.path}
        isDisabled
        className="w-full min-w-0"
      />

      <div className="flex flex-col gap-2">
        <span className="text-xs font-semibold text-[var(--oh-muted)] uppercase tracking-wide">
          {t(I18nKey.HOME$WORKSPACE_OPTIONS)}
        </span>
        <WorkspaceTypeSelector
          value={workspaceType}
          onChange={handleTypeChange}
        />
        {workspaceType === "pentest" && (
          <PentestWorkspaceFields
            engagements={engagements}
            isLoadingEngagements={isLoadingEngagements}
            engagementId={engagementId}
            onEngagementChange={setEngagementId}
            autonomyMode={autonomyMode}
            onAutonomyChange={setAutonomyMode}
            assets={assets}
            onAssetsChange={setAssets}
            scopeError={scopeError}
          />
        )}
      </div>

      <div className="flex flex-col gap-2">
        <span className="text-xs font-semibold text-[var(--oh-muted)] uppercase tracking-wide">
          {t(I18nKey.HOME$WORKSPACE_ENV_VARS)}
        </span>
        <p className="text-xs text-[var(--oh-muted)]">
          {t(I18nKey.HOME$WORKSPACE_ENV_HINT)}
        </p>
        <ul className="flex flex-col gap-2" data-testid="workspace-edit-env-list">
          {envVars.map((entry, index) => (
            <li
              key={`env-${index}`}
              className="flex items-center gap-2"
              data-testid={`workspace-edit-env-row-${index}`}
            >
              <input
                data-testid={`workspace-edit-env-key-${index}`}
                value={entry.key}
                onChange={(event) =>
                  updateEnv(index, { key: event.target.value })
                }
                placeholder={t(I18nKey.HOME$WORKSPACE_ENV_KEY)}
                aria-label={t(I18nKey.HOME$WORKSPACE_ENV_KEY)}
                disabled={isBusy}
                className="min-w-0 flex-1 rounded-md border border-[var(--oh-border)] bg-[var(--oh-surface)] px-2 py-1.5 text-sm text-white placeholder:text-[var(--oh-muted)]"
              />
              <input
                data-testid={`workspace-edit-env-value-${index}`}
                value={entry.value}
                onChange={(event) =>
                  updateEnv(index, { value: event.target.value })
                }
                placeholder={t(I18nKey.HOME$WORKSPACE_ENV_VALUE)}
                aria-label={t(I18nKey.HOME$WORKSPACE_ENV_VALUE)}
                disabled={isBusy}
                className="min-w-0 flex-1 rounded-md border border-[var(--oh-border)] bg-[var(--oh-surface)] px-2 py-1.5 text-sm text-white placeholder:text-[var(--oh-muted)]"
              />
              <button
                type="button"
                data-testid={`workspace-edit-env-remove-${index}`}
                aria-label={t(I18nKey.HOME$WORKSPACE_ENV_REMOVE)}
                onClick={() =>
                  setEnvVars((current) =>
                    current.filter((_, entryIndex) => entryIndex !== index),
                  )
                }
                className="shrink-0 px-2 py-1 text-xs text-[var(--oh-text-tertiary)] hover:text-white"
              >
                {t(I18nKey.HOME$WORKSPACE_ENV_REMOVE)}
              </button>
            </li>
          ))}
        </ul>
        <BrandButton
          type="button"
          variant="secondary"
          testId="workspace-edit-env-add"
          onClick={() =>
            setEnvVars((current) => [...current, { key: "", value: "" }])
          }
          className="self-start px-2 py-1 text-xs"
        >
          {t(I18nKey.HOME$WORKSPACE_ENV_ADD)}
        </BrandButton>
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <BrandButton
          type="button"
          variant="secondary"
          testId="workspace-edit-cancel"
          onClick={onClose}
          isDisabled={isSavingBundle || isRenaming}
        >
          {t(I18nKey.HOME$CANCEL)}
        </BrandButton>
        <BrandButton
          type="button"
          variant="primary"
          testId="workspace-edit-save"
          onClick={handleSave}
          isDisabled={isBusy || (workspaceType === "pentest" && pentestBlocked)}
        >
          {t(I18nKey.HOME$WORKSPACE_SAVE)}
        </BrandButton>
      </div>
    </div>
  );
}
