import { describe, expect, it, vi } from "vitest";
import {
  loadWorkspaceBundle,
  parseWorkspaceProfile,
  saveWorkspaceBundle,
} from "#/components/features/home/workspace-dropdown/workspace-profile";

describe("parseWorkspaceProfile", () => {
  it("reads pentest options and ignores unknown fields", () => {
    expect(
      parseWorkspaceProfile(
        JSON.stringify({
          workspaceType: "pentest",
          engagementId: "eng-1",
          autonomyMode: "autonomous",
          extra: true,
        }),
      ),
    ).toEqual({
      workspaceType: "pentest",
      engagementId: "eng-1",
      autonomyMode: "autonomous",
      assets: [],
    });
  });

  it("falls back to code defaults on invalid JSON", () => {
    expect(parseWorkspaceProfile("nope")).toEqual({
      workspaceType: "code",
      engagementId: null,
      autonomyMode: "semi_autonomous",
      assets: [],
    });
  });
});

describe("workspace bundle IO", () => {
  it("treats missing files as empty defaults", async () => {
    const downloadTextFile = vi.fn().mockRejectedValue({ status: 404 });
    const bundle = await loadWorkspaceBundle("/projects/alvo", {
      downloadTextFile,
      uploadTextFile: vi.fn(),
    });
    expect(bundle).toEqual({
      profile: {
        workspaceType: "code",
        engagementId: null,
        autonomyMode: "semi_autonomous",
        assets: [],
      },
      envVars: [],
    });
  });

  it("writes profile and env into the workspace folder", async () => {
    const uploadTextFile = vi.fn().mockResolvedValue({ success: true });
    await saveWorkspaceBundle(
      "/projects/alvo",
      {
        profile: {
          workspaceType: "pentest",
          engagementId: "eng-1",
          autonomyMode: "semi_autonomous",
          assets: [{ kind: "domain", value: "alvo.example" }],
        },
        envVars: [{ key: "API_URL", value: "https://example.test" }],
      },
      { downloadTextFile: vi.fn(), uploadTextFile },
    );
    expect(uploadTextFile).toHaveBeenCalledWith(
      expect.stringContaining('"workspaceType": "pentest"'),
      "/projects/alvo/.openhands/workspace.json",
      "workspace.json",
    );
    expect(uploadTextFile).toHaveBeenCalledWith(
      "API_URL=https://example.test\n",
      "/projects/alvo/.env",
      ".env",
    );
  });
});
