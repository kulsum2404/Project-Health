import React from "react"
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
  Label,
} from "recharts"
import type { Snapshot, Project } from "@/api/client"

interface PortfolioScatterChartProps {
  history: Record<number, Snapshot[]>
  projects: Project[]
}

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const d = payload[0].payload
    return (
      <div className="bg-card border border-white/10 rounded-xl px-4 py-3 shadow-xl backdrop-blur-md max-w-[220px]">
        <p className="text-sm font-bold text-foreground truncate">{d.name}</p>
        <p className="text-xs text-muted-foreground mt-1">Schedule Score: <span className="text-indigo-400 font-bold">{d.scheduleLabel}</span></p>
        <p className="text-xs text-muted-foreground">Budget Score: <span className="text-teal-400 font-bold">{d.budgetLabel}</span></p>
        <p className="text-xs text-muted-foreground">Status: <span className="font-bold capitalize" style={{ color: d.color }}>{d.ragStatus}</span></p>
      </div>
    )
  }
  return null
}

export function PortfolioScatterChart({ history, projects }: PortfolioScatterChartProps) {
  const ragColors: Record<string, string> = {
    green: "#10b981",
    amber: "#f59e0b",
    red: "#ef4444",
  }

  const data = projects
    .map(project => {
      const snaps = history[project.id] || []
      if (snaps.length === 0) return null
      const latest = snaps[snaps.length - 1]
      if (latest.schedule_score === null && latest.budget_score === null) return null
      return {
        name: project.name,
        x: latest.schedule_score ?? latest.weighted_score,
        y: latest.budget_score ?? latest.weighted_score,
        ragStatus: latest.rag_status,
        color: ragColors[latest.rag_status] || "#6366f1",
        scheduleLabel: latest.schedule_score !== null ? `${latest.schedule_score.toFixed(0)}` : "N/A",
        budgetLabel: latest.budget_score !== null ? `${latest.budget_score.toFixed(0)}` : "N/A (using overall)",
      }
    })
    .filter(Boolean) as { name: string; x: number; y: number; ragStatus: string; color: string; scheduleLabel: string; budgetLabel: string }[]

  if (data.length === 0) return null

  return (
    <div className="w-full mt-8 mb-12 p-6 bg-card/40 backdrop-blur-xl border border-white/5 rounded-2xl shadow-2xl relative z-10">
      <h3 className="text-xl font-bold mb-1 flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
        Schedule vs. Budget Quadrant
      </h3>
      <p className="text-sm text-muted-foreground mb-6">
        Each dot is a project. Top-right = healthy. Bottom-left = critical risk.
      </p>
      <div className="h-[360px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 20, right: 30, bottom: 30, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" />
            <XAxis
              type="number"
              dataKey="x"
              domain={[0, 100]}
              name="Schedule Score"
              stroke="rgba(255,255,255,0.4)"
              tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 12 }}
              tickLine={false}
              axisLine={false}
            >
              <Label value="Schedule Score" position="bottom" offset={15} fill="rgba(255,255,255,0.4)" fontSize={12} fontWeight={600} />
            </XAxis>
            <YAxis
              type="number"
              dataKey="y"
              domain={[0, 100]}
              name="Budget Score"
              stroke="rgba(255,255,255,0.4)"
              tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 12 }}
              tickLine={false}
              axisLine={false}
            >
              <Label value="Budget Score" angle={-90} position="insideLeft" offset={15} fill="rgba(255,255,255,0.4)" fontSize={12} fontWeight={600} />
            </YAxis>
            {/* Quadrant dividers */}
            <ReferenceLine x={50} stroke="rgba(255,255,255,0.12)" strokeDasharray="6 4" />
            <ReferenceLine y={50} stroke="rgba(255,255,255,0.12)" strokeDasharray="6 4" />
            <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: "3 3", stroke: "rgba(255,255,255,0.2)" }} />
            <Scatter name="Projects" data={data} shape="circle">
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.color}
                  fillOpacity={0.85}
                  stroke={entry.color}
                  strokeWidth={2}
                  r={14}
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <div className="flex items-center justify-center gap-6 mt-2 flex-wrap">
        {[["#10b981", "Green (Healthy)"], ["#f59e0b", "Amber (Watch)"], ["#ef4444", "Red (At Risk)"]].map(([color, label]) => (
          <div key={label} className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full" style={{ background: color }} />
            <span className="text-xs text-muted-foreground font-medium">{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
