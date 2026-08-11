import { Provider } from "#/types/settings";
import type { PluginSpec } from "#/api/conversation-service/agent-server-conversation-service.types";
import type { PentestAsset } from "#/components/features/pentest/pentest-assets";
import type {
  AutonomyMode,
  PentestRuntimeProfile,
  WorkspaceType,
} from "#/types/workspace-types";

const STORAGE_KEY = "openhands-agent-server-conversation-metadata";

export type WorkspaceMode = "local_repo" | "new_worktree";

export interface ConversationMetadata {
  selected_repository: string | null;
  selected_branch: string | null;
  git_provider: Provider | null;
  /**
   * The local workspace path the user explicitly attached at conversation
   * creation time. Distinct from `selected_repository` (which is set by
   * the repo picker on the home page). Used by the Files tab to decide
   * whether to default to diff view: if the user attached *anything*
   * (repo or local workspace), we lean diff-first because there's a real
   * git baseline to compare against.
   */
  selected_workspace?: string | null;
  /**
   * How the conversation should use `selected_workspace`.
   *
   * `local_repo` means the runtime should operate directly in the selected
   * folder, even when it is not a git checkout. `new_worktree` preserves the
   * historical agent-server behavior for conversations that should start in a
   * generated per-conversation worktree.
   */
  workspace_mode?: WorkspaceMode | null;
  /**
   * The LLM profile the conversation was created with (or last switched to).
   * Client-side only. Lets the chat-header switcher show the exact profile
   * name even when several profiles share the same underlying model — the
   * agent-server only round-trips the model string, so matching on it alone
   * is ambiguous (issue #1082).
   */
  active_profile?: string | null;
  /** Store plugin coordinates only; parameters may contain secrets. */
  plugins?: PluginSpec[] | null;
  /** Workspace kind chosen at creation (`code` default when omitted). */
  workspace_type?: WorkspaceType | null;
  /** Engagement Manager id — required for pentest workspaces. */
  engagement_id?: string | null;
  autonomy_mode?: AutonomyMode | null;
  runtime_profile?: PentestRuntimeProfile | null;
  /** In-scope pentest assets for this conversation (PROJETOSIN-205). */
  pentest_assets?: PentestAsset[] | null;
  /** Selected physical ADB serial (PROJETOSIN-194). */
  physical_device_serial?: string | null;
  /** Optional TCP host used with `adb connect` for LAN devices. */
  physical_adb_host?: string | null;
  physical_adb_port?: number | null;
  /**
   * Runtime ADB target override for engagement metadata.
   * `physical` → Opção B (`ADB_HOST=host.docker.internal` on Desktop).
   */
  pentest_adb_target?: "physical" | "emulator" | null;
}

export const toPluginCoordinates = (plugin: PluginSpec): PluginSpec => ({
  source: plugin.source,
  ref: plugin.ref ?? null,
  repo_path: plugin.repo_path ?? null,
});

type StoredMetadata = Record<string, ConversationMetadata>;

const readAll = (): StoredMetadata => {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return {};
    return parsed as StoredMetadata;
  } catch {
    return {};
  }
};

const metadataListeners = new Set<() => void>();

export function subscribeConversationMetadata(
  onStoreChange: () => void,
): () => void {
  metadataListeners.add(onStoreChange);
  return () => {
    metadataListeners.delete(onStoreChange);
  };
}

function emitMetadataChange(): void {
  metadataListeners.forEach((listener) => listener());
}

export function normalizeWorkspacePath(path: string): string {
  return path.replace(/\\/g, "/").replace(/\/+$/, "");
}

export function workspacePathsMatch(
  left: string | null | undefined,
  right: string | null | undefined,
): boolean {
  if (!left || !right) return false;
  return normalizeWorkspacePath(left) === normalizeWorkspacePath(right);
}

const writeAll = (next: StoredMetadata): void => {
  if (typeof window === "undefined") return;
  if (Object.keys(next).length === 0) {
    window.localStorage.removeItem(STORAGE_KEY);
  } else {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }
  emitMetadataChange();
};

export const getStoredConversationMetadata = (
  conversationId: string,
): ConversationMetadata | null => readAll()[conversationId] ?? null;

export const setStoredConversationMetadata = (
  conversationId: string,
  metadata: ConversationMetadata,
): void => {
  const all = readAll();
  all[conversationId] = metadata;
  writeAll(all);
};

export const removeStoredConversationMetadata = (
  conversationId: string,
): void => {
  const all = readAll();
  if (!(conversationId in all)) return;
  delete all[conversationId];
  writeAll(all);
};

/** Stamp every conversation attached to this folder after a workspace edit. */
export function syncWorkspaceProfileToConversations(
  workspacePath: string,
  patch: {
    workspaceType: WorkspaceType;
    engagementId: string | null;
    autonomyMode: AutonomyMode;
    assets?: PentestAsset[];
  },
): number {
  const all = readAll();
  let changed = 0;
  for (const [id, meta] of Object.entries(all)) {
    if (!workspacePathsMatch(meta.selected_workspace, workspacePath)) {
      continue;
    }
    all[id] = {
      ...meta,
      workspace_type: patch.workspaceType,
      engagement_id: patch.engagementId,
      autonomy_mode: patch.autonomyMode,
      pentest_assets: patch.assets ?? meta.pentest_assets ?? null,
    };
    changed += 1;
  }
  if (changed > 0) writeAll(all);
  return changed;
}
