import { FileClient } from "@openhands/typescript-client/clients";
import { getAgentServerClientOptions } from "#/api/agent-server-client-options";
import { syncWorkspaceProfileToConversations } from "#/api/conversation-metadata-store";
import type { AutonomyMode, WorkspaceType } from "#/types/workspace-types";
import {
  parsePentestAssets,
  type PentestAsset,
} from "#/components/features/pentest/pentest-assets";
import { joinBrowsePath } from "./folder-browser-paths";
import {
  parseDotenv,
  serializeDotenv,
  type WorkspaceEnvVar,
} from "./workspace-dotenv";

function readHttpStatus(error: unknown): number | null {
  if (!error || typeof error !== "object") return null;
  const record = error as {
    status?: unknown;
    response?: { status?: unknown };
  };
  if (typeof record.status === "number") return record.status;
  if (typeof record.response?.status === "number") return record.response.status;
  return null;
}

export const WORKSPACE_PROFILE_DIR = ".openhands";
export const WORKSPACE_PROFILE_FILE = "workspace.json";
export const WORKSPACE_ENV_FILE = ".env";

export interface WorkspaceProfile {
  workspaceType: WorkspaceType;
  engagementId: string | null;
  autonomyMode: AutonomyMode;
  assets: PentestAsset[];
}

export interface WorkspaceBundle {
  profile: WorkspaceProfile;
  envVars: WorkspaceEnvVar[];
}

export const DEFAULT_WORKSPACE_PROFILE: WorkspaceProfile = {
  workspaceType: "code",
  engagementId: null,
  autonomyMode: "semi_autonomous",
  assets: [],
};

type FileIOClient = Pick<FileClient, "downloadTextFile" | "uploadTextFile">;

function fileClient(): FileIOClient {
  return new FileClient(getAgentServerClientOptions());
}

function isMissingFile(error: unknown): boolean {
  return readHttpStatus(error) === 404;
}

export function parseWorkspaceProfile(raw: string): WorkspaceProfile {
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const workspaceType =
      parsed.workspaceType === "pentest" ? "pentest" : "code";
    const autonomyMode =
      parsed.autonomyMode === "manual" ||
      parsed.autonomyMode === "autonomous" ||
      parsed.autonomyMode === "semi_autonomous"
        ? parsed.autonomyMode
        : DEFAULT_WORKSPACE_PROFILE.autonomyMode;
    const engagementId =
      typeof parsed.engagementId === "string" && parsed.engagementId.trim()
        ? parsed.engagementId.trim()
        : null;
    return {
      workspaceType,
      engagementId,
      autonomyMode,
      assets: parsePentestAssets(parsed.assets),
    };
  } catch {
    return { ...DEFAULT_WORKSPACE_PROFILE };
  }
}

export async function loadWorkspaceBundle(
  workspacePath: string,
  client: FileIOClient = fileClient(),
): Promise<WorkspaceBundle> {
  const profilePath = joinBrowsePath(
    joinBrowsePath(workspacePath, WORKSPACE_PROFILE_DIR),
    WORKSPACE_PROFILE_FILE,
  );
  const envPath = joinBrowsePath(workspacePath, WORKSPACE_ENV_FILE);

  const [profileResult, envResult] = await Promise.all([
    client.downloadTextFile(profilePath).catch((error: unknown) => {
      if (isMissingFile(error)) return "";
      throw error;
    }),
    client.downloadTextFile(envPath).catch((error: unknown) => {
      if (isMissingFile(error)) return "";
      throw error;
    }),
  ]);

  return {
    profile: profileResult
      ? parseWorkspaceProfile(profileResult)
      : { ...DEFAULT_WORKSPACE_PROFILE },
    envVars: parseDotenv(envResult),
  };
}

export async function saveWorkspaceBundle(
  workspacePath: string,
  bundle: WorkspaceBundle,
  client: FileIOClient = fileClient(),
): Promise<void> {
  const profilePath = joinBrowsePath(
    joinBrowsePath(workspacePath, WORKSPACE_PROFILE_DIR),
    WORKSPACE_PROFILE_FILE,
  );
  const envPath = joinBrowsePath(workspacePath, WORKSPACE_ENV_FILE);
  await Promise.all([
    client.uploadTextFile(
      `${JSON.stringify(bundle.profile, null, 2)}\n`,
      profilePath,
      WORKSPACE_PROFILE_FILE,
    ),
    client.uploadTextFile(
      serializeDotenv(bundle.envVars),
      envPath,
      WORKSPACE_ENV_FILE,
    ),
  ]);
  syncWorkspaceProfileToConversations(workspacePath, {
    workspaceType: bundle.profile.workspaceType,
    engagementId: bundle.profile.engagementId,
    autonomyMode: bundle.profile.autonomyMode,
    assets: bundle.profile.assets,
  });
}
