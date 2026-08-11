import { describe, expect, it, vi } from "vitest";
import {
  createHostDirectory,
  HOST_DIRECTORY_PLACEHOLDER_FILE,
} from "#/components/features/home/workspace-dropdown/create-host-directory";

describe("createHostDirectory", () => {
  it("uploads a placeholder into the new folder so the parent is mkdir -p'd", async () => {
    const uploadTextFile = vi.fn().mockResolvedValue({ success: true });

    await expect(
      createHostDirectory("/projects", "alvo", { uploadTextFile }),
    ).resolves.toBe("/projects/alvo");

    expect(uploadTextFile).toHaveBeenCalledWith(
      "",
      "/projects/alvo/.gitkeep",
      HOST_DIRECTORY_PLACEHOLDER_FILE,
    );
  });

  it("rejects invalid names before calling the file API", async () => {
    const uploadTextFile = vi.fn();

    await expect(
      createHostDirectory("/projects", "../escape", { uploadTextFile }),
    ).rejects.toThrow("Invalid folder name");

    expect(uploadTextFile).not.toHaveBeenCalled();
  });
});
