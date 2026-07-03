import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts"

import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import type { TimelinePoint } from "@/types"
import { formatTime } from "@/lib/api"

const STAT_KEYS = ["Aces", "Dobles faltas", "Puntos ganados", "Break points convertidos"]

type Props = {
  timeline: TimelinePoint[]
  statName?: string
}

function parseNum(value?: string): number | null {
  if (!value) return null
  const n = Number(value.replace("%", "").replace(",", "."))
  return Number.isFinite(n) ? n : null
}

function statSide(
  stat: { home?: string; away?: string; player1?: string; player2?: string } | undefined,
  side: "home" | "away",
): number | null {
  if (!stat) return null
  const raw = side === "home" ? stat.home ?? stat.player1 : stat.away ?? stat.player2
  return parseNum(raw)
}

export function StatsTrendChart({ timeline, statName = "Aces" }: Props) {
  const chartConfig = {
    home: { label: "Jugador 1 / Home", color: "var(--chart-3)" },
    away: { label: "Jugador 2 / Away", color: "var(--chart-4)" },
  } satisfies ChartConfig

  const data = timeline.map((point) => {
    const stat = point.stats_overall?.[statName]
    return {
      time: formatTime(point.timestamp),
      home: statSide(stat, "home"),
      away: statSide(stat, "away"),
    }
  })

  const hasData = data.some((d) => d.home != null || d.away != null)
  if (!hasData) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Tendencia — {statName}</CardTitle>
          <CardDescription>Sin valores numéricos para esta métrica</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Tendencia — {statName}</CardTitle>
        <CardDescription>Flashscore por snapshot</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig} className="aspect-[2/1] w-full min-h-[220px]">
          <LineChart data={data} margin={{ left: 8, right: 8, top: 8, bottom: 0 }}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="time" tickLine={false} axisLine={false} tickMargin={8} />
            <YAxis tickLine={false} axisLine={false} width={36} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <ChartLegend content={<ChartLegendContent />} />
            <Line type="monotone" dataKey="home" stroke="var(--color-home)" strokeWidth={2} dot={{ r: 2 }} connectNulls />
            <Line type="monotone" dataKey="away" stroke="var(--color-away)" strokeWidth={2} dot={{ r: 2 }} connectNulls />
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

export function availableStatNames(timeline: TimelinePoint[]): string[] {
  const names = new Set<string>()
  for (const point of timeline) {
    Object.keys(point.stats_overall ?? {}).forEach((k) => names.add(k))
  }
  const preferred = STAT_KEYS.filter((k) => names.has(k))
  const rest = Array.from(names).filter((k) => !preferred.includes(k))
  return [...preferred, ...rest].slice(0, 8)
}
