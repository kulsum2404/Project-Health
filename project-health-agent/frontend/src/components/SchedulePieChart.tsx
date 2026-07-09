import React from "react"
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts"

interface SchedulePieChartProps {
  data: any
}

export function SchedulePieChart({ data }: SchedulePieChartProps) {
  if (!data || !data.available || !data.details) return null
  
  const { total_tasks, overdue_tasks, late_completed_tasks } = data.details
  
  // Calculate on-time tasks
  const onTimeTasks = Math.max(0, total_tasks - (overdue_tasks || 0) - (late_completed_tasks || 0))
  
  const chartData = [
    { name: "On-Time / Pending", value: onTimeTasks, color: "#10b981" }, // emerald
    { name: "Overdue", value: overdue_tasks || 0, color: "#ef4444" }, // red
    { name: "Completed Late", value: late_completed_tasks || 0, color: "#f59e0b" }, // amber
  ].filter(d => d.value > 0)

  if (chartData.length === 0) return null

  return (
    <div className="bg-card/40 backdrop-blur-xl border border-white/5 rounded-3xl p-6 shadow-xl h-[350px] flex flex-col">
      <h4 className="text-lg font-bold mb-2 flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-xs">
          📅
        </div>
        Schedule Execution Breakdown
      </h4>
      <div className="flex-1 w-full relative">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={90}
              paddingAngle={5}
              dataKey="value"
              stroke="none"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip 
              contentStyle={{ 
                backgroundColor: "rgba(15, 23, 42, 0.9)", 
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
                color: "white"
              }}
              itemStyle={{ color: "white", fontWeight: "bold" }}
            />
            <Legend verticalAlign="bottom" height={36} iconType="circle" />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none mb-8">
          <div className="text-center">
            <span className="text-3xl font-black">{total_tasks}</span>
            <span className="block text-[10px] uppercase tracking-widest text-muted-foreground mt-1">Total Tasks</span>
          </div>
        </div>
      </div>
    </div>
  )
}
