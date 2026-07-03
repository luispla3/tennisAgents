export type SnapshotTimingInput = {
  last_snapshot_at?: string | null
  next_snapshot_at?: string | null
  seconds_until_next?: number | null
  progress?: number | null
  snapshot_interval_sec?: number | null
}

export type LiveSnapshotTiming = {
  seconds: number | null
  progress: number | null
}

const DEFAULT_INTERVAL_SEC = 120

function parseIsoMs(value: string): number {
  return Date.parse(value.replace("Z", "+00:00"))
}

function resolveIntervalSec(input: SnapshotTimingInput, lastMs: number, nextMs: number): number {
  if (input.snapshot_interval_sec != null && input.snapshot_interval_sec > 0) {
    return input.snapshot_interval_sec
  }
  if (nextMs > lastMs) {
    return (nextMs - lastMs) / 1000
  }
  return DEFAULT_INTERVAL_SEC
}

/** Barra de cuenta atrás: 100% recién tras snapshot, 0% al llegar a 0s. */
function progressFromRemaining(remainingSec: number, intervalSec: number): number {
  if (intervalSec <= 0) return 0
  return Math.min(100, Math.max(0, (remainingSec / intervalSec) * 100))
}

function timingFromApiFallback(input: SnapshotTimingInput): LiveSnapshotTiming {
  const intervalSec =
    input.snapshot_interval_sec != null && input.snapshot_interval_sec > 0
      ? input.snapshot_interval_sec
      : DEFAULT_INTERVAL_SEC
  const seconds =
    input.seconds_until_next != null ? Math.max(0, Math.ceil(input.seconds_until_next)) : null
  return {
    seconds,
    progress:
      seconds != null ? progressFromRemaining(seconds, intervalSec) : null,
  }
}

export function liveSnapshotTiming(
  input: SnapshotTimingInput,
  nowMs: number
): LiveSnapshotTiming {
  const { last_snapshot_at, next_snapshot_at } = input

  if (!last_snapshot_at) {
    return timingFromApiFallback(input)
  }

  const lastMs = parseIsoMs(last_snapshot_at)
  if (Number.isNaN(lastMs)) {
    return timingFromApiFallback(input)
  }

  let nextMs = next_snapshot_at ? parseIsoMs(next_snapshot_at) : Number.NaN
  const intervalSec = resolveIntervalSec(input, lastMs, nextMs)

  if (Number.isNaN(nextMs) || nextMs <= lastMs) {
    nextMs = lastMs + intervalSec * 1000
  }

  const remainingSec = Math.max(0, (nextMs - nowMs) / 1000)

  return {
    seconds: Math.ceil(remainingSec),
    progress: progressFromRemaining(remainingSec, intervalSec),
  }
}
