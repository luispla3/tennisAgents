import { Activity, Trophy } from "lucide-react"
import { useEffect, useMemo, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { liveSnapshotTiming } from "@/lib/snapshot-timing"
import { isMatchLive } from "@/lib/match-status"
import { cn } from "@/lib/utils"
import type { MatchSummary } from "@/types"

type Props = {
  matches: MatchSummary[]
  selectedId: string | null
  collectorRunning?: boolean
  onSelect: (id: string) => void
}

function MatchSnapshotProgress({
  match,
  collectorRunning,
  nowMs,
}: {
  match: MatchSummary
  collectorRunning: boolean
  nowMs: number
}) {
  const live = isMatchLive(match)
  if (!collectorRunning || !live) return null

  const timing = liveSnapshotTiming(match, nowMs)
  const hasTiming = match.last_snapshot_at != null && timing.seconds != null

  if (!hasTiming) {
    if (match.snapshot_error) {
      return (
        <span className="text-[11px] text-destructive" title={match.snapshot_error}>
          Betfair no disponible
        </span>
      )
    }
    const label = match.queued_for_snapshot
      ? "En cola para snapshot…"
      : "Esperando primer snapshot…"
    return (
      <span className="text-[11px] text-muted-foreground">{label}</span>
    )
  }

  if (timing.seconds === 0 || match.snapshot_due) {
    return (
      <div className="mt-2 flex flex-col gap-1">
        <span className="text-[11px] text-amber-600 dark:text-amber-500">
          Snapshot pendiente…
        </span>
        <Progress value={0} className="h-1.5" />
      </div>
    )
  }

  return (
    <div className="mt-2 flex flex-col gap-1">
      <span className="text-[11px] text-muted-foreground">
        Próximo snapshot en {timing.seconds ?? 0}s
      </span>
      <Progress value={timing.progress ?? 0} className="h-1.5" />
    </div>
  )
}

export function MatchList({ matches, selectedId, collectorRunning = false, onSelect }: Props) {
  const [nowMs, setNowMs] = useState(() => Date.now())

  const hasLiveMatches = useMemo(
    () => matches.some((m) => isMatchLive(m)),
    [matches]
  )

  useEffect(() => {
    if (!collectorRunning || !hasLiveMatches) return
    const tick = setInterval(() => setNowMs(Date.now()), 250)
    return () => clearInterval(tick)
  }, [collectorRunning, hasLiveMatches])

  if (!matches.length) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-muted-foreground">
          Sin partidos registrados. Arranca el colector con <code>start.bat</code>.
        </CardContent>
      </Card>
    )
  }

  return (
    <ScrollArea className="h-[calc(100vh-8rem)] pr-3">
      <div className="flex flex-col gap-2">
        {matches.map((match) => {
          const id = String(match.event_id)
          const live = isMatchLive(match)
          return (
            <button
              key={id}
              type="button"
              onClick={() => onSelect(id)}
              className={cn(
                "rounded-xl border bg-card p-3 text-left transition-colors hover:bg-accent/40",
                selectedId === id && "border-primary bg-accent/30"
              )}
            >
              <div className="mb-1 flex items-start justify-between gap-2">
                <p className="text-sm font-medium leading-snug">
                  {match.player1 ?? "?"} <span className="text-muted-foreground">vs</span>{" "}
                  {match.player2 ?? "?"}
                </p>
                {live ? (
                  <Badge variant="destructive" className="shrink-0 gap-1">
                    <Activity className="size-3" /> Live
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="shrink-0 gap-1">
                    <Trophy className="size-3" /> Fin
                  </Badge>
                )}
              </div>
              <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                <span>{match.snapshots_count ?? 0} snaps</span>
                <span>{match.competition ?? "—"}</span>
              </div>
              <MatchSnapshotProgress
                match={match}
                collectorRunning={collectorRunning}
                nowMs={nowMs}
              />
            </button>
          )
        })}
      </div>
    </ScrollArea>
  )
}
