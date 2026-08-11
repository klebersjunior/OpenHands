import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppLoginService } from "#/api/app-login-service";
import { APP_LOGIN_QUERY_KEYS } from "#/hooks/query/query-keys";
import type { AppPermission } from "#/types/app-login-rbac";

function invalidateAppLoginLists(
  queryClient: ReturnType<typeof useQueryClient>,
) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: APP_LOGIN_QUERY_KEYS.users }),
    queryClient.invalidateQueries({ queryKey: APP_LOGIN_QUERY_KEYS.groups }),
    queryClient.invalidateQueries({ queryKey: APP_LOGIN_QUERY_KEYS.session }),
  ]);
}

export function useAppLoginUsers(enabled: boolean) {
  return useQuery({
    queryKey: APP_LOGIN_QUERY_KEYS.users,
    queryFn: () => AppLoginService.listUsers(),
    enabled,
    meta: { disableToast: true },
  });
}

export function useAppLoginGroups(enabled: boolean) {
  return useQuery({
    queryKey: APP_LOGIN_QUERY_KEYS.groups,
    queryFn: () => AppLoginService.listGroups(),
    enabled,
    meta: { disableToast: true },
  });
}

export function useCreateAppLoginUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      username: string;
      password: string;
      groupId?: string;
    }) => AppLoginService.createUser(input),
    onSuccess: async () => {
      await invalidateAppLoginLists(queryClient);
    },
  });
}

export function useUpdateAppLoginUserGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { username: string; groupId: string }) =>
      AppLoginService.updateUserGroup(input.username, input.groupId),
    onSuccess: async () => {
      await invalidateAppLoginLists(queryClient);
    },
  });
}

export function useDeleteAppLoginUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (username: string) => AppLoginService.deleteUser(username),
    onSuccess: async () => {
      await invalidateAppLoginLists(queryClient);
    },
  });
}

export function useCreateAppLoginGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; permissions: AppPermission[] }) =>
      AppLoginService.createGroup(input),
    onSuccess: async () => {
      await invalidateAppLoginLists(queryClient);
    },
  });
}

export function useUpdateAppLoginGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      groupId: string;
      name?: string;
      permissions?: AppPermission[];
    }) =>
      AppLoginService.updateGroup(input.groupId, {
        name: input.name,
        permissions: input.permissions,
      }),
    onSuccess: async () => {
      await invalidateAppLoginLists(queryClient);
    },
  });
}

export function useDeleteAppLoginGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (groupId: string) => AppLoginService.deleteGroup(groupId),
    onSuccess: async () => {
      await invalidateAppLoginLists(queryClient);
    },
  });
}
