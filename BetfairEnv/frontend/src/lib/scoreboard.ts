import type { FullSnapshot, GameScore, PlayerSide, PointScore, SetScore, TimelinePoint } from "@/types"

const SET_KEY_PAIRS: Array<[string, string]> = [
  ["BA", "BB"],
  ["BC", "BD"],
  ["BE", "BF"],
  ["BG", "BH"],
  ["BI", "BJ"],
]

export function parseScoreString(score?: string): SetScore[] {
  if (!score?.trim()) return []
  return score.split(/\s+/).flatMap((part) => {
    const [p1, p2] = part.split("-")
    const n1 = Number(p1)
    const n2 = Number(p2)
    if (Number.isNaN(n1) || Number.isNaN(n2)) return []
    return [{ player1: n1, player2: n2 }]
  })
}

export function setsFromScoreboardRaw(raw?: Record<string, string>): SetScore[] {
  if (!raw) return []
  const sets: SetScore[] = []
  for (const [home, away] of SET_KEY_PAIRS) {
    if (!(home in raw) && !(away in raw)) continue
    sets.push({
      player1: Number(raw[home] ?? 0),
      player2: Number(raw[away] ?? 0),
    })
  }
  return sets
}

export type ScoreboardView = {
  sets: SetScore[]
  setsWon: { player1: number; player2: number }
  currentGame?: GameScore
  currentPoints?: PointScore
  serving?: PlayerSide
  leading?: PlayerSide
  winner?: PlayerSide
  status?: string
}

const TENNIS_GAME_POINTS = new Set(["0", "15", "30", "40", "AD"])

/** Notación de tenis o tie-break; descarta totales acumulados (p. ej. 22). */
export function formatGamePoint(
  value: string | undefined | null,
  options?: { tiebreak?: boolean },
): string | undefined {
  if (value == null || value === "") return undefined
  const normalized = value.trim().toUpperCase()
  const tennis = normalized === "A" ? "AD" : normalized
  if (TENNIS_GAME_POINTS.has(tennis)) return tennis
  if (options?.tiebreak) {
    const n = Number(tennis)
    if (!Number.isNaN(n) && n >= 0 && n <= 30) return String(n)
  }
  return undefined
}

export function sanitizePointScore(
  points?: PointScore,
  currentGame?: GameScore,
): PointScore | undefined {
  if (!points) return undefined
  const tiebreak = currentGame?.player1 === 6 && currentGame?.player2 === 6
  const player1 = formatGamePoint(points.player1, { tiebreak })
  const player2 = formatGamePoint(points.player2, { tiebreak })
  if (player1 == null && player2 == null) return undefined
  return { player1, player2 }
}

function inferLeading(setsWon: { player1?: number; player2?: number }): PlayerSide | undefined {
  const p1 = setsWon.player1
  const p2 = setsWon.player2
  if (p1 == null || p2 == null || p1 === p2) return undefined
  return p1 > p2 ? "player1" : "player2"
}

function resolveSets(
  point: TimelinePoint | undefined,
  fs: FullSnapshot["flashscore"],
): SetScore[] {
  if (point?.sets_detail?.length) return point.sets_detail
  if (fs?.sets_detail?.length) return fs.sets_detail
  const fromRaw = setsFromScoreboardRaw(fs?.scoreboard_raw)
  if (fromRaw.length) return fromRaw
  return parseScoreString(point?.score ?? fs?.score)
}

function liveField<T>(fs: FullSnapshot["flashscore"], key: "current_game" | "current_points" | "serving"): T | undefined {
  if (!fs) return undefined
  const live = (fs as { live?: Record<string, unknown> }).live
  return (fs[key] as T | undefined) ?? (live?.[key] as T | undefined)
}

export function buildScoreboardView(
  point: TimelinePoint | undefined,
  snapshot: FullSnapshot | null,
  fallbackStatus?: string,
): ScoreboardView {
  const fs = snapshot?.flashscore
  const sets = resolveSets(point, fs)

  const setsWon = {
    player1: point?.sets_won?.player1 ?? fs?.sets_won?.player1 ?? 0,
    player2: point?.sets_won?.player2 ?? fs?.sets_won?.player2 ?? 0,
  }

  const leading =
    point?.leading ?? point?.winner ?? fs?.leading ?? fs?.winner ?? inferLeading(setsWon)

  const currentGame = point?.current_game ?? liveField<GameScore>(fs, "current_game")
  const rawPoints = point?.current_points ?? liveField<PointScore>(fs, "current_points")

  return {
    sets,
    setsWon: { player1: setsWon.player1 ?? 0, player2: setsWon.player2 ?? 0 },
    currentGame,
    currentPoints: sanitizePointScore(rawPoints, currentGame),
    serving: point?.serving ?? liveField<PlayerSide>(fs, "serving"),
    leading,
    winner: point?.winner ?? fs?.winner,
    status: point?.status ?? fallbackStatus,
  }
}

export function playerLabel(side: PlayerSide, player1?: string, player2?: string): string {
  return side === "player1" ? (player1 ?? "Jugador 1") : (player2 ?? "Jugador 2")
}
