import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useActiveBackend } from "#/contexts/active-backend-context";
import { createHostDirectory } from "#/components/features/home/workspace-dropdown/create-host-directory";

export interface CreateHostDirectoryRequest {
  parentPath: string;
  name: string;
}

export function useCreateHostDirectory() {
  const queryClient = useQueryClient();
  const active = useActiveBackend();

  return useMutation({
    mutationFn: ({ parentPath, name }: CreateHostDirectoryRequest) =>
      createHostDirectory(parentPath, name),
    onSuccess: (_destination, { parentPath }) => {
      void queryClient.invalidateQueries({
        queryKey: [
          "file",
          "search_subdirs",
          parentPath,
          active.backend.id,
          active.orgId,
        ],
      });
    },
  });
}
