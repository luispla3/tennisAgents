import { OddsChart } from "@/components/odds-chart"
import { MARKET_CHART_TYPES } from "@/lib/market-chart-types"
import type { TimelinePoint } from "@/types"

type Props = {
  timeline: TimelinePoint[]
  player1?: string
  player2?: string
}

export function MarketOddsCharts({ timeline, player1, player2 }: Props) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {MARKET_CHART_TYPES.map((chartType) => (
        <OddsChart
          key={chartType.id}
          timeline={timeline}
          chartType={chartType.id}
          player1={player1}
          player2={player2}
          title={chartType.label}
          description={chartType.description}
        />
      ))}
    </div>
  )
}
