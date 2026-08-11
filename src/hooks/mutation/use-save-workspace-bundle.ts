import { useMutation, useQueryClient } from "@tanstack/react-query";
import { WORKSPACE_PROFILE_QUERY_KEYS } from "#/hooks/query/query-keys";
import { useActiveBackend } from "#/contexts/active-backend-context";
import {
  saveWorkspaceBundle,
  type WorkspaceBundle,
} from "#/components/features/home/workspace-dropdown/workspace-profile";

export function useSaveWorkspaceBundle() {
  const queryClient = useQueryClient();
  const active = useActiveBackend();

  return useMutation({
    mutationFn: ({
      workspacePath,
      bundle,
    }: {
      workspacePath: string;
      bundle: WorkspaceBundle;
    }) => saveWorkspaceBundle(workspacePath, bundle),
    onSuccess: (_result, { workspacePath }) => {
      void queryClient.invalidateQueries({
        queryKey: [
          ...WORKSPACE_PROFILE_QUERY_KEYS.byPath(workspacePath),
          active.backend.id,
          active.orgId,
        ],
      });
    },
  });
}
