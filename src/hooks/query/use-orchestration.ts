/**
 * TanStack Query hooks for EngMgr orchestration (PROJETOSIN-196).
 * @spec PROJETOSIN-196 — playbook start / phase polling
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import OrchestrationService from "#/api/pentest/orchestration-service";
import {
  isActiveOrchestrationStatus,
  type OrchestrationRun,
} from "#/api/pentest/orchestration-types";
import { useActiveBackend } from "#/contexts/active-backend-context";
import { ORCHESTRATION_QUERY_KEYS } from "#/hooks/query/query-keys";
import { I18nKey } from "#/i18n/declaration";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";

const POLL_INTERVAL_MS = 3000;

function pickLatestRun(items: OrchestrationRun[]): OrchestrationRun | null {
  if (items.length === 0) return null;
  return [...items].sort((a, b) => {
    const aTs = Date.parse(a.updated_at || a.created_at) || 0;
    const bTs = Date.parse(b.updated_at || b.created_at) || 0;
    return bTs - aTs;
  })[0];
}

export function useOrchestration(options: {
  engagementId: string | null;
  enabled?: boolean;
}) {
  const { engagementId, enabled = true } = options;
  const { backend, orgId } = useActiveBackend();
  const queryClient = useQueryClient();
  const { t } = useTranslation("openhands");
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  const playbooksQuery = useQuery({
    queryKey: engagementId
      ? [...ORCHESTRATION_QUERY_KEYS.playbooks(engagementId), backend.id, orgId]
      : [...ORCHESTRATION_QUERY_KEYS.all, "playbooks", "none"],
    queryFn: () => OrchestrationService.listPlaybooks(engagementId!),
    enabled: Boolean(engagementId) && enabled,
    retry: false,
    meta: { disableToast: true },
  });

  const runsQuery = useQuery({
    queryKey: engagementId
      ? [...ORCHESTRATION_QUERY_KEYS.runs(engagementId), backend.id, orgId]
      : [...ORCHESTRATION_QUERY_KEYS.all, "runs", "none"],
    queryFn: () => OrchestrationService.listRuns(engagementId!),
    enabled: Boolean(engagementId) && enabled,
    retry: false,
    meta: { disableToast: true },
  });

  const latestFromList = useMemo(
    () => pickLatestRun(runsQuery.data?.items ?? []),
    [runsQuery.data?.items],
  );

  const resolvedRunId = activeRunId ?? latestFromList?.id ?? null;

  const runQuery = useQuery({
    queryKey:
      engagementId && resolvedRunId
        ? [
            ...ORCHESTRATION_QUERY_KEYS.run(engagementId, resolvedRunId),
            backend.id,
            orgId,
          ]
        : [...ORCHESTRATION_QUERY_KEYS.all, "run", "none"],
    queryFn: () => OrchestrationService.getRun(engagementId!, resolvedRunId!),
    enabled: Boolean(engagementId) && Boolean(resolvedRunId) && enabled,
    retry: false,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && isActiveOrchestrationStatus(status)
        ? POLL_INTERVAL_MS
        : false;
    },
    meta: { disableToast: true },
  });

  const invalidateAll = useCallback(async () => {
    if (!engagementId) return;
    await queryClient.invalidateQueries({
      queryKey: ORCHESTRATION_QUERY_KEYS.runs(engagementId),
    });
    if (resolvedRunId) {
      await queryClient.invalidateQueries({
        queryKey: ORCHESTRATION_QUERY_KEYS.run(engagementId, resolvedRunId),
      });
    }
  }, [engagementId, queryClient, resolvedRunId]);

  const startMutation = useMutation({
    mutationFn: (playbookId: string) =>
      OrchestrationService.createRun(engagementId!, {
        playbook_id: playbookId,
      }),
    onSuccess: async (created) => {
      setActiveRunId(created.run_id);
      displaySuccessToast(t(I18nKey.PENTEST$ORCHESTRATION_START_SUCCESS));
      await invalidateAll();
    },
    onError: () => {
      displayErrorToast(t(I18nKey.PENTEST$ORCHESTRATION_START_ERROR));
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (runId: string) =>
      OrchestrationService.cancelRun(engagementId!, runId),
    onSuccess: async () => {
      displaySuccessToast(t(I18nKey.PENTEST$ORCHESTRATION_CANCEL_SUCCESS));
      await invalidateAll();
    },
    onError: () => {
      displayErrorToast(t(I18nKey.PENTEST$ORCHESTRATION_CANCEL_ERROR));
    },
  });

  const advanceMutation = useMutation({
    mutationFn: (runId: string) =>
      OrchestrationService.advanceRun(engagementId!, runId),
    onSuccess: async () => {
      displaySuccessToast(t(I18nKey.PENTEST$ORCHESTRATION_ADVANCE_SUCCESS));
      await invalidateAll();
    },
    onError: () => {
      displayErrorToast(t(I18nKey.PENTEST$ORCHESTRATION_ADVANCE_ERROR));
    },
  });

  const run = runQuery.data ?? latestFromList;

  return {
    playbooks: playbooksQuery.data ?? [],
    isLoadingPlaybooks: playbooksQuery.isLoading,
    isLoadingRun: runQuery.isLoading && Boolean(resolvedRunId),
    isError: playbooksQuery.isError || runsQuery.isError || runQuery.isError,
    run,
    isBusy:
      startMutation.isPending ||
      cancelMutation.isPending ||
      advanceMutation.isPending,
    isStarting: startMutation.isPending,
    isCancelling: cancelMutation.isPending,
    isAdvancing: advanceMutation.isPending,
    startRun: async (playbookId: string) => {
      if (!engagementId) return;
      await startMutation.mutateAsync(playbookId);
    },
    cancelRun: async () => {
      if (!engagementId || !run?.id) return;
      await cancelMutation.mutateAsync(run.id);
    },
    advanceRun: async () => {
      if (!engagementId || !run?.id) return;
      await advanceMutation.mutateAsync(run.id);
    },
  };
}
