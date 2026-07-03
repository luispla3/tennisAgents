import { Circle } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { buildScoreboardView, playerLabel } from "@/lib/scoreboard"
import { cn } from "@/lib/utils"
import type { FullSnapshot, MatchSummary, TimelinePoint } from "@/types"

type Props = {
  match: MatchSummary
  point?: TimelinePoint
  snapshot?: FullSnapshot | null
}

function ServingBadge({ active }: { active: boolean }) {
  if (!active) return <span className="inline-block w-14" aria-hidden />
  return (
    <Badge
      variant="secondary"
      className="w-14 justify-center gap-1 border-amber-500/30 bg-amber-500/10 text-[10px] text-amber-200"
    >
      <Circle className="size-2 fill-amber-400 text-amber-400" />
      Saca
    </Badge>
  )
}

export function MatchScoreboard({ match, point, snapshot }: Props) {
  const view = buildScoreboardView(point, snapshot ?? null, match.status)
  const { sets, setsWon, currentGame, currentPoints, serving, leading, winner, status } = view
  const currentSetIndex = Math.max(0, sets.length - 1)
  const hasPointsData =
    currentPoints != null &&
    (currentPoints.player1 != null || currentPoints.player2 != null)
  const hasGameData =
    currentGame != null &&
    (currentGame.player1 != null || currentGame.player2 != null)
  const showLiveScore = sets.length > 0 || hasPointsData || hasGameData
  const pointsP1 = hasPointsData ? (currentPoints?.player1 ?? "—") : "—"
  const pointsP2 = hasPointsData ? (currentPoints?.player2 ?? "—") : "—"

  const leaderName = leading ? playerLabel(leading, match.player1, match.player2) : null
  const winnerName = winner ? playerLabel(winner, match.player1, match.player2) : null

  return (
    <Card className="overflow-hidden border-border/80 bg-gradient-to-b from-card to-muted/30 py-0 shadow-md">
      <CardContent className="space-y-5 p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="text-xs uppercase tracking-wide">
              {status ?? "—"}
            </Badge>
            {winnerName && (
              <Badge className="bg-emerald-600/90 text-xs hover:bg-emerald-600/90">
                Ganador: {winnerName}
              </Badge>
            )}
            {!winnerName && leaderName && (
              <span className="text-sm text-muted-foreground">
                Lidera: <span className="font-medium text-foreground">{leaderName}</span>
              </span>
            )}
          </div>
          <p className="text-xs text-muted-foreground">{match.competition}</p>
        </div>

        <div className="flex items-center justify-center gap-4 sm:gap-8">
          <div className="min-w-0 flex-1 text-right">
            <p
              className={cn(
                "truncate text-lg font-semibold sm:text-xl",
                leading === "player1" && "text-primary",
                winner === "player1" && "text-emerald-400",
              )}
            >
              {match.player1}
            </p>
          </div>

          <div className="flex shrink-0 items-baseline gap-2 sm:gap-3">
            <span
              className={cn(
                "font-mono text-4xl font-bold tabular-nums tracking-tight sm:text-5xl",
                leading === "player1" && "text-primary",
                winner === "player1" && "text-emerald-400",
              )}
            >
              {setsWon.player1}
            </span>
            <span className="text-2xl font-light text-muted-foreground sm:text-3xl">—</span>
            <span
              className={cn(
                "font-mono text-4xl font-bold tabular-nums tracking-tight sm:text-5xl",
                leading === "player2" && "text-primary",
                winner === "player2" && "text-emerald-400",
              )}
            >
              {setsWon.player2}
            </span>
          </div>

          <div className="min-w-0 flex-1 text-left">
            <p
              className={cn(
                "truncate text-lg font-semibold sm:text-xl",
                leading === "player2" && "text-primary",
                winner === "player2" && "text-emerald-400",
              )}
            >
              {match.player2}
            </p>
          </div>
        </div>

        {showLiveScore && (
          <div className="flex flex-col items-center gap-1.5 py-1">
            <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-muted-foreground">
              Puntos del juego
            </p>
            <div className="flex items-baseline gap-2 sm:gap-3">
              <span
                className={cn(
                  "font-mono text-3xl font-bold tabular-nums tracking-tight sm:text-4xl",
                  hasPointsData && serving === "player1" && "text-amber-300",
                  !hasPointsData && "text-muted-foreground/60",
                )}
              >
                {pointsP1}
              </span>
              <span className="text-xl font-light text-muted-foreground sm:text-2xl">—</span>
              <span
                className={cn(
                  "font-mono text-3xl font-bold tabular-nums tracking-tight sm:text-4xl",
                  hasPointsData && serving === "player2" && "text-amber-300",
                  !hasPointsData && "text-muted-foreground/60",
                )}
              >
                {pointsP2}
              </span>
            </div>
            {hasGameData && sets.length > 0 && (
              <p className="text-sm text-muted-foreground">
                Juegos en el set{" "}
                <span className="font-mono font-semibold tabular-nums text-foreground">
                  {currentGame?.player1 ?? 0} — {currentGame?.player2 ?? 0}
                </span>
              </p>
            )}
          </div>
        )}

        {sets.length > 0 && (
          <div className="overflow-x-auto rounded-lg border bg-background/60">
            <table className="w-full min-w-[280px] text-sm">
              <thead>
                <tr className="border-b text-xs text-muted-foreground">
                  <th className="px-3 py-2 text-left font-medium">Jugador</th>
                  {sets.map((_, i) => (
                    <th
                      key={`set-head-${i}`}
                      className={cn(
                        "px-3 py-2 text-center font-medium tabular-nums",
                        i === currentSetIndex && "bg-primary/10 text-primary",
                      )}
                    >
                      Set {i + 1}
                    </th>
                  ))}
                  <th className="px-3 py-2 text-center font-medium">Sets</th>
                </tr>
              </thead>
              <tbody>
                {(["player1", "player2"] as const).map((side) => {
                  const name = side === "player1" ? match.player1 : match.player2
                  const isLeading = leading === side
                  const isWinner = winner === side
                  return (
                    <tr
                      key={side}
                      className={cn(
                        "border-b last:border-0",
                        isLeading && "bg-primary/5",
                        isWinner && "bg-emerald-500/5",
                      )}
                    >
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <ServingBadge active={serving === side} />
                          <span
                            className={cn(
                              "truncate font-medium",
                              isLeading && "text-primary",
                              isWinner && "text-emerald-400",
                            )}
                          >
                            {name}
                          </span>
                        </div>
                      </td>
                      {sets.map((set, i) => (
                        <td
                          key={`${side}-set-${i}`}
                          className={cn(
                            "px-3 py-2.5 text-center font-mono text-base tabular-nums",
                            i === currentSetIndex && "bg-primary/10 font-semibold",
                          )}
                        >
                          {side === "player1" ? set.player1 : set.player2}
                        </td>
                      ))}
                      <td className="px-3 py-2.5 text-center font-mono text-lg font-bold tabular-nums">
                        {side === "player1" ? setsWon.player1 : setsWon.player2}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {!sets.length && point?.score && (
          <p className="text-center font-mono text-xl text-muted-foreground">{point.score}</p>
        )}
      </CardContent>
    </Card>
  )
}
