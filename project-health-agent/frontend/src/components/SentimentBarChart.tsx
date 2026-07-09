import React from "react"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts"

interface SentimentBarChartProps {
  data: any
}

export function SentimentBarChart({ data }: SentimentBarChartProps) {
  if (!data || !data.available || !data.details || !data.details.sentiment_distribution) return null
  
  const dist = data.details.sentiment_distribution
  
  const chartData = [
    { name: "Positive", value: dist.positive || 0, color: "#10b981" },
    { name: "Neutral", value: dist.neutral || 0, color: "#94a3b8" },
    { name: "Negative", value: dist.negative || 0, color: "#ef4444" },
  ]

  const hasData = chartData.some(d => d.value > 0)
  if (!hasData) return null

  return (
    <div className="bg-card/40 backdrop-blur-xl border border-white/5 rounded-3xl p-6 shadow-xl h-[350px] flex flex-col">
      <h4 className="text-lg font-bold mb-6 flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-pink-500/20 text-pink-400 flex items-center justify-center text-xs">
          💬
        </div>
        Stakeholder Sentiment Distribution
      </h4>
      <div className="flex-1 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: -20, bottom: 5 }} barSize={50}>
            <XAxis 
              dataKey="name" 
              stroke="rgba(255,255,255,0.5)"
              tick={{ fill: "rgba(255,255,255,0.8)", fontSize: 12, fontWeight: "bold" }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis 
              stroke="rgba(255,255,255,0.2)"
              tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              allowDecimals={false}
            />
            <Tooltip 
              cursor={{ fill: "rgba(255,255,255,0.05)" }}
              contentStyle={{ 
                backgroundColor: "rgba(15, 23, 42, 0.9)", 
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
                color: "white"
              }}
              itemStyle={{ color: "white", fontWeight: "bold" }}
            />
            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
