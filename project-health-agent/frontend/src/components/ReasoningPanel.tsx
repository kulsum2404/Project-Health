import React, { useState, useEffect } from "react"
import { ChevronDown, Bot, FileText, CheckCircle2, AlertCircle, Info, Ban, ThumbsUp, ThumbsDown } from "lucide-react"
import { Card, CardContent } from "./ui/card"
import { Badge } from "./ui/badge"
import { motion, AnimatePresence } from "framer-motion"
import { api } from "@/api/client"

interface SignalDetailData {
  score: number
  available: boolean
  details: Record<string, any>
  reason: string
}

interface ReasoningPanelProps {
  reasoning: string
  confidence: number
  signalsUsed: string[]
  signalsSkipped: string[]
  signalDetails: Record<string, SignalDetailData>
  signalSummaries: Record<string, string>
  weightedScore: number
  ragStatus: string
  projectName: string
  managerName: string
  createdAt: string
  sourceFile: string
  sheetCount: number
  totalTasks: number
  projectId: number
  snapshotId: number
  feedbackScore: number
}

// Signal display config
const SIGNAL_CONFIG: Record<string, { label: string; defaultWeight: number }> = {
  schedule: { label: "Schedule", defaultWeight: 0.30 },
  budget: { label: "Budget", defaultWeight: 0.20 },
  milestones: { label: "Milestones", defaultWeight: 0.20 },
  blockers: { label: "Blockers", defaultWeight: 0.15 },
  sentiment: { label: "Sentiment", defaultWeight: 0.15 },
}

const SIGNAL_ORDER = ["schedule", "budget", "milestones", "blockers", "sentiment"]

/** Parse quoted phrases in text and render them as highlighted spans */
function HighlightedText({ text }: { text: string }) {
  if (!text) return null

  // Split on quoted phrases: "something"
  const parts = text.split(/(".*?")/g)
  
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith('"') && part.endsWith('"')) {
          const inner = part.slice(1, -1)
          // Color based on content
          let className = "text-indigo-400 font-semibold"
          const lower = inner.toLowerCase()
          if (lower.includes("red") || lower.includes("high") || lower.includes("critical") || lower.includes("at risk")) {
            className = "text-rose-400 font-semibold"
          } else if (lower.includes("green") || lower.includes("on track") || lower.includes("complete")) {
            className = "text-emerald-400 font-semibold"
          } else if (lower.includes("amber") || lower.includes("medium") || lower.includes("warning")) {
            className = "text-amber-400 font-semibold"
          }
          return <span key={i} className={className}>"{inner}"</span>
        }
        return <span key={i}>{part}</span>
      })}
    </>
  )
}

/** Typewriter effect for the executive summary */
const TypewriterText = ({ text }: { text: string }) => {
  const [displayedText, setDisplayedText] = useState("")

  useEffect(() => {
    setDisplayedText("")
    let i = 0
    const intervalId = setInterval(() => {
      setDisplayedText(text.slice(0, i))
      i += 4
      if (i > text.length + 4) {
        clearInterval(intervalId)
        setDisplayedText(text)
      }
    }, 12)

    return () => clearInterval(intervalId)
  }, [text])

  const isComplete = displayedText === text

  return (
    <span>
      <HighlightedText text={displayedText} />
      {!isComplete && (
        <motion.span
          animate={{ opacity: [1, 0] }}
          transition={{ repeat: Infinity, duration: 0.8 }}
          className="inline-block w-1.5 h-4 ml-1 bg-primary align-middle"
        />
      )}
    </span>
  )
}

function getScoreColor(score: number) {
  if (score >= 80) return "bg-emerald-500"
  if (score >= 60) return "bg-amber-500"
  return "bg-rose-500"
}

function getScoreTextColor(score: number) {
  if (score >= 80) return "text-emerald-400"
  if (score >= 60) return "text-amber-400"
  return "text-rose-400"
}

function getRagBadgeClasses(status: string) {
  switch (status) {
    case "green": return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
    case "amber": return "bg-amber-500/20 text-amber-400 border-amber-500/30"
    case "red": return "bg-rose-500/20 text-rose-400 border-rose-500/30"
    default: return "bg-gray-500/20 text-gray-400 border-gray-500/30"
  }
}

export function ReasoningPanel({
  reasoning,
  confidence,
  signalsUsed,
  signalsSkipped,
  signalDetails,
  signalSummaries,
  weightedScore,
  ragStatus,
  projectName,
  managerName,
  createdAt,
  sourceFile,
  sheetCount,
  totalTasks,
  projectId,
  snapshotId,
  feedbackScore,
}: ReasoningPanelProps) {
  const [expandedSignal, setExpandedSignal] = useState<string | null>(null)
  const [currentFeedback, setCurrentFeedback] = useState(feedbackScore)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleFeedback = async (score: number) => {
    if (score === currentFeedback || isSubmitting) return
    setIsSubmitting(true)
    try {
      await api.submitFeedback(projectId, snapshotId, score)
      setCurrentFeedback(score)
    } catch (err) {
      console.error("Failed to submit feedback", err)
    } finally {
      setIsSubmitting(false)
    }
  }

  // Calculate redistributed weights
  const totalAvailableWeight = SIGNAL_ORDER.reduce((sum, key) => {
    const data = signalDetails[key]
    if (data?.available) return sum + SIGNAL_CONFIG[key].defaultWeight
    return sum
  }, 0)

  const getRedistributedWeight = (key: string) => {
    if (totalAvailableWeight === 0) return 0
    return SIGNAL_CONFIG[key].defaultWeight / totalAvailableWeight
  }

  const availableCount = signalsUsed.length
  const totalSignals = signalsUsed.length + signalsSkipped.length
  const skippedNames = signalsSkipped.map(s => SIGNAL_CONFIG[s]?.label || s).join(", ")

  const reportDate = new Date(createdAt)
  const formattedDate = reportDate.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).toUpperCase()

  return (
    <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-2xl overflow-hidden rounded-3xl relative">
      {/* Subtle top glow */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent opacity-50" />

      {/* ── HEADER ── */}
      <div className="px-8 pt-6 pb-4">
        <p className="text-[11px] font-bold text-muted-foreground/70 uppercase tracking-[0.25em] mb-4">
          Weekly Health Report · {formattedDate}
        </p>

        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 className="text-2xl font-black tracking-tight text-foreground truncate">
              {projectName}
            </h2>
            <p className="text-sm text-muted-foreground mt-1 font-medium">
              {managerName}
            </p>
          </div>

          <Badge
            className={`${getRagBadgeClasses(ragStatus)} border text-sm font-black uppercase px-4 py-1.5 rounded-full shadow-lg shrink-0`}
          >
            <span className={`w-2 h-2 rounded-full mr-2 inline-block ${ragStatus === "green" ? "bg-emerald-400" : ragStatus === "amber" ? "bg-amber-400" : "bg-rose-400"}`} />
            {ragStatus}
          </Badge>
        </div>
      </div>

      <CardContent className="px-8 pb-8 pt-0 space-y-8">
        {/* ── SCORE + CONFIDENCE ROW ── */}
        <div className="flex items-end gap-8 pt-4">
          <div>
            <span className={`text-6xl font-black tabular-nums leading-none ${getScoreTextColor(weightedScore)}`}>
              {Math.round(weightedScore)}
            </span>
            <p className="text-xs text-muted-foreground/60 font-bold uppercase tracking-wider mt-1">
              Composite Score / 100
            </p>
          </div>

          <div className="flex-1 space-y-2 pb-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground font-semibold">data confidence</span>
              <span className="text-muted-foreground font-bold tabular-nums">{Math.round(confidence * 100)}%</span>
            </div>
            <div className="h-2 w-full bg-black/40 rounded-full overflow-hidden shadow-inner">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${confidence * 100}%` }}
                transition={{ duration: 1.2, ease: "easeOut" }}
                className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
              />
            </div>
            <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground/60">
              <Info className="w-3 h-3" />
              <span>
                {availableCount} of {totalSignals} signals available
                {signalsSkipped.length > 0 && ` — ${skippedNames.toLowerCase()} data absent`}
              </span>
            </div>
          </div>
        </div>

        {/* ── EXECUTIVE SUMMARY ── */}
        <div className="bg-black/30 rounded-2xl p-6 border border-white/5 shadow-inner group">
          <div className="flex items-start gap-3">
            <div className="mt-1 text-muted-foreground/40 shrink-0">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z" />
                <path d="M15 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2h.75c0 2.25.25 4-2.75 4v3c0 1 0 1 1 1z" />
              </svg>
            </div>
            <div className="text-sm text-foreground/90 leading-relaxed font-medium flex-1">
              <TypewriterText text={reasoning.replace(/\*\*/g, "")} />
            </div>
          </div>
          
          <div className="flex items-center justify-end gap-2 mt-4 pt-4 border-t border-white/5 opacity-0 group-hover:opacity-100 transition-opacity">
            <span className="text-xs text-muted-foreground mr-2 font-medium">Was this analysis accurate?</span>
            <button 
              onClick={() => handleFeedback(1)}
              disabled={isSubmitting}
              className={`p-1.5 rounded-md transition-colors border ${currentFeedback === 1 ? 'text-green-500 bg-green-500/10 border-green-500/30' : 'text-muted-foreground hover:bg-white/10 border-transparent hover:border-white/10'}`}
              title="Yes, accurate"
            >
              <ThumbsUp className="w-4 h-4" />
            </button>
            <button 
              onClick={() => handleFeedback(-1)}
              disabled={isSubmitting}
              className={`p-1.5 rounded-md transition-colors border ${currentFeedback === -1 ? 'text-rose-500 bg-rose-500/10 border-rose-500/30' : 'text-muted-foreground hover:bg-white/10 border-transparent hover:border-white/10'}`}
              title="No, inaccurate"
            >
              <ThumbsDown className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* ── SIGNAL BREAKDOWN ── */}
        <div className="space-y-1">
          <p className="text-[11px] font-bold text-muted-foreground/60 uppercase tracking-[0.2em] mb-3">
            Signal Breakdown
          </p>

          {SIGNAL_ORDER.map(key => {
            const data = signalDetails[key]
            const config = SIGNAL_CONFIG[key]
            const isAvailable = data?.available
            const isExcluded = !isAvailable
            const isExpanded = expandedSignal === key
            const redistributedWeight = isAvailable ? getRedistributedWeight(key) : 0
            const score = data?.score ?? 0
            const summary = signalSummaries[key] || data?.reason || ""

            return (
              <div key={key} className="border-b border-white/5 last:border-b-0">
                <button
                  className="w-full flex items-center gap-3 py-3.5 px-1 text-left hover:bg-white/[0.02] transition-colors group"
                  onClick={() => setExpandedSignal(isExpanded ? null : key)}
                >
                  <motion.div
                    animate={{ rotate: isExpanded ? 90 : 0 }}
                    transition={{ duration: 0.2 }}
                    className="text-muted-foreground/50"
                  >
                    <ChevronDown className="w-3.5 h-3.5 -rotate-90" />
                  </motion.div>

                  <span className="font-bold text-sm text-foreground/90 min-w-[90px]">
                    {config.label}
                  </span>

                  {isExcluded && (
                    <Badge className="bg-white/5 text-muted-foreground/50 border-white/10 text-[10px] font-bold px-2 py-0 rounded-md uppercase">
                      Excluded
                    </Badge>
                  )}

                  <div className="flex-1" />

                  {isAvailable ? (
                    <>
                      {/* Progress bar */}
                      <div className="w-48 h-1.5 bg-black/40 rounded-full overflow-hidden shadow-inner hidden sm:block">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${score}%` }}
                          transition={{ duration: 1, ease: "easeOut", delay: 0.2 }}
                          className={`h-full rounded-full ${getScoreColor(score)}`}
                        />
                      </div>

                      <span className="text-xs text-muted-foreground/50 font-mono tabular-nums w-16 text-right">
                        {(redistributedWeight * 100).toFixed(redistributedWeight * 100 % 1 === 0 ? 0 : 2)}% wt
                      </span>

                      <span className={`text-sm font-black tabular-nums w-8 text-right ${getScoreTextColor(score)}`}>
                        {Math.round(score)}
                      </span>
                    </>
                  ) : (
                    <>
                      <span className="text-xs text-muted-foreground/30 font-mono tabular-nums w-16 text-right">
                        0% wt
                      </span>
                      <span className="text-sm text-muted-foreground/30 font-bold tabular-nums w-8 text-right">
                        —
                      </span>
                    </>
                  )}
                </button>

                <AnimatePresence>
                  {isExpanded && summary && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3, ease: "easeInOut" }}
                      className="overflow-hidden"
                    >
                      <div className="pl-9 pr-4 pb-4">
                        <p className="text-sm text-foreground/70 leading-relaxed">
                          <HighlightedText text={summary} />
                        </p>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )
          })}
        </div>

        {/* ── FOOTER ── */}
        {(sourceFile || totalTasks > 0) && (
          <div className="flex items-center justify-between text-[11px] text-muted-foreground/40 font-mono pt-4 border-t border-white/5">
            <span>
              {sourceFile && `source: ${sourceFile}`}
              {sheetCount > 0 && ` · sheet 1 of ${sheetCount}`}
            </span>
            {totalTasks > 0 && (
              <span>{totalTasks} tasks analyzed</span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
