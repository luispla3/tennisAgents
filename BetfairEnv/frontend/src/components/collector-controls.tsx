import { Play, Square } from "lucide-react"
import { useCallback, useEffect, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  fetchCollectorStatus,
  formatDateTime,
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
    const timer = setInterval(() => void refresh(), 10000)
    return () => clearInterval(timer)
  }, [refresh])

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

  return (
    <div className="flex w-full flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={running ? "default" : "secondary"}>
          Colector {running ? "activo" : "parado"}
          {running && status?.pid ? ` · PID ${status.pid}` : ""}
        </Badge>
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
