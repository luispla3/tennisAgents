import { Play, Square, Trash2 } from "lucide-react"
import { useCallback, useEffect, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  fetchCollectorStatus,
  formatDateTime,
  clearCollectorData,
  startCollector,
  stopCollector,
} from "@/lib/api"
import type { CollectorStatus } from "@/types"

type Props = {
  onChange?: () => void
  onStatusChange?: (status: CollectorStatus) => void
}

export function CollectorControls({ onChange, onStatusChange }: Props) {
  const [status, setStatus] = useState<CollectorStatus | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const data = await fetchCollectorStatus()
      setStatus(data)
      onStatusChange?.(data)
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Error de estado")
    }
  }, [onStatusChange])

  useEffect(() => {
    void refresh()
    if (!status?.running) return
    const timer = setInterval(() => void refresh(), 10000)
    return () => clearInterval(timer)
  }, [refresh, status?.running])

  const running = status?.running ?? false

  async function handleStart() {
    setBusy(true)
    setMessage(null)
    try {
      const data = await startCollector()
      setStatus(data)
      onStatusChange?.(data)
      setMessage(data.message ?? "Colector iniciado")
      onChange?.()
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "No se pudo iniciar")
    } finally {
      setBusy(false)
    }
  }

  async function handleStop() {
    setBusy(true)
    setMessage(null)
    try {
      const data = await stopCollector()
      setStatus(data)
      onStatusChange?.(data)
      setMessage(data.message ?? "Colector detenido")
      onChange?.()
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "No se pudo detener")
    } finally {
      setBusy(false)
    }
  }

  async function handleClear() {
    const ok = window.confirm(
      "¿Borrar todo el dataset recolectado?\n\nSe eliminarán partidos, snapshots e índice. El colector se detendrá si está activo."
    )
    if (!ok) return

    setBusy(true)
    setMessage(null)
    try {
      const data = await clearCollectorData()
      setStatus(data)
      onStatusChange?.(data)
      const dirs = data.removed_match_dirs ?? 0
      setMessage(data.message ?? `Dataset borrado (${dirs} partidos)`)
      onChange?.()
    } catch (e) {
      const msg = e instanceof Error ? e.message : "No se pudo borrar el dataset"
      setMessage(
        msg.includes("no válida") || msg.includes("404")
          ? "La API está desactualizada. Reinicia: python -m api.server"
          : msg
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex w-full flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={running ? "default" : "secondary"}>
          Colector {running ? "activo" : "parado"}
          {running && status?.pid ? ` · PID ${status.pid}` : ""}
        </Badge>
        {status?.cycle_state && status.cycle_state !== "ok" && (
          <Badge
            variant={
              status.cycle_state === "degraded" || status.cycle_state === "failed"
                ? "destructive"
                : "outline"
            }
            title={status.cycle_message ?? undefined}
          >
            Ciclo {status.cycle_state}
            {status.cycle_errors ? ` · ${status.cycle_errors} errores` : ""}
          </Badge>
        )}
        {status?.analysis_health?.status === "degraded" && (
          <Badge
            variant="destructive"
            title={status.analysis_health.details
              .map((item) => `${item.event_id}: ${item.error ?? item.status ?? "degradado"}`)
              .join("\n")}
          >
            Análisis degradado · {status.analysis_health.events_unhealthy}
          </Badge>
        )}
        <Button size="sm" onClick={() => void handleStart()} disabled={busy || running}>
          <Play className="mr-1 size-4" />
          Iniciar
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => void handleStop()}
          disabled={busy || !running}
        >
          <Square className="mr-1 size-4" />
          Detener
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => void handleClear()}
          disabled={busy || running}
          title={running ? "Detén el colector antes de limpiar" : "Borrar dataset recolectado"}
        >
          <Trash2 className="mr-1 size-4" />
          Limpiar
        </Button>
        {status?.last_index_update && (
          <span className="text-xs text-muted-foreground">
            Último dato: {formatDateTime(status.last_index_update)}
          </span>
        )}
        {running && status?.interval_hint && (
          <span className="text-xs text-muted-foreground">{status.interval_hint}</span>
        )}
        {message && <span className="text-xs text-muted-foreground">{message}</span>}
      </div>
    </div>
  )
}
