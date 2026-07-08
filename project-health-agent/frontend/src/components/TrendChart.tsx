import React from "react"
import { format, parseISO } from "date-fns"
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card"
import type { Snapshot } from "@/api/client"

interface TrendChartProps {
  history: Snapshot[]
}

export function TrendChart({ history }: TrendChartProps) {
  if (!history || history.length < 2) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle>Health Trend</CardTitle>
          <CardDescription>Insufficient data for trend analysis</CardDescription>
        </CardHeader>
        <CardContent className="h-64 flex items-center justify-center text-muted-foreground text-sm bg-muted/20 m-6 rounded-lg border border-dashed">
          Run analysis over multiple weeks to see trends
        </CardContent>
      </Card>
    )
  }

  // Format data for chart
  const data = history.map(snapshot => ({
    date: format(parseISO(snapshot.created_at), "MMM d"),
    score: snapshot.weighted_score,
    status: snapshot.rag_status,
  }))

  const latestScore = data[data.length - 1].score
  const previousScore = data[0].score // Comparing to earliest available for demo
  const isUp = latestScore >= previousScore
  const delta = Math.abs(latestScore - previousScore)

  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle>Health Trend</CardTitle>
            <CardDescription>Weighted score over time</CardDescription>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold">{latestScore.toFixed(0)}</div>
            <div className={`text-xs font-medium flex items-center justify-end gap-1 ${isUp ? "text-emerald-500" : "text-rose-500"}`}>
              {isUp ? "↗" : "↘"} {delta.toFixed(1)} pts
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[250px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
              <XAxis 
                dataKey="date" 
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                dy={10}
              />
              <YAxis 
                domain={[0, 100]} 
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                dx={-10}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: "hsl(var(--popover))", 
                  borderColor: "hsl(var(--border))",
                  borderRadius: "8px",
                  color: "hsl(var(--popover-foreground))",
                  boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)"
                }}
                itemStyle={{ color: "hsl(var(--primary))" }}
              />
              <ReferenceLine y={80} stroke="hsl(var(--rag-green))" strokeDasharray="3 3" opacity={0.5} />
              <ReferenceLine y={60} stroke="hsl(var(--rag-amber))" strokeDasharray="3 3" opacity={0.5} />
              <Area 
                type="monotone" 
                dataKey="score" 
                stroke="hsl(var(--primary))" 
                strokeWidth={3}
                fillOpacity={1} 
                fill="url(#colorScore)" 
                activeDot={{ r: 6, strokeWidth: 0, fill: "hsl(var(--primary))" }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
