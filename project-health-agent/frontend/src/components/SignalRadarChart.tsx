import React from "react"
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts"
import type { Snapshot } from "@/api/client"

interface SignalRadarChartProps {
  snapshot: Snapshot
}

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-card border border-white/10 rounded-xl px-4 py-2 shadow-xl backdrop-blur-md">
        <p className="text-sm font-bold text-foreground">{payload[0].payload.signal}</p>
        <p className="text-lg font-black text-primary">{payload[0].value?.toFixed(0) ?? "N/A"}<span className="text-xs font-normal text-muted-foreground"> / 100</span></p>
      </div>
    )
  }
  return null
}

export function SignalRadarChart({ snapshot }: SignalRadarChartProps) {
  const data = [
    { signal: "Schedule", score: snapshot.schedule_score ?? null },
    { signal: "Budget", score: snapshot.budget_score ?? null },
    { signal: "Milestones", score: snapshot.milestone_score ?? null },
    { signal: "Blockers", score: snapshot.blocker_score ?? null },
    { signal: "Sentiment", score: snapshot.sentiment_score ?? null },
  ].filter(d => d.score !== null)

  if (data.length < 3) return null

  const avgScore = data.reduce((sum, d) => sum + (d.score ?? 0), 0) / data.length
  const color = avgScore >= 70 ? "#10b981" : avgScore >= 45 ? "#f59e0b" : "#ef4444"

  return (
    <div className="bg-card/60 backdrop-blur-2xl rounded-3xl border border-white/10 shadow-2xl p-6 flex flex-col items-center">
      <h3 className="text-lg font-bold mb-1 self-start flex items-center gap-2">
        <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: color }} />
        Signal Health Radar
      </h3>
      <p className="text-xs text-muted-foreground self-start mb-4">
        Visual profile of all 5 health signals (0-100 scale)
      </p>
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
          <PolarGrid stroke="rgba(255,255,255,0.1)" />
          <PolarAngleAxis
            dataKey="signal"
            tick={{ fill: "rgba(255,255,255,0.65)", fontSize: 13, fontWeight: 600 }}
          />
          <PolarRadiusAxis
            domain={[0, 100]}
            tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
            axisLine={false}
            tickCount={4}
          />
          <Radar
            name="Score"
            dataKey="score"
            stroke={color}
            fill={color}
            fillOpacity={0.25}
            strokeWidth={2}
            dot={{ r: 4, fill: color, strokeWidth: 2, stroke: "rgba(0,0,0,0.5)" }}
          />
          <Tooltip content={<CustomTooltip />} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}
