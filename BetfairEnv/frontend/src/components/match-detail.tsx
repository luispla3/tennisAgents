import { useEffect, useMemo, useState } from "react"

import { MarketOddsCharts } from "@/components/market-odds-charts"
import { MatchScoreboard } from "@/components/match-scoreboard"
import { StatsTrendChart, availableStatNames } from "@/components/stats-trend-chart"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { fetchMatchDetail, fetchSnapshot, fetchTimeline, formatDateTime } from "@/lib/api"
import { isMatchLive } from "@/lib/match-status"
import type { FullSnapshot, MatchSummary, TimelinePoint } from "@/types"

type Props = {
  match: MatchSummary
  collectorRunning?: boolean
}

export function MatchDetailPanel({ match, collectorRunning = false }: Props) {
  const eventId = String(match.event_id)
  const [timeline, setTimeline] = useState<TimelinePoint[]>([])
  const [snapIndex, setSnapIndex] = useState(0)
  const [snapshot, setSnapshot] = useState<FullSnapshot | null>(null)
  const [files, setFiles] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [statPick, setStatPick] = useState("Aces")

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      try {
        const [detail, tl] = await Promise.all([
          fetchMatchDetail(eventId),
          fetchTimeline(eventId),
        ])
        if (cancelled) return
        setTimeline(tl)
        setFiles((detail.snapshots ?? []).map((s) => s.file))
        setSnapIndex(Math.max(0, tl.length - 1))
        const stats = availableStatNames(tl)
        if (stats.length) setStatPick(stats[0])
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    if (!collectorRunning || !isMatchLive(match)) return () => { cancelled = true }
    const timer = setInterval(() => void load(), 8000)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [eventId, match, collectorRunning])

  useEffect(() => {
    const file = files[snapIndex]
    if (!file) {
      setSnapshot(null)
      return
    }
    let cancelled = false
    void fetchSnapshot(eventId, file).then((data) => {
      if (!cancelled) setSnapshot(data)
    })
    return () => {
      cancelled = true
    }
  }, [eventId, files, snapIndex])

  const current = timeline[snapIndex]
  const statNames = useMemo(() => availableStatNames(timeline), [timeline])
  const statsOverall =
    current?.stats_overall ?? snapshot?.flashscore?.statistics?.overall ?? {}
  const statsPeriods =
    current?.stats_periods ?? snapshot?.flashscore?.statistics?.periods ?? []
  const statsError =
    current?.statistics_error ??
    (snapshot?.flashscore as { statistics_error?: string } | undefined)?.statistics_error
  const hasStats = Object.keys(statsOverall).length > 0 || statsPeriods.length > 0

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (!timeline.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>
            {match.player1} vs {match.player2}
          </CardTitle>
          <CardDescription>Sin snapshots todavía para este partido.</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <MatchScoreboard match={match} point={current} snapshot={snapshot} />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Card size="sm">
          <CardHeader>
            <CardDescription>Snapshot</CardDescription>
            <CardTitle>
              {snapIndex + 1} / {timeline.length}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card size="sm">
          <CardHeader>
            <CardDescription>Hora UTC</CardDescription>
            <CardTitle className="font-mono text-base">
              {formatDateTime(current?.timestamp)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card size="sm">
          <CardHeader>
            <CardDescription>Betfair ID</CardDescription>
            <CardTitle>{eventId}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Instante en la línea temporal</CardTitle>
          <CardDescription>Selecciona un snapshot para ver cuotas y stats</CardDescription>
        </CardHeader>
        <CardContent>
          <Select
            value={String(snapIndex)}
            onValueChange={(v) => setSnapIndex(Number(v))}
          >
            <SelectTrigger className="w-full max-w-md">
              <SelectValue placeholder="Snapshot" />
            </SelectTrigger>
            <SelectContent>
              {timeline.map((point, i) => (
                <SelectItem key={point.timestamp} value={String(i)}>
                  {formatDateTime(point.timestamp)} — {point.score ?? "sin marcador"}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      <Tabs defaultValue="charts">
        <TabsList>
          <TabsTrigger value="charts">Gráficas</TabsTrigger>
          <TabsTrigger value="markets">Mercados</TabsTrigger>
          <TabsTrigger value="stats">Estadísticas</TabsTrigger>
          <TabsTrigger value="json">JSON</TabsTrigger>
        </TabsList>

        <TabsContent value="charts" className="space-y-4">
          <MarketOddsCharts timeline={timeline} player1={match.player1} player2={match.player2} />
          {statNames.length > 0 ? (
            <>
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Stat Flashscore:</span>
                <Select value={statPick} onValueChange={setStatPick}>
                  <SelectTrigger className="w-[260px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {statNames.map((name) => (
                      <SelectItem key={name} value={name}>
                        {name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <StatsTrendChart timeline={timeline} statName={statPick} />
            </>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Estadísticas Flashscore</CardTitle>
                <CardDescription>
                  {statsError
                    ? `Error al obtener stats: ${statsError}`
                    : "Sin estadísticas en los snapshots de este partido."}
                </CardDescription>
              </CardHeader>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="markets">
          <Card>
            <CardHeader>
              <CardTitle>Mercados Betfair en este instante</CardTitle>
              <CardDescription>
                {(snapshot?.betfair?.markets ?? []).length} mercados capturados
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {(snapshot?.betfair?.markets ?? []).slice(0, 20).map((market) => (
                <div key={market.market_id ?? market.name} className="rounded-lg border p-3">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <p className="font-medium">{market.group_name ?? market.name}</p>
                    {market.set_tab && <Badge variant="outline">{market.set_tab}</Badge>}
                    <Badge variant="secondary">{market.market_type}</Badge>
                  </div>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Selección</TableHead>
                        <TableHead>Cuota</TableHead>
                        <TableHead>Estado</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(market.runners ?? []).map((runner) => (
                        <TableRow key={`${runner.name}-${runner.odds_decimal}`}>
                          <TableCell>{runner.name}</TableCell>
                          <TableCell className="font-mono">
                            {runner.odds_decimal ?? "—"}
                          </TableCell>
                          <TableCell>{runner.status ?? "—"}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="stats">
          <Card>
            <CardHeader>
              <CardTitle>Estadísticas Flashscore — snapshot actual</CardTitle>
              {!hasStats && (
                <CardDescription>
                  {statsError
                    ? `Error al obtener stats: ${statsError}`
                    : "Sin estadísticas disponibles para este instante."}
                </CardDescription>
              )}
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Métrica</TableHead>
                    <TableHead>{match.player1 ?? "Home"}</TableHead>
                    <TableHead>{match.player2 ?? "Away"}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Object.entries(statsOverall).map(([name, vals]) => (
                    <TableRow key={name}>
                      <TableCell>{name}</TableCell>
                      <TableCell>{vals.home ?? vals.player1 ?? "—"}</TableCell>
                      <TableCell>{vals.away ?? vals.player2 ?? "—"}</TableCell>
                    </TableRow>
                  ))}
                  {!Object.keys(statsOverall).length && (
                    <TableRow>
                      <TableCell colSpan={3} className="text-muted-foreground">
                        Sin datos overall.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>

              <Separator className="my-4" />

              <Accordion type="multiple" className="w-full">
                {statsPeriods.map((period) => (
                  <AccordionItem key={period.name} value={period.name}>
                    <AccordionTrigger>{period.name}</AccordionTrigger>
                    <AccordionContent>
                      <Table>
                        <TableBody>
                          {(period.stats ?? []).map((s) => (
                            <TableRow key={s.name}>
                              <TableCell>{s.name}</TableCell>
                              <TableCell>{s.home}</TableCell>
                              <TableCell>{s.away}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </AccordionContent>
                  </AccordionItem>
                ))}
                {!statsPeriods.length && (
                  <p className="text-sm text-muted-foreground">Sin desglose por set/período.</p>
                )}
              </Accordion>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="json">
          <Card>
            <CardHeader>
              <CardTitle>JSON del snapshot</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="max-h-[480px] overflow-auto rounded-lg bg-muted p-4 text-xs">
                {JSON.stringify(snapshot, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
