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
import { oddsForChartType, type MarketChartTypeId } from "@/lib/market-chart-types"
import type { TimelinePoint } from "@/types"
import { formatTime } from "@/lib/api"

const CHART_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
]

type Props = {
  timeline: TimelinePoint[]
  player1?: string
  player2?: string
  chartType?: MarketChartTypeId
  title?: string
  description?: string
}

function slug(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "_")
}

function oddsForPoint(
  point: TimelinePoint,
  chartType?: MarketChartTypeId,
): Record<string, number | null | undefined> {
  if (chartType) {
    return oddsForChartType(point.markets, chartType)
  }
  return point.odds ?? {}
}

export function OddsChart({
  timeline,
  player1,
  player2,
  chartType,
  title = "Evolución de cuotas",
  description,
}: Props) {
  const names = new Set<string>()
  for (const point of timeline) {
    Object.keys(oddsForPoint(point, chartType)).forEach((n) => names.add(n))
  }

  const series = Array.from(names).slice(0, 6)
  if (!series.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>Sin datos de cuotas en los snapshots</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  const chartConfig = series.reduce((acc, name, i) => {
    acc[slug(name)] = {
      label: name,
      color: CHART_COLORS[i % CHART_COLORS.length],
    }
    return acc
  }, {} as ChartConfig)

  const data = timeline.map((point) => {
    const odds = oddsForPoint(point, chartType)
    const row: Record<string, string | number | null> = {
      time: formatTime(point.timestamp),
    }
    for (const name of series) {
      row[slug(name)] = odds[name] ?? null
    }
    return row
  })

  const subtitle =
    description ??
    `${player1 ?? "J1"} vs ${player2 ?? "J2"}${chartType ? "" : " — mercado principal"}`

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{subtitle}</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig} className="aspect-[2/1] w-full min-h-[260px]">
          <LineChart data={data} margin={{ left: 8, right: 8, top: 8, bottom: 0 }}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="time" tickLine={false} axisLine={false} tickMargin={8} />
            <YAxis tickLine={false} axisLine={false} width={40} domain={["auto", "auto"]} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <ChartLegend content={<ChartLegendContent />} />
            {series.map((name) => (
              <Line
                key={name}
                type="monotone"
                dataKey={slug(name)}
                stroke={`var(--color-${slug(name)})`}
                strokeWidth={2}
                dot={{ r: 3 }}
                connectNulls
              />
            ))}
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
