import { afterEach, describe, expect, it } from "vitest";
import {
  getStoredConversationMetadata,
  setStoredConversationMetadata,
  syncWorkspaceProfileToConversations,
} from "#/api/conversation-metadata-store";

const STORAGE_KEY = "openhands-agent-server-conversation-metadata";

describe("syncWorkspaceProfileToConversations", () => {
  afterEach(() => {
    localStorage.removeItem(STORAGE_KEY);
  });

  it("stamps every conversation attached to the edited workspace", () => {
    setStoredConversationMetadata("conv-old", {
      selected_repository: null,
      selected_branch: null,
      git_provider: null,
      selected_workspace: "/projects/Teste2",
      workspace_type: "code",
    });
    setStoredConversationMetadata("conv-other", {
      selected_repository: null,
      selected_branch: null,
      git_provider: null,
      selected_workspace: "/projects/outro",
      workspace_type: "code",
    });

    const changed = syncWorkspaceProfileToConversations("/projects/Teste2/", {
      workspaceType: "pentest",
      engagementId: "eng-1",
      autonomyMode: "semi_autonomous",
      assets: [{ kind: "domain", value: "alvo.example" }],
    });

    expect(changed).toBe(1);
    expect(getStoredConversationMetadata("conv-old")).toMatchObject({
      workspace_type: "pentest",
      engagement_id: "eng-1",
      selected_workspace: "/projects/Teste2",
    });
    expect(getStoredConversationMetadata("conv-other")?.workspace_type).toBe(
      "code",
    );
  });
});
