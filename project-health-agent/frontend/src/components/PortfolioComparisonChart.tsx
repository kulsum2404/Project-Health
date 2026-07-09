import React from "react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts"
import type { Snapshot, Project } from "@/api/client"

interface PortfolioComparisonChartProps {
  history: Record<number, Snapshot[]>
  projects: Project[]
}

export function PortfolioComparisonChart({ history, projects }: PortfolioComparisonChartProps) {
  // Extract latest snapshot for each project
  const latestSnapshots: Record<string, Snapshot> = {}
  projects.forEach(project => {
    const projHistory = history[project.id] || []
    if (projHistory.length > 0) {
      // Assuming history is chronological, or we can just take the last element
      // since the backend returns them sorted by created_at asc
      latestSnapshots[project.name] = projHistory[projHistory.length - 1]
    }
  })

  // We want to compare across 5 signals
  const signals = [
    { key: "schedule_score", label: "Schedule" },
    { key: "budget_score", label: "Budget" },
    { key: "milestone_score", label: "Milestones" },
    { key: "blocker_score", label: "Blockers" },
    { key: "sentiment_score", label: "Sentiment" },
  ]

  // Build chart data where each row is a Signal, and columns are Projects
  const chartData = signals.map(sig => {
    const dataPoint: any = { subject: sig.label }
    projects.forEach(project => {
      const snap = latestSnapshots[project.name]
      if (snap && snap[sig.key as keyof Snapshot] !== null) {
        dataPoint[project.name] = snap[sig.key as keyof Snapshot]
      }
    })
    return dataPoint
  })

  const colors = [
    "#6366f1", // indigo
    "#ea0c7bff", // pink
    "#14b8a6", // teal
    "#f59e0b", // amber
    "#8b5cf6", // violet
    "#ef4444", // red
    "#3b82f6", // blue
    "#10b981", // emerald
  ]

  if (projects.length === 0 || Object.keys(latestSnapshots).length === 0) {
    return null
  }

  return (
    <div className="w-full h-[400px] mt-8 mb-12 p-6 bg-card/40 backdrop-blur-xl border border-white/5 rounded-2xl shadow-2xl relative z-10">
      <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
        Cross-Project Signal Comparison
      </h3>
      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
            <XAxis
              dataKey="subject"
              stroke="rgba(255,255,255,0.5)"
              tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 13, fontWeight: 500 }}
              tickLine={false}
              axisLine={false}
              dy={10}
            />
            <YAxis
              domain={[0, 100]}
              stroke="rgba(255,255,255,0.5)"
              tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              dx={-10}
            />
            <Tooltip
              cursor={{ fill: "rgba(255,255,255,0.05)" }}
              contentStyle={{
                backgroundColor: "rgba(15, 23, 42, 0.9)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "12px",
                backdropFilter: "blur(10px)",
                color: "white"
              }}
              itemStyle={{ fontSize: "14px", fontWeight: "bold" }}
            />
            <Legend
              wrapperStyle={{ paddingTop: "20px" }}
              iconType="circle"
            />
            {projects.map((project, idx) => (
              latestSnapshots[project.name] && (
                <Bar
                  key={project.id}
                  dataKey={project.name}
                  name={project.name.length > 20 ? project.name.substring(0, 20) + "..." : project.name}
                  fill={colors[idx % colors.length]}
                  radius={[4, 4, 0, 0]}
                  barSize={30}
                />
              )
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
