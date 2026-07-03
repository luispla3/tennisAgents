import type { TimelineMarket } from "@/types"

export const MARKET_CHART_TYPES = [
  {
    id: "match_odds",
    label: "Cuotas de partido",
    description: "Match Odds — ganador del partido",
  },
  {
    id: "set_winner",
    label: "Ganador del set",
    description: "Set Winner — ganador del set en juego",
  },
  {
    id: "correct_set_score",
    label: "Marcador correcto del set",
    description: "Correct Set Score — resultado exacto del set",
  },
  {
    id: "total_games",
    label: "Total de juegos del set",
    description: "Total Games — over/under de juegos en el set",
  },
] as const

export type MarketChartTypeId = (typeof MARKET_CHART_TYPES)[number]["id"]

function setNumberFromMarket(market: TimelineMarket): number {
  const type = market.market_type ?? ""
  const name = market.name ?? ""
  const fromType = type.match(/SET_(\d+)/i)
  if (fromType) return Number(fromType[1])
  const fromName = name.match(/set\s*(\d+)/i)
  if (fromName) return Number(fromName[1])
  const fromTab = market.set_tab?.match(/set\s*(\d+)/i)
  if (fromTab) return Number(fromTab[1])
  return 0
}

function totalGamesLine(market: TimelineMarket): number {
  const type = market.market_type ?? ""
  const fromType = type.match(/OVER\/UNDER_([\d.]+)/i)
  if (fromType) return Number(fromType[1])
  const name = market.name ?? ""
  const fromName = name.match(/([\d]+[,.][\d]+)/)
  if (fromName) return Number(fromName[1].replace(",", "."))
  return 0
}

export function classifyMarketChartType(market: TimelineMarket): MarketChartTypeId | null {
  const group = (market.group_name ?? "").toLowerCase()
  const type = (market.market_type ?? "").toUpperCase()

  if (group.includes("cuotas de partido") || type === "MATCH_ODDS") {
    return "match_odds"
  }
  if (group.includes("ganador/a por sets") || /^SET_\d+_WINNER$/.test(type)) {
    return "set_winner"
  }
  if (group.includes("marcador correcto") || /^CORRECT_SCORE_\d/.test(type)) {
    return "correct_set_score"
  }
  if (group.includes("set - total de juegos") || /SET_\d+_TOTAL_GAMES/.test(type)) {
    return "total_games"
  }
  return null
}

function pickHighestSetMarket(markets: TimelineMarket[]): TimelineMarket {
  return markets.reduce((best, market) =>
    setNumberFromMarket(market) >= setNumberFromMarket(best) ? market : best,
  )
}

function pickRepresentativeTotalGames(markets: TimelineMarket[]): TimelineMarket {
  const bySet = new Map<number, TimelineMarket[]>()
  for (const market of markets) {
    const setNum = setNumberFromMarket(market)
    const bucket = bySet.get(setNum) ?? []
    bucket.push(market)
    bySet.set(setNum, bucket)
  }
  const activeSet = Math.max(...bySet.keys())
  const candidates = bySet.get(activeSet) ?? markets
  const sorted = [...candidates].sort((a, b) => totalGamesLine(a) - totalGamesLine(b))
  return sorted[Math.floor(sorted.length / 2)] ?? candidates[0]
}

export function pickMarketForChartType(
  markets: TimelineMarket[],
  chartType: MarketChartTypeId,
): TimelineMarket | undefined {
  const matches = markets.filter((market) => classifyMarketChartType(market) === chartType)
  if (!matches.length) return undefined

  switch (chartType) {
    case "match_odds":
      return matches[0]
    case "set_winner":
    case "correct_set_score":
      return pickHighestSetMarket(matches)
    case "total_games":
      return pickRepresentativeTotalGames(matches)
  }
}

export function oddsForChartType(
  markets: TimelineMarket[] | undefined,
  chartType: MarketChartTypeId,
): Record<string, number | null | undefined> {
  const market = pickMarketForChartType(markets ?? [], chartType)
  return market?.odds ?? {}
}
