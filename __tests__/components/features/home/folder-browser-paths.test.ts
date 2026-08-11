import { describe, expect, it } from "vitest";
import {
  getParentPath,
  isValidWorkspaceFolderName,
  joinBrowsePath,
} from "#/components/features/home/workspace-dropdown/folder-browser-paths";

describe("joinBrowsePath", () => {
  it("joins posix directories", () => {
    expect(joinBrowsePath("/projects", "alvo")).toBe("/projects/alvo");
    expect(joinBrowsePath("/projects/", "alvo")).toBe("/projects/alvo");
    expect(joinBrowsePath("/", "alvo")).toBe("/alvo");
  });

  it("joins Windows directories", () => {
    expect(joinBrowsePath(String.raw`C:\Users\me`, "dev")).toBe(
      String.raw`C:\Users\me\dev`,
    );
    expect(joinBrowsePath("C:\\", "dev")).toBe(String.raw`C:\dev`);
  });
});

describe("getParentPath", () => {
  it("returns the posix parent", () => {
    expect(getParentPath("/projects/alvo")).toBe("/projects");
    expect(getParentPath("/projects")).toBe("/");
    expect(getParentPath("/")).toBeNull();
  });
});

describe("isValidWorkspaceFolderName", () => {
  it("accepts ordinary folder names", () => {
    expect(isValidWorkspaceFolderName("meu-alvo")).toBe(true);
    expect(isValidWorkspaceFolderName("  workspace_1  ")).toBe(true);
  });

  it("rejects empty, traversal, and reserved names", () => {
    expect(isValidWorkspaceFolderName("")).toBe(false);
    expect(isValidWorkspaceFolderName("   ")).toBe(false);
    expect(isValidWorkspaceFolderName(".")).toBe(false);
    expect(isValidWorkspaceFolderName("..")).toBe(false);
    expect(isValidWorkspaceFolderName("../escape")).toBe(false);
    expect(isValidWorkspaceFolderName("a/b")).toBe(false);
    expect(isValidWorkspaceFolderName(String.raw`a\b`)).toBe(false);
    expect(isValidWorkspaceFolderName("CON")).toBe(false);
    expect(isValidWorkspaceFolderName("foo:bar")).toBe(false);
  });
});
