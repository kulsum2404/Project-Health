import React from "react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts"
import { format, parseISO } from "date-fns"
import type { Snapshot, Project } from "@/api/client"

interface PortfolioTrendChartProps {
  history: Record<number, Snapshot[]>
  projects: Project[]
}

export function PortfolioTrendChart({ history, projects }: PortfolioTrendChartProps) {
  // Find all unique dates across all snapshots
  const allDates = new Set<string>()
  Object.values(history).forEach(snaps => {
    snaps.forEach(s => {
      const dateStr = format(parseISO(s.created_at), "yyyy-MM-dd")
      allDates.add(dateStr)
    })
  })

  // Sort dates chronologically
  const sortedDates = Array.from(allDates).sort()

  // Build the chart data
  const chartData = sortedDates.map(dateStr => {
    const dataPoint: any = { date: dateStr, displayDate: format(parseISO(dateStr), "MMM d") }
    
    // For each project, find the snapshot on or before this date
    projects.forEach(project => {
      const projHistory = history[project.id] || []
      const snapshot = [...projHistory].reverse().find(s => {
        return format(parseISO(s.created_at), "yyyy-MM-dd") <= dateStr
      })
      if (snapshot) {
        dataPoint[project.name] = snapshot.weighted_score
      }
    })
    
    return dataPoint
  })

  const colors = [
    "#6366f1", // indigo
    "#ec4899", // pink
    "#14b8a6", // teal
    "#f59e0b", // amber
    "#8b5cf6", // violet
    "#ef4444", // red
    "#3b82f6", // blue
    "#10b981", // emerald
  ]

  if (chartData.length === 0) {
    return null
  }

  return (
    <div className="w-full h-[400px] mt-8 mb-12 p-6 bg-card/40 backdrop-blur-xl border border-white/5 rounded-2xl shadow-2xl relative z-10">
      <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
        Portfolio Progress Trend
      </h3>
      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
            <XAxis 
              dataKey="displayDate" 
              stroke="rgba(255,255,255,0.5)"
              tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 12 }}
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
              chartData.some(d => d[project.name] !== undefined) && (
                <Line
                  key={project.id}
                  type="monotone"
                  dataKey={project.name}
                  name={project.name.length > 20 ? project.name.substring(0, 20) + "..." : project.name}
                  stroke={colors[idx % colors.length]}
                  strokeWidth={3}
                  dot={{ r: 4, strokeWidth: 2, fill: "rgba(15,23,42,1)" }}
                  activeDot={{ r: 6, strokeWidth: 0 }}
                  connectNulls
                />
              )
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
