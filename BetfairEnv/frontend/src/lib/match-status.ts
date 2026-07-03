import type { MatchSummary } from "@/types"

const FINISHED_STATUS = /final|terminad|finished|walkover|retirad|abandon/

export function isMatchLive(
  match: Pick<MatchSummary, "is_live" | "status" | "finished_at" | "is_finished">
): boolean {
  if (match.finished_at || match.is_finished) return false
  const status = (match.status ?? "").toLowerCase()
  if (FINISHED_STATUS.test(status)) return false
  if (match.is_live === false) return false
  return match.is_live === true || status.includes("juego")
}
