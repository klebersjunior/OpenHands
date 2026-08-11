/**
 * Compact physical-device status + connect controls for the Emulator tab.
 * MVP: status / selection / reconnect banner — no scrcpy mirror (AC-194).
 *
 * @spec PROJETOSIN-194 — physical device UI (minimal)
 */

import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import PhysicalDeviceService, {
  physicalDeviceReconnectMonitor,
} from "#/api/pentest/physical-device-service";
import type {
  DeviceConnectionEvent,
  PhysicalDeviceSelection,
} from "#/api/pentest/physical-device-types";
import { PHYSICAL_DEVICE_QUERY_KEYS } from "#/hooks/query/query-keys";
import { I18nKey } from "#/i18n/declaration";
import { cn } from "#/utils/utils";

type PhysicalDeviceStatusProps = {
  conversationId: string;
};

type ConnectionUiState =
  | { kind: "idle" }
  | { kind: "connected"; serial: string }
  | { kind: "reconnecting"; serial: string; attempt: number }
  | { kind: "error"; message: string };

function parseHostPort(raw: string): { host: string; port: number } | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const idx = trimmed.lastIndexOf(":");
  if (idx <= 0) {
    return { host: trimmed, port: 5555 };
  }
  const host = trimmed.slice(0, idx).trim();
  const port = Number(trimmed.slice(idx + 1));
  if (!host || !Number.isFinite(port) || port <= 0 || port > 65535) {
    return null;
  }
  return { host, port };
}

export function PhysicalDeviceStatus({
  conversationId,
}: PhysicalDeviceStatusProps) {
  const { t } = useTranslation("openhands");
  const queryClient = useQueryClient();
  const [tcpInput, setTcpInput] = useState("");
  const [selection, setSelection] = useState<PhysicalDeviceSelection | null>(
    () => PhysicalDeviceService.readSelection(conversationId),
  );
  const [connection, setConnection] = useState<ConnectionUiState>(() => {
    const initial = PhysicalDeviceService.readSelection(conversationId);
    return initial
      ? { kind: "connected", serial: initial.serial }
      : { kind: "idle" };
  });
  const [busy, setBusy] = useState(false);

  const availabilityQuery = useQuery({
    queryKey: PHYSICAL_DEVICE_QUERY_KEYS.availability,
    queryFn: () => PhysicalDeviceService.getAvailability(),
    staleTime: 15_000,
    meta: { disableToast: true },
  });

  const devicesQuery = useQuery({
    queryKey: PHYSICAL_DEVICE_QUERY_KEYS.devices,
    queryFn: async () => {
      const result = await PhysicalDeviceService.listDevices();
      if (!result || !("ok" in result) || result.ok !== true) {
        return [];
      }
      return result.devices;
    },
    enabled: availabilityQuery.data?.status === "available",
    refetchInterval: 10_000,
    meta: { disableToast: true },
  });

  useEffect(() => {
    setSelection(PhysicalDeviceService.readSelection(conversationId));
  }, [conversationId]);

  useEffect(() => {
    const onEvent = (event: DeviceConnectionEvent) => {
      if (event.type === "connected") {
        setConnection({ kind: "connected", serial: event.serial });
      } else if (event.type === "reconnecting") {
        setConnection({
          kind: "reconnecting",
          serial: event.serial,
          attempt: event.attempt,
        });
      } else if (event.type === "disconnected") {
        setConnection({
          kind: "reconnecting",
          serial: event.serial,
          attempt: 0,
        });
      } else if (event.type === "error") {
        setConnection({ kind: "error", message: event.message });
      }
    };
    return physicalDeviceReconnectMonitor.subscribe(onEvent);
  }, []);

  useEffect(() => {
    if (!selection?.serial || availabilityQuery.data?.status !== "available") {
      physicalDeviceReconnectMonitor.stop();
      return;
    }
    physicalDeviceReconnectMonitor.start({ selection });
    return () => {
      physicalDeviceReconnectMonitor.stop();
    };
  }, [
    selection?.serial,
    selection?.tcpHost,
    selection?.tcpPort,
    availabilityQuery.data?.status,
  ]);

  const applySelection = useCallback(
    (next: PhysicalDeviceSelection | null) => {
      PhysicalDeviceService.persistSelection(conversationId, next);
      setSelection(next);
      void queryClient.invalidateQueries({
        queryKey: PHYSICAL_DEVICE_QUERY_KEYS.selection(conversationId),
      });
      void queryClient.invalidateQueries({
        queryKey: PHYSICAL_DEVICE_QUERY_KEYS.devices,
      });
      if (next) {
        setConnection({ kind: "connected", serial: next.serial });
      } else {
        setConnection({ kind: "idle" });
      }
    },
    [conversationId, queryClient],
  );

  const handleConnectTcp = useCallback(async () => {
    const parsed = parseHostPort(tcpInput);
    if (!parsed) return;
    setBusy(true);
    try {
      const result = await PhysicalDeviceService.connectTcp(
        parsed.host,
        parsed.port,
      );
      if ("ok" in result && result.ok) {
        applySelection({
          serial: result.serial,
          tcpHost: parsed.host,
          tcpPort: parsed.port,
        });
      } else if ("message" in result) {
        setConnection({ kind: "error", message: result.message });
      }
    } finally {
      setBusy(false);
    }
  }, [applySelection, tcpInput]);

  if (availabilityQuery.isLoading) {
    return null;
  }

  if (availabilityQuery.data?.status === "unavailable") {
    return (
      <div
        className="border-b border-[var(--oh-border)] px-3 py-2 text-xs text-[var(--oh-muted)]"
        data-testid="physical-device-unavailable"
      >
        {t(I18nKey.EMULATOR$PHYSICAL_UNAVAILABLE)}
      </div>
    );
  }

  const devices = devicesQuery.data ?? [];

  return (
    <div
      className="flex flex-col gap-2 border-b border-[var(--oh-border)] px-3 py-2"
      data-testid="physical-device-status"
    >
      {connection.kind === "reconnecting" && (
        <p
          className="text-xs text-[var(--oh-muted)]"
          data-testid="physical-device-reconnecting"
          role="status"
        >
          {t(I18nKey.EMULATOR$PHYSICAL_RECONNECTING, {
            serial: connection.serial,
            attempt: connection.attempt,
          })}
        </p>
      )}
      {connection.kind === "connected" && (
        <p
          className="text-xs text-[var(--foreground)]"
          data-testid="physical-device-connected"
        >
          {t(I18nKey.EMULATOR$PHYSICAL_CONNECTED, {
            serial: connection.serial,
          })}
          <span className="ml-2 text-[var(--oh-muted)]">
            {t(I18nKey.EMULATOR$PHYSICAL_MIRROR_STATUS_ONLY)}
          </span>
        </p>
      )}
      {connection.kind === "error" && (
        <p className="text-xs text-red-400" data-testid="physical-device-error">
          {connection.message}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <label className="sr-only" htmlFor="physical-device-serial">
          {t(I18nKey.EMULATOR$PHYSICAL_SELECT_SERIAL)}
        </label>
        <select
          id="physical-device-serial"
          data-testid="physical-device-serial-select"
          className="h-8 min-w-[10rem] rounded border border-[var(--oh-border)] bg-transparent px-2 text-xs text-[var(--foreground)]"
          value={selection?.serial ?? ""}
          onChange={(event) => {
            const serial = event.target.value;
            if (!serial) {
              applySelection(null);
              return;
            }
            applySelection({
              serial,
              tcpHost: selection?.tcpHost ?? null,
              tcpPort: selection?.tcpPort ?? null,
            });
          }}
        >
          <option value="">{t(I18nKey.EMULATOR$PHYSICAL_SELECT_SERIAL)}</option>
          {devices.map((device) => (
            <option key={device.serial} value={device.serial}>
              {`${device.serial} (${device.state})`}
            </option>
          ))}
        </select>

        <input
          data-testid="physical-device-tcp-input"
          value={tcpInput}
          onChange={(event) => setTcpInput(event.target.value)}
          placeholder={t(I18nKey.EMULATOR$PHYSICAL_TCP_PLACEHOLDER)}
          aria-label={t(I18nKey.EMULATOR$PHYSICAL_TCP_PLACEHOLDER)}
          className="h-8 min-w-[8rem] flex-1 rounded border border-[var(--oh-border)] bg-transparent px-2 text-xs text-[var(--foreground)]"
        />
        <button
          type="button"
          data-testid="physical-device-connect-button"
          disabled={busy || !tcpInput.trim()}
          onClick={() => void handleConnectTcp()}
          className={cn(
            "flex h-8 items-center rounded bg-white px-3 text-xs font-medium text-black",
            "cursor-pointer disabled:cursor-not-allowed disabled:opacity-50",
          )}
        >
          {t(I18nKey.EMULATOR$PHYSICAL_CONNECT)}
        </button>
      </div>
    </div>
  );
}
