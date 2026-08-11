import { useQuery } from "@tanstack/react-query";
import { WORKSPACE_PROFILE_QUERY_KEYS } from "#/hooks/query/query-keys";
import { useActiveBackend } from "#/contexts/active-backend-context";
import { loadWorkspaceBundle } from "#/components/features/home/workspace-dropdown/workspace-profile";

export function useWorkspaceProfile(workspacePath: string | null) {
  const active = useActiveBackend();
  return useQuery({
    queryKey: [
      ...WORKSPACE_PROFILE_QUERY_KEYS.byPath(workspacePath ?? ""),
      active.backend.id,
      active.orgId,
    ],
    queryFn: () => loadWorkspaceBundle(workspacePath as string),
    enabled: Boolean(workspacePath),
    retry: false,
    meta: { disableToast: true },
  });
}
