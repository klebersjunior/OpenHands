// @vitest-environment node
import { describe, expect, it } from "vitest";
import { isMobileArtifactsProxyRequest } from "../../scripts/mobile-artifacts-proxy.mjs";

describe("isMobileArtifactsProxyRequest", () => {
  it("matches only /:id/mobile artifact paths", () => {
    expect(
      isMobileArtifactsProxyRequest(
        "/api/pentest/engagements/abc/mobile/apk",
      ),
    ).toBe(true);
    expect(
      isMobileArtifactsProxyRequest(
        "/api/pentest/engagements/abc/mobile/artifacts",
      ),
    ).toBe(true);
  });

  it("does not swallow EngMgr list or create", () => {
    expect(isMobileArtifactsProxyRequest("/api/pentest/engagements")).toBe(
      false,
    );
    expect(isMobileArtifactsProxyRequest("/api/pentest/engagements/")).toBe(
      false,
    );
    expect(
      isMobileArtifactsProxyRequest("/api/pentest/engagements/abc"),
    ).toBe(false);
    expect(
      isMobileArtifactsProxyRequest(
        "/api/pentest/engagements/abc/authorize-scope",
      ),
    ).toBe(false);
  });
});
