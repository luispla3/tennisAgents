export type CollectorStatus = {
  running: boolean
  pid?: number | null
  interval_hint?: string
  last_index_update?: string | null
  last_cycle_at?: string | null
  heartbeat_at?: string | null
  cycle_started_at?: string | null
  cycle_state?: "running" | "ok" | "degraded" | "failed" | null
  cycle_duration_sec?: number | null
  cycle_snapshots?: number | null
  cycle_errors?: number | null
  cycle_message?: string | null
  next_cycle_at?: string | null
  seconds_until_next?: number | null
  progress?: number | null
  interval_sec?: number | null
  interval_sec_min?: number
  interval_sec_max?: number
  message?: string
  already_running?: boolean
  was_running?: boolean
  removed_match_dirs?: number
  removed_files?: number
  collector_was_running?: boolean
  graceful?: boolean
  analysis_health?: {
    status: "ok" | "degraded"
    events_total: number
    events_unhealthy: number
    historical_events_unhealthy: number
    events_with_backlog: number
    details: Array<{
      event_id: string
      status?: string | null
      error?: string | null
      missing_reports?: string[]
      has_backlog?: boolean
      snapshot_retention_blocked?: Record<string, unknown>
    }>
  }
}

export type MatchSummary = {
  event_id: string
  betfair_event_id?: number
  flashscore_match_id?: string
  player1?: string
  player2?: string
  competition?: string
  status?: string
  is_live?: boolean
  is_finished?: boolean
  is_stale?: boolean
  winner?: "player1" | "player2"
  snapshots_count?: number
  first_seen?: string
  last_seen?: string
  finished_at?: string | null
  stale_at?: string | null
  last_snapshot_at?: string | null
  next_snapshot_at?: string | null
  seconds_until_next?: number | null
  progress?: number | null
  snapshot_interval_sec?: number | null
  awaiting_first_snapshot?: boolean
  queued_for_snapshot?: boolean
  snapshot_due?: boolean
  snapshot_error?: string
  analysis_status?: string
  analysts_completed?: boolean
  last_analysis_step?: number
  last_analysis_at?: string
  last_processed_snapshot_at?: string
  analysis_current_snapshot_at?: string
  analysis_error?: string
  analysis_degraded_reason?: string
  available_balance?: number
  open_positions_count?: number
  realized_pnl?: number
  settlement_status?: string
  betfair_url?: string
  flashscore_url?: string
}

export type SnapshotMeta = {
  file: string
  timestamp?: string
  score?: string
  status?: string
}

export type TimelineMarket = {
  market_id?: string
  name?: string
  market_type?: string
  group_name?: string
  set_tab?: string
  odds: Record<string, number | null | undefined>
}

export type SetScore = {
  player1: number
  player2: number
}

export type PlayerSide = "player1" | "player2"

export type GameScore = {
  player1?: number
  player2?: number
}

export type PointScore = {
  player1?: string
  player2?: string
}

export type TimelinePoint = {
  timestamp: string
  score?: string
  sets_won?: { player1?: number; player2?: number }
  sets_detail?: SetScore[]
  current_game?: GameScore
  current_points?: PointScore
  serving?: PlayerSide
  leading?: PlayerSide
  winner?: PlayerSide
  status?: string
  odds: Record<string, number | null | undefined>
  markets?: TimelineMarket[]
  stats_overall?: Record<string, { home?: string; away?: string; player1?: string; player2?: string }>
  stats_periods?: Array<{
    name: string
    stats: Array<{ name: string; home: string; away: string }>
  }>
  statistics_error?: string
}

export type MatchDetail = {
  event_id: string
  meta: Record<string, unknown>
  snapshots: SnapshotMeta[]
}

export type FullSnapshot = {
  timestamp: string
  betfair_event_id: number
  flashscore_match_id?: string
  betfair?: {
    status?: string
    is_live?: boolean
    player1?: string
    player2?: string
    primary_market?: {
      runners?: Array<{ name?: string; odds_decimal?: number | null }>
    }
    markets?: Array<{
      market_id?: string
      name?: string
      group_name?: string
      set_tab?: string
      market_type?: string
      runners?: Array<{ name?: string; odds_decimal?: number | null; status?: string }>
    }>
  }
  flashscore?: {
    score?: string
    sets_won?: { player1?: number; player2?: number }
    sets_detail?: SetScore[]
    current_game?: GameScore
    current_points?: PointScore
    serving?: PlayerSide
    leading?: PlayerSide
    winner?: PlayerSide
    scoreboard_raw?: Record<string, string>
    statistics?: {
      overall?: Record<string, { home?: string; away?: string; player1?: string; player2?: string }>
      periods?: TimelinePoint["stats_periods"]
    }
  }
}
