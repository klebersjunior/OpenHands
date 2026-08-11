import { describe, expect, it } from "vitest";
import {
  isValidEnvVarKey,
  parseDotenv,
  serializeDotenv,
} from "#/components/features/home/workspace-dropdown/workspace-dotenv";

describe("workspace dotenv", () => {
  it("parses keys, quoted values, and skips comments", () => {
    expect(
      parseDotenv(`# ignore
API_URL=https://example.test
TOKEN="abc 123"
INVALID
`),
    ).toEqual([
      { key: "API_URL", value: "https://example.test" },
      { key: "TOKEN", value: "abc 123" },
    ]);
  });

  it("serializes values that need quotes", () => {
    expect(
      serializeDotenv([
        { key: "API_URL", value: "https://example.test" },
        { key: "NOTE", value: "hello world" },
      ]),
    ).toBe('API_URL=https://example.test\nNOTE="hello world"\n');
  });

  it("rejects invalid keys", () => {
    expect(isValidEnvVarKey("API_URL")).toBe(true);
    expect(isValidEnvVarKey("1BAD")).toBe(false);
    expect(isValidEnvVarKey("HAS-DASH")).toBe(false);
  });
});
