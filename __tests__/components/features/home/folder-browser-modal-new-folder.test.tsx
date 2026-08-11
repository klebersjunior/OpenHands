import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, vi, beforeEach, it } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import {
  FolderBrowserModal,
  isNotADirectoryBrowseError,
} from "#/components/features/home/workspace-dropdown/folder-browser-modal";
import { displayErrorToast } from "#/utils/custom-toast-handlers";

const { mockSearchSubdirectories, mockGetHome, mockUploadTextFile } =
  vi.hoisted(() => ({
    mockSearchSubdirectories: vi.fn(),
    mockGetHome: vi.fn(),
    mockUploadTextFile: vi.fn(),
  }));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

vi.mock("#/utils/custom-toast-handlers", () => ({
  displaySuccessToast: vi.fn(),
  displayErrorToast: vi.fn(),
}));

vi.mock("@openhands/typescript-client/clients", async () => {
  const actual = await vi.importActual<
    typeof import("@openhands/typescript-client/clients")
  >("@openhands/typescript-client/clients");
  return {
    ...actual,
    FileClient: vi.fn(function FileClientMock() {
      return {
        searchSubdirectories: mockSearchSubdirectories,
        getHome: mockGetHome,
        uploadTextFile: mockUploadTextFile,
      };
    }),
  };
});

function renderModal() {
  return render(
    <FolderBrowserModal isOpen onClose={vi.fn()} onAdd={vi.fn()} />,
    {
      wrapper: ({ children }) => (
        <QueryClientProvider
          client={
            new QueryClient({
              defaultOptions: {
                queries: { retry: false },
                mutations: { retry: false },
              },
            })
          }
        >
          {children}
        </QueryClientProvider>
      ),
    },
  );
}

describe("FolderBrowserModal new folder", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetHome.mockResolvedValue({ home: "/projects" });
    mockSearchSubdirectories.mockImplementation(async (path: string) => {
      if (path === "/projects") {
        return {
          items: [{ name: "odysseus", path: "/projects/odysseus" }],
          next_page_id: null,
        };
      }
      return { items: [], next_page_id: null };
    });
    mockUploadTextFile.mockResolvedValue({ success: true });
  });

  it("creates a folder in the current directory and navigates into it", async () => {
    const user = userEvent.setup();
    renderModal();

    await screen.findByTestId("folder-browser-entry-odysseus");
    await user.click(screen.getByTestId("folder-browser-new-folder"));

    const input = await screen.findByTestId("folder-browser-new-folder-input");
    await user.type(input, "alvo");
    await user.click(screen.getByTestId("folder-browser-new-folder-submit"));

    await waitFor(() => {
      expect(mockUploadTextFile).toHaveBeenCalledWith(
        "",
        "/projects/alvo/.gitkeep",
        ".gitkeep",
      );
    });
    await waitFor(() => {
      expect(screen.getByTestId("folder-browser-current-path")).toHaveTextContent(
        "/projects/alvo",
      );
    });
  });

  it("does not create a folder when the name already exists", async () => {
    const user = userEvent.setup();
    renderModal();

    await screen.findByTestId("folder-browser-entry-odysseus");
    await user.click(screen.getByTestId("folder-browser-new-folder"));
    await user.type(
      await screen.findByTestId("folder-browser-new-folder-input"),
      "odysseus",
    );
    await user.click(screen.getByTestId("folder-browser-new-folder-submit"));

    expect(mockUploadTextFile).not.toHaveBeenCalled();
    expect(displayErrorToast).toHaveBeenCalledWith("HOME$NEW_FOLDER_EXISTS");
  });

  it("recognizes the agent-server not-a-directory browse error", () => {
    expect(
      isNotADirectoryBrowseError(
        new Error(
          'HTTP request failed (400 Bad Request): {"detail":"Path is not a directory"}',
        ),
      ),
    ).toBe(true);
    expect(isNotADirectoryBrowseError(new Error("Directory not found"))).toBe(
      false,
    );
  });
});
