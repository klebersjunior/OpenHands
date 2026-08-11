import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { UsersSettingsScreen } from "#/routes/users-settings";
import { AppLoginService } from "#/api/app-login-service";
import { ALL_PENTEST_CAPABILITIES } from "#/types/pentest-rbac";
import type { AppPermission } from "#/types/app-login-rbac";

vi.mock("#/api/app-login-service", () => ({
  AppLoginService: {
    getStatus: vi.fn(),
    getSession: vi.fn(),
    listUsers: vi.fn(),
    listGroups: vi.fn(),
    createUser: vi.fn(),
    updateUserGroup: vi.fn(),
    deleteUser: vi.fn(),
    createGroup: vi.fn(),
    updateGroup: vi.fn(),
    deleteGroup: vi.fn(),
    logout: vi.fn(),
  },
}));

vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>(
    "react-router",
  );
  return { ...actual, useNavigate: () => vi.fn() };
});

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

const adminPermissions: AppPermission[] = [
  "app.users.manage",
  ...ALL_PENTEST_CAPABILITIES,
];

function renderScreen() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <UsersSettingsScreen />
    </QueryClientProvider>,
  );
}

describe("UsersSettingsScreen", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(AppLoginService.getStatus).mockResolvedValue({ enabled: true });
    vi.mocked(AppLoginService.getSession).mockResolvedValue({
      authenticated: true,
      username: "heimdallsec",
      groupId: "admin",
      groupName: "Administrators",
      permissions: adminPermissions,
    });
    vi.mocked(AppLoginService.listGroups).mockResolvedValue([
      {
        id: "admin",
        name: "Administrators",
        builtin: true,
        permissions: adminPermissions,
      },
      {
        id: "pentester",
        name: "Pentesters",
        builtin: true,
        permissions: [...ALL_PENTEST_CAPABILITIES],
      },
    ]);
    vi.mocked(AppLoginService.listUsers).mockResolvedValue([
      {
        username: "heimdallsec",
        groupId: "admin",
        groupName: "Administrators",
        permissions: adminPermissions,
      },
      {
        username: "kleber",
        groupId: "pentester",
        groupName: "Pentesters",
        permissions: [...ALL_PENTEST_CAPABILITIES],
      },
    ]);
  });

  it("renders users in a table with group and permissions columns", async () => {
    renderScreen();

    await waitFor(() => {
      expect(screen.getByTestId("users-settings-row-heimdallsec")).toBeTruthy();
    });

    expect(
      screen.getAllByRole("columnheader", { name: "SETTINGS$USERS_USERNAME" }).length,
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByRole("columnheader", { name: "SETTINGS$USERS_GROUP" }).length,
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByRole("columnheader", { name: "SETTINGS$USERS_PERMISSIONS" })
        .length,
    ).toBeGreaterThan(1);
    expect(screen.getByText("kleber")).toBeTruthy();
    expect(screen.getByTestId("users-settings-row-group-kleber")).toBeTruthy();
    expect(screen.getByTestId("users-settings-group-row-admin")).toBeTruthy();
  });
});
