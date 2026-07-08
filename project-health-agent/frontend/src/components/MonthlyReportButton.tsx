import React, { useState } from "react"
import { Presentation, Loader2, Download, AlertTriangle } from "lucide-react"
import { Button } from "./ui/button"
import { api } from "@/api/client"

export function MonthlyReportButton() {
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleGenerate = async () => {
    setIsGenerating(true)
    setError(null)
    
    try {
      const report = await api.synthesizeMonthly()
      if (report.has_pptx) {
        // Trigger download safely without popup blocker
        const url = api.getMonthlyReportDownloadUrl(report.id)
        const a = document.createElement("a")
        a.href = url
        a.download = `Monthly_Report_${report.id}.pptx`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
      } else {
        setError("Report generated but PPTX file could not be created.")
      }
    } catch (err: any) {
      setError(err.message || "Failed to generate monthly report")
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <Button 
        variant="secondary" 
        onClick={handleGenerate} 
        disabled={isGenerating}
        className="gap-2 border border-primary/20 bg-secondary/80 hover:bg-secondary shadow-sm"
      >
        {isGenerating ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Synthesizing Trends...
          </>
        ) : (
          <>
            <Presentation className="w-4 h-4 text-primary" />
            Generate Monthly Deck
          </>
        )}
      </Button>
      
      {error && (
        <div className="text-xs text-destructive flex items-center gap-1 max-w-[200px] text-right">
          <AlertTriangle className="w-3 h-3 shrink-0" />
          <span className="truncate">{error}</span>
        </div>
      )}
    </div>
  )
}
