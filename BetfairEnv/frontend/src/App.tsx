import { useCallback, useEffect, useState } from "react"
import { RefreshCw } from "lucide-react"

import { MatchDetailPanel } from "@/components/match-detail"
import { MatchList } from "@/components/match-list"
import { CollectorControls } from "@/components/collector-controls"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { fetchMatches } from "@/lib/api"
import type { CollectorStatus, MatchSummary } from "@/types"

export function App() {
  const [matches, setMatches] = useState<MatchSummary[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [collectorRunning, setCollectorRunning] = useState(false)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchMatches()
      setMatches(data)
      if (!selectedId && data.length) {
        setSelectedId(String(data[0].event_id))
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido")
    } finally {
      setLoading(false)
    }
  }, [selectedId])

  useEffect(() => {
    void refresh()
    const intervalMs = collectorRunning ? 8000 : 30000
    const timer = setInterval(() => void refresh(), intervalMs)
    return () => clearInterval(timer)
  }, [refresh, collectorRunning])

  const handleCollectorStatus = useCallback((status: CollectorStatus) => {
    setCollectorRunning(status.running ?? false)
  }, [])

  const selected = matches.find((m) => String(m.event_id) === selectedId) ?? null
  const totalSnaps = matches.reduce((a, m) => a + (m.snapshots_count ?? 0), 0)

  return (
    <div className="min-h-svh bg-background">
      <header className="border-b px-4 py-4 md:px-6">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-widest text-muted-foreground">
              Betfair + Flashscore
            </p>
            <h1 className="text-2xl font-semibold tracking-tight">BetfairEnv</h1>
          </div>
          <div className="flex flex-col items-end gap-2">
            <CollectorControls
              onChange={() => void refresh()}
              onStatusChange={handleCollectorStatus}
            />
            <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">{matches.length} partidos</Badge>
            <Badge variant="secondary">{totalSnaps} snapshots</Badge>
            <Button variant="outline" size="sm" onClick={() => void refresh()} disabled={loading}>
              <RefreshCw className={`mr-1 size-4 ${loading ? "animate-spin" : ""}`} />
              Actualizar
            </Button>
            </div>
          </div>
        </div>
        {error && <p className="mx-auto mt-2 max-w-7xl text-sm text-destructive">{error}</p>}
      </header>

      <main className="mx-auto grid max-w-7xl gap-4 p-4 md:grid-cols-[320px_1fr] md:p-6">
        <aside>
          <h2 className="mb-2 text-sm font-medium text-muted-foreground">Partidos registrados</h2>
          <MatchList
            matches={matches}
            selectedId={selectedId}
            collectorRunning={collectorRunning}
            onSelect={setSelectedId}
          />
        </aside>
        <section>
          {selected ? (
            <MatchDetailPanel match={selected} />
          ) : (
            <div className="rounded-xl border border-dashed p-10 text-center text-muted-foreground">
              Selecciona un partido para ver la reconstrucción punto a punto.
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

export default App
