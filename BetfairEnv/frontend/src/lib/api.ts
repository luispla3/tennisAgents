import type { CollectorStatus, FullSnapshot, MatchDetail, MatchSummary, TimelinePoint } from "@/types"

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || res.statusText)
  return data as T
}

async function postJson<T>(path: string): Promise<T> {
  return getJson<T>(path, { method: "POST" })
}

export async function fetchCollectorStatus(): Promise<CollectorStatus> {
  return getJson<CollectorStatus>("/api/collector/status")
}

export async function startCollector(): Promise<CollectorStatus> {
  return postJson<CollectorStatus>("/api/collector/start")
}

export async function stopCollector(): Promise<CollectorStatus> {
  return postJson<CollectorStatus>("/api/collector/stop")
}

export async function fetchMatches(): Promise<MatchSummary[]> {
  const data = await getJson<{ matches: MatchSummary[] }>("/api/matches")
  return data.matches ?? []
}

export async function fetchMatchDetail(eventId: string): Promise<MatchDetail> {
  return getJson<MatchDetail>(`/api/matches/${eventId}`)
}

export async function fetchTimeline(eventId: string): Promise<TimelinePoint[]> {
  const data = await getJson<{ timeline: TimelinePoint[] }>(
    `/api/matches/${eventId}/timeline`
  )
  return data.timeline ?? []
}

export async function fetchSnapshot(
  eventId: string,
  filename: string
): Promise<FullSnapshot> {
  return getJson<FullSnapshot>(`/api/matches/${eventId}/snapshots/${filename}`)
}

export function formatTime(iso?: string): string {
  if (!iso) return "—"
  return iso.replace("T", " ").slice(11, 16)
}

export function formatDateTime(iso?: string): string {
  if (!iso) return "—"
  return iso.replace("T", " ").slice(0, 19)
}
