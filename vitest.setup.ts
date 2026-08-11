import { afterAll, afterEach, beforeAll, beforeEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

// @mswjs/interceptors bakes `SUPPORTS_PROGRESS_EVENT = typeof ProgressEvent !==
// "undefined"` at module-eval time. jsdom provides ProgressEvent, so the flag
// becomes true; later file teardown deletes the global, and late XHR callbacks
// hit `ReferenceError: ProgressEvent is not defined` (Ubuntu CI,
// home-chat-launcher). Strip it BEFORE loading MSW so createEvent permanently
// uses the built-in ProgressEventPolyfill.
Reflect.deleteProperty(globalThis, "ProgressEvent");

const { server } = await import("#/mocks/node");

// Some modules read env at import time before Vitest's per-test hooks run.
// The beforeEach below restores the same default after tests call
// `vi.unstubAllEnvs()`.
vi.stubEnv("VITE_SESSION_API_KEY", "test-session-key");

if (typeof HTMLCanvasElement !== "undefined") {
  HTMLCanvasElement.prototype.getContext = vi.fn();
}

if (typeof HTMLElement !== "undefined") {
  HTMLElement.prototype.scrollTo = vi.fn();
}

const windowStub =
  typeof window === "undefined"
    ? ({ event: undefined } as unknown as Window & typeof globalThis)
    : window;

vi.stubGlobal("window", windowStub);
windowStub.scrollTo = vi.fn();

// Node.js 25+ ships a built-in localStorage that requires --localstorage-file
// and is not functional without it. Stub it with a plain in-memory
// implementation so zustand's persist middleware works in tests.
if (
  typeof localStorage === "undefined" ||
  typeof localStorage.setItem !== "function"
) {
  const store: Record<string, string> = {};
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = String(value);
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      Object.keys(store).forEach((k) => delete store[k]);
    },
    get length() {
      return Object.keys(store).length;
    },
    key: (index: number) => Object.keys(store)[index] ?? null,
  });
}

if (typeof requestAnimationFrame === "undefined") {
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) =>
    setTimeout(() => callback(0), 0),
  );
  vi.stubGlobal(
    "cancelAnimationFrame",
    (timeoutId: ReturnType<typeof setTimeout>) => clearTimeout(timeoutId),
  );
}

// Optional global for app code that constructs ProgressEvent directly. MSW's
// createEvent path no longer depends on this (see delete above). Keep it
// outside `vi.stubGlobal()` so `vi.unstubAllGlobals()` does not remove it.
class MockProgressEvent extends Event {
  readonly lengthComputable: boolean;

  readonly loaded: number;

  readonly total: number;

  constructor(type: string, eventInitDict: ProgressEventInit = {}) {
    super(type, eventInitDict);
    this.lengthComputable = eventInitDict.lengthComputable ?? false;
    this.loaded = eventInitDict.loaded ?? 0;
    this.total = eventInitDict.total ?? 0;
  }
}

function installProgressEventPolyfill(): void {
  Object.defineProperty(globalThis, "ProgressEvent", {
    configurable: true,
    writable: true,
    enumerable: false,
    value: MockProgressEvent,
  });
}

installProgressEventPolyfill();

// Mock ResizeObserver for test environment
class MockResizeObserver {
  observe = vi.fn();

  unobserve = vi.fn();

  disconnect = vi.fn();
}

// Mock the i18n provider
vi.mock("react-i18next", async (importOriginal) => ({
  ...(await importOriginal<typeof import("react-i18next")>()),
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: {
      language: "en",
      exists: () => false,
    },
  }),
}));

vi.mock("#/hooks/use-is-on-tos-page", () => ({
  useIsOnTosPage: () => false,
}));

vi.mock("#/hooks/use-is-on-intermediate-page", () => ({
  useIsOnIntermediatePage: () => false,
}));

// Mock useRevalidator from react-router to allow direct store manipulation in tests
vi.mock("react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("react-router")>()),
  useRevalidator: () => ({
    revalidate: vi.fn(),
  }),
}));

// Import the Zustand mock to enable automatic store resets
vi.mock("zustand");

// Mock requests during tests
beforeAll(() => {
  server.listen({ onUnhandledRequest: "bypass" });
  vi.stubGlobal("ResizeObserver", MockResizeObserver);
});

beforeEach(() => {
  vi.stubEnv("VITE_SESSION_API_KEY", "test-session-key");
});

afterEach(async () => {
  server.resetHandlers();
  window.sessionStorage?.removeItem("openhands-active-backend");
  // Cleanup the document body after each test
  cleanup();
  // Drain any queued microtasks before jsdom is torn down between test files.
  // Without this, async state updates queued during render (for example by
  // HeroUI v2 components wrapped in framer-motion's LazyMotion) can resolve
  // after `window` is gone and trigger spurious unhandled rejections in
  // react-dom's `resolveUpdatePriority`. We use `Promise.resolve()` (a
  // microtask) rather than `setTimeout(0)` so this stays compatible with
  // tests that install fake timers.
  await Promise.resolve();
  await Promise.resolve();
  // Restore for app code after jsdom file teardown may have dropped it.
  installProgressEventPolyfill();
});
afterAll(() => {
  server.close();
  vi.unstubAllGlobals();
  installProgressEventPolyfill();
});
