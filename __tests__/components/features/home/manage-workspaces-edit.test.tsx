import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, vi, beforeEach, it } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ManageWorkspacesModal } from "#/components/features/home/workspace-dropdown/manage-workspaces-modal";
import WorkspacesService from "#/api/workspaces-service/workspaces-service.api";

const { mockDownloadTextFile, mockUploadTextFile } = vi.hoisted(() => ({
  mockDownloadTextFile: vi.fn(),
  mockUploadTextFile: vi.fn(),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

vi.mock("#/utils/custom-toast-handlers", () => ({
  displaySuccessToast: vi.fn(),
  displayErrorToast: vi.fn(),
}));

vi.mock("#/hooks/use-pentest-capabilities", () => ({
  usePentestEngagements: () => ({ engagements: [], isLoading: false }),
  useHasPentestCapability: () => true,
}));

vi.mock("@openhands/typescript-client/clients", async () => {
  const actual = await vi.importActual<
    typeof import("@openhands/typescript-client/clients")
  >("@openhands/typescript-client/clients");
  return {
    ...actual,
    FileClient: vi.fn(function FileClientMock() {
      return {
        downloadTextFile: mockDownloadTextFile,
        uploadTextFile: mockUploadTextFile,
      };
    }),
  };
});

const workspace = {
  id: "/projects/alvo",
  name: "alvo",
  path: "/projects/alvo",
};

function renderModal() {
  return render(
    <ManageWorkspacesModal
      isOpen
      workspaces={[workspace]}
      onClose={vi.fn()}
      onRemove={vi.fn()}
    />,
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

describe("ManageWorkspacesModal edit", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockDownloadTextFile.mockRejectedValue({ status: 404 });
    mockUploadTextFile.mockResolvedValue({ success: true });
  });

  it("saves options and env vars for the selected workspace", async () => {
    const user = userEvent.setup();
    renderModal();

    await user.click(screen.getByTestId("manage-workspaces-edit-alvo"));
    await screen.findByTestId("workspace-edit-form");

    await user.clear(screen.getByTestId("workspace-edit-name"));
    await user.type(screen.getByTestId("workspace-edit-name"), "alvo-web");
    await user.type(screen.getByTestId("workspace-edit-env-key-0"), "API_URL");
    await user.type(
      screen.getByTestId("workspace-edit-env-value-0"),
      "https://example.test",
    );

    const renameSpy = vi
      .spyOn(WorkspacesService, "removeWorkspace")
      .mockResolvedValue();
    vi.spyOn(WorkspacesService, "addWorkspaces").mockResolvedValue({
      workspaces: [{ ...workspace, name: "alvo-web" }],
      workspaceParents: [],
    });

    await user.click(screen.getByTestId("workspace-edit-save"));

    await waitFor(() => {
      expect(renameSpy).toHaveBeenCalledWith("/projects/alvo");
    });
    await waitFor(() => {
      expect(mockUploadTextFile).toHaveBeenCalledWith(
        expect.stringContaining('"assets": []'),
        "/projects/alvo/.openhands/workspace.json",
        "workspace.json",
      );
      expect(mockUploadTextFile).toHaveBeenCalledWith(
        "API_URL=https://example.test\n",
        "/projects/alvo/.env",
        ".env",
      );
    });
  });
});
