import React, { useEffect, useState } from "react"
import { useParams, Link, useNavigate } from "react-router-dom"
import { format, parseISO } from "date-fns"
import { ArrowLeft, RefreshCw, AlertTriangle, Calendar, DollarSign, Flag, ShieldAlert, MessageSquare, Activity, ChevronRight, ChevronDown, Zap, Edit2, Check as CheckIcon, X, ArrowRight, Trash2, Loader2, Sparkles } from "lucide-react"
import { api, type ReportResponse, type Snapshot, type Project } from "@/api/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { ReasoningPanel } from "@/components/ReasoningPanel"
import { TrendChart } from "@/components/TrendChart"
import type { Variants } from "framer-motion"
import { motion, AnimatePresence } from "framer-motion"
import { SchedulePieChart } from "@/components/SchedulePieChart"
import { SentimentBarChart } from "@/components/SentimentBarChart"

// Animation Variants
const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.15 }
  }
}

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 30 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { type: "spring", stiffness: 100, damping: 15 }
  }
}

export function ProjectDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const projectId = parseInt(id || "0", 10)
  
  const [project, setProject] = useState<Project | null>(null)
  const [report, setReport] = useState<ReportResponse | null>(null)
  const [history, setHistory] = useState<Snapshot[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisStep, setAnalysisStep] = useState(0)
  const [error, setError] = useState<string | null>(null)
  
  const [isEditingName, setIsEditingName] = useState(false)
  const [editedName, setEditedName] = useState("")
  
  const [isEditingManager, setIsEditingManager] = useState(false)
  const [editedManager, setEditedManager] = useState("")

  const fetchProjectData = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const projData = await api.getProject(projectId)
      setProject(projData)
      setEditedName(projData.name)
      setEditedManager(projData.manager_name)
      
      try {
        const reportData = await api.getLatestReport(projectId)
        setReport(reportData)
        const historyData = await api.getProjectHistory(projectId)
        setHistory(historyData)
      } catch (err: any) {
        if (err.message && err.message.includes("No analysis snapshots")) {
          setReport(null)
        } else {
          throw err
        }
      }
    } catch (err: any) {
      setError(err.message || "Failed to load project details")
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeleteProject = async () => {
    if (!confirm("Are you sure you want to delete this project?")) return
    
    try {
      await api.deleteProject(projectId)
      navigate("/")
    } catch (err: any) {
      setError(err.message || "Failed to delete project")
    }
  }

  useEffect(() => {
    if (projectId) {
      fetchProjectData()
    }
  }, [projectId])

  const handleRename = async () => {
    if (!editedName.trim() || !project || editedName === project.name) {
      setIsEditingName(false)
      return
    }
    
    try {
      await api.updateProject(projectId, { name: editedName })
      setProject({ ...project, name: editedName })
      if (report) {
        setReport({ ...report, project_name: editedName })
      }
      setIsEditingName(false)
    } catch (err: any) {
      setError(err.message || "Failed to rename project")
    }
  }

  const handleRenameManager = async () => {
    if (!editedManager.trim() || !project || editedManager === project.manager_name) {
      setIsEditingManager(false)
      return
    }
    
    try {
      await api.updateProject(projectId, { manager_name: editedManager })
      setProject({ ...project, manager_name: editedManager })
      setIsEditingManager(false)
    } catch (err: any) {
      setError(err.message || "Failed to update project manager")
    }
  }

  const handleRunAnalysis = async () => {
    setIsAnalyzing(true)
    setAnalysisStep(0)
    setError(null)
    
    // Simulate steps for the "crazy" animation
    const interval = setInterval(() => {
      setAnalysisStep(prev => prev < 4 ? prev + 1 : prev)
    }, 1500)
    
    try {
      await api.analyzeProject(projectId)
      clearInterval(interval)
      setAnalysisStep(5) // Complete
      setTimeout(async () => {
        await fetchProjectData()
        setIsAnalyzing(false)
      }, 1000)
    } catch (err: any) {
      clearInterval(interval)
      setError(err.message || "Analysis failed")
      setIsAnalyzing(false)
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto py-8 px-4 flex items-center justify-center min-h-[50vh]">
        <motion.div 
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full shadow-[0_0_15px_rgba(99,102,241,0.5)]"
        />
      </div>
    )
  }

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="container mx-auto py-8 px-4 max-w-7xl relative z-10"
    >
      {/* Crazy Analysis Overlay */}
      <AnimatePresence>
        {isAnalyzing && (
          <motion.div 
            initial={{ opacity: 0, backdropFilter: "blur(0px)" }}
            animate={{ opacity: 1, backdropFilter: "blur(20px)" }}
            exit={{ opacity: 0, backdropFilter: "blur(0px)" }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-background/80"
          >
            <div className="relative w-full max-w-2xl p-8 rounded-3xl bg-card/50 border border-white/10 shadow-2xl overflow-hidden">
              {/* Scanning laser line — sweeps top to bottom */}
              <motion.div 
                animate={{ top: ["0%", "100%", "0%"] }}
                transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
                style={{ position: "absolute", left: 0, right: 0, height: "2px" }}
                className="bg-gradient-to-r from-transparent via-primary to-transparent shadow-[0_0_15px_rgba(99,102,241,0.8),0_0_30px_rgba(99,102,241,0.4)] z-20"
              />
              {/* Secondary glow that follows the line */}
              <motion.div 
                animate={{ top: ["0%", "100%", "0%"] }}
                transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
                style={{ position: "absolute", left: "10%", right: "10%", height: "40px", filter: "blur(20px)" }}
                className="bg-primary/20 z-0"
              />
              
              <div className="relative z-10 text-center space-y-8">
                <motion.div
                  animate={{ scale: [1, 1.1, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="w-24 h-24 mx-auto bg-primary/20 rounded-full flex items-center justify-center shadow-[0_0_30px_rgba(99,102,241,0.5)]"
                >
                  <Zap className="w-12 h-12 text-primary" />
                </motion.div>
                
                <h2 className="text-3xl font-black tracking-widest uppercase text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 animate-pulse">
                  System Analyzing
                </h2>
                
                <div className="space-y-4 text-left max-w-sm mx-auto">
                  <AnalysisStep label="Ingesting Project Data" active={analysisStep >= 0} done={analysisStep > 0} />
                  <AnalysisStep label="Extracting NLP Signals" active={analysisStep >= 1} done={analysisStep > 1} />
                  <AnalysisStep label="Calculating SPI & CPI" active={analysisStep >= 2} done={analysisStep > 2} />
                  <AnalysisStep label="LLM Evaluating Reasoning" active={analysisStep >= 3} done={analysisStep > 3} />
                  <AnalysisStep label="Compiling Executive Report" active={analysisStep >= 4} done={analysisStep > 4} />
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="mb-8">
        <Link 
          to="/" 
          className="inline-flex items-center text-sm font-bold text-muted-foreground hover:text-primary transition-colors mb-6 group bg-card/50 px-4 py-2 rounded-full border border-white/5 hover:border-primary/30"
        >
          <ArrowLeft className="w-4 h-4 mr-2 group-hover:-translate-x-1 transition-transform" /> 
          Back to Dashboard
        </Link>
        
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <motion.div initial={{ x: -20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ duration: 0.5 }}>
            {isEditingName ? (
              <div className="flex items-center gap-2">
                <Input 
                  value={editedName}
                  onChange={(e) => setEditedName(e.target.value)}
                  className="text-3xl font-black h-12 w-96 bg-card/50 border-white/20 text-foreground focus-visible:ring-primary"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleRename()
                    if (e.key === 'Escape') setIsEditingName(false)
                  }}
                />
                <Button size="icon" variant="ghost" onClick={handleRename} className="text-green-500 hover:text-green-400 hover:bg-green-500/10">
                  <CheckIcon className="w-5 h-5" />
                </Button>
                <Button size="icon" variant="ghost" onClick={() => { setIsEditingName(false); setEditedName(project?.name || "") }} className="text-muted-foreground hover:text-foreground">
                  <X className="w-5 h-5" />
                </Button>
              </div>
            ) : (
              <h1 className="text-4xl font-black tracking-tight drop-shadow-md flex items-center gap-3 group">
                {project?.name || `Project #${projectId}`}
                <Button size="icon" variant="ghost" onClick={() => setIsEditingName(true)} className="opacity-0 group-hover:opacity-100 transition-opacity w-8 h-8 rounded-full bg-white/5">
                  <Edit2 className="w-4 h-4 text-muted-foreground" />
                </Button>
              </h1>
            )}
            
            {report && (
              <p className="text-muted-foreground mt-2 font-medium flex items-center gap-2">
                <Activity className="w-4 h-4 text-primary" />
                Last analyzed: {format(parseISO(report.snapshot.created_at), "PPP 'at' p")}
              </p>
            )}
            
            {project && (
              <div className="flex flex-wrap items-center gap-6 mt-4 text-sm bg-black/20 p-3 rounded-xl border border-white/5 inline-flex backdrop-blur-sm">
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground uppercase tracking-wider text-[10px] font-bold">Manager</span>
                  {isEditingManager ? (
                    <div className="flex items-center gap-1">
                      <Input 
                        value={editedManager}
                        onChange={(e) => setEditedManager(e.target.value)}
                        className="h-7 w-40 text-xs bg-black/40 border-white/20"
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleRenameManager()
                          if (e.key === 'Escape') setIsEditingManager(false)
                        }}
                      />
                      <Button size="icon" variant="ghost" onClick={handleRenameManager} className="h-7 w-7 text-green-500">
                        <CheckIcon className="w-3 h-3" />
                      </Button>
                      <Button size="icon" variant="ghost" onClick={() => setIsEditingManager(false)} className="h-7 w-7 text-muted-foreground">
                        <X className="w-3 h-3" />
                      </Button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1 group/manager">
                      <span className="font-semibold">{project.manager_name || "Unassigned"}</span>
                      <Button size="icon" variant="ghost" onClick={() => setIsEditingManager(true)} className="opacity-0 group-hover/manager:opacity-100 transition-opacity w-5 h-5 rounded-full">
                        <Edit2 className="w-3 h-3 text-muted-foreground" />
                      </Button>
                    </div>
                  )}
                </div>
                
                <div className="w-px h-4 bg-white/10" />
                
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground uppercase tracking-wider text-[10px] font-bold">Timeline</span>
                  <span className="font-semibold text-foreground/80 flex items-center gap-1.5">
                    <Calendar className="w-3 h-3" />
                    {project.start_date ? format(new Date(project.start_date), 'MMM d, yy') : 'N/A'} 
                    <ArrowRight className="w-3 h-3 mx-0.5 text-muted-foreground" /> 
                    {project.end_date ? format(new Date(project.end_date), 'MMM d, yy') : 'N/A'}
                  </span>
                </div>
              </div>
            )}
          </motion.div>
          
          <motion.div initial={{ x: 20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ duration: 0.5 }} className="flex items-center gap-3">
            <Button 
              onClick={handleDeleteProject}
              variant="outline"
              size="lg"
              className="border-destructive/30 text-destructive hover:bg-destructive/10 gap-2 font-bold"
            >
              <Trash2 className="w-5 h-5" />
              Delete
            </Button>
            <Button 
              onClick={handleRunAnalysis} 
              disabled={isAnalyzing} 
              size="lg"
              className="gap-2 shadow-[0_0_20px_rgba(99,102,241,0.3)] hover:shadow-[0_0_30px_rgba(99,102,241,0.5)] transition-all bg-gradient-to-r from-indigo-500 to-purple-600 border-0 font-bold"
            >
              <RefreshCw className={`w-5 h-5 ${isAnalyzing ? "animate-spin" : ""}`} />
              {isAnalyzing ? "Analyzing Core..." : "Run Weekly Analysis"}
            </Button>
          </motion.div>
        </div>
      </div>

      {error && (
        <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="mb-8 p-6 text-destructive bg-destructive/10 rounded-2xl border border-destructive/20 flex items-start gap-4 backdrop-blur-md">
          <AlertTriangle className="w-6 h-6 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-bold text-lg">System Error</h4>
            <p className="text-sm mt-1">{error}</p>
          </div>
        </motion.div>
      )}

      {!report && !isLoading && !error && (
        <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="flex flex-col items-center justify-center p-16 text-center border rounded-3xl bg-card/40 backdrop-blur-xl border-dashed border-white/10 min-h-[40vh] shadow-2xl">
          <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mb-6 shadow-[0_0_30px_rgba(99,102,241,0.1)]">
            <RefreshCw className="w-10 h-10 text-primary/70" />
          </div>
          <h3 className="text-2xl font-black">No Analysis Data Found</h3>
          <p className="text-muted-foreground mt-3 max-w-md text-lg">
            This project matrix is currently empty. Initialize the first analysis sequence to generate RAG status and health signals.
          </p>
          <Button onClick={handleRunAnalysis} disabled={isAnalyzing} size="lg" className="mt-8 gap-2 bg-primary/20 text-primary hover:bg-primary/30 shadow-[0_0_20px_rgba(99,102,241,0.2)]">
            {isAnalyzing ? "Initializing..." : "Run Initial Analysis"}
          </Button>
        </motion.div>
      )}

      {report && (
        <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="space-y-8">
          
          {/* ── Weekly Health Report (primary view) ── */}
          <motion.div variants={fadeUp}>
            <ReasoningPanel
              reasoning={report.snapshot.reasoning}
              confidence={report.snapshot.confidence}
              signalsUsed={report.snapshot.signals_used}
              signalsSkipped={report.snapshot.signals_skipped}
              signalDetails={report.snapshot.signal_details}
              signalSummaries={report.snapshot.signal_summaries || {}}
              weightedScore={report.snapshot.weighted_score}
              ragStatus={report.snapshot.rag_status}
              projectName={project?.name || `Project #${projectId}`}
              managerName={project?.manager_name || "Unassigned"}
              createdAt={report.snapshot.created_at}
              sourceFile={report.snapshot.source_file || ""}
              sheetCount={report.snapshot.sheet_count || 0}
              totalTasks={report.snapshot.total_tasks || 0}
            />
          </motion.div>

          {/* ── Trend Chart ── */}
          {history.length > 0 && (
            <motion.div variants={fadeUp}>
              <div className="bg-card/60 backdrop-blur-2xl rounded-3xl border border-white/10 shadow-2xl p-2">
                <TrendChart history={history} />
              </div>
            </motion.div>
          )}

          {/* ── Signal Detail Cards ── */}
          <motion.div variants={fadeUp}>
            <h3 className="text-2xl font-black mt-12 mb-6 tracking-tight flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center text-primary">
                <Activity className="w-5 h-5" />
              </div>
              Signal Details
            </h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <SignalCard name="Schedule" signalKey="schedule" projectId={projectId} icon={<Calendar className="w-5 h-5" />} data={report.snapshot.signal_details.schedule} />
              <SignalCard name="Budget" signalKey="budget" projectId={projectId} icon={<DollarSign className="w-5 h-5" />} data={report.snapshot.signal_details.budget} />
              <SignalCard name="Milestones" signalKey="milestones" projectId={projectId} icon={<Flag className="w-5 h-5" />} data={report.snapshot.signal_details.milestones} />
              <SignalCard name="Blockers" signalKey="blockers" projectId={projectId} icon={<ShieldAlert className="w-5 h-5" />} data={report.snapshot.signal_details.blockers} />
              <SignalCard name="Sentiment" signalKey="sentiment" projectId={projectId} icon={<MessageSquare className="w-5 h-5" />} data={report.snapshot.signal_details.sentiment} />
            </div>
          </motion.div>

          {/* ── Deep Dive Analytics Charts ── */}
          {(report.snapshot.signal_details.schedule?.available || report.snapshot.signal_details.sentiment?.available) && (
            <motion.div variants={fadeUp}>
              <h3 className="text-2xl font-black mt-12 mb-6 tracking-tight flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-teal-500/20 flex items-center justify-center text-teal-400">
                  <Activity className="w-5 h-5" />
                </div>
                Deep Dive Analytics
              </h3>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <SchedulePieChart data={report.snapshot.signal_details.schedule} />
                <SentimentBarChart data={report.snapshot.signal_details.sentiment} />
              </div>
            </motion.div>
          )}

          {/* Blockers Table */}
          {report.blockers.length > 0 && (
            <motion.div variants={fadeUp}>
              <h3 className="text-2xl font-black mt-12 mb-6 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-destructive/20 flex items-center justify-center text-destructive">
                  <ShieldAlert className="w-5 h-5" />
                </div>
                Active Blockers
                <Badge variant="destructive" className="ml-2 rounded-md font-black text-sm px-3 shadow-[0_0_10px_rgba(244,63,94,0.5)]">
                  {report.blockers.length} Detected
                </Badge>
              </h3>
              <div className="rounded-3xl border border-white/10 bg-card/40 backdrop-blur-xl overflow-hidden shadow-2xl">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-black/40 text-muted-foreground uppercase text-xs tracking-wider">
                      <tr>
                        <th className="px-6 py-5 font-bold">Description</th>
                        <th className="px-6 py-5 font-bold">Severity</th>
                        <th className="px-6 py-5 font-bold">Age</th>
                        <th className="px-6 py-5 font-bold">Reported</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {report.blockers.map(blocker => (
                        <tr key={blocker.id} className="hover:bg-white/5 transition-colors group">
                          <td className="px-6 py-5 font-medium max-w-md truncate group-hover:text-primary transition-colors" title={blocker.description}>
                            {blocker.description}
                          </td>
                          <td className="px-6 py-5">
                            <Badge variant={blocker.severity === 'critical' || blocker.severity === 'high' ? 'destructive' : 'secondary'} className="capitalize font-bold border-0 shadow-sm">
                              {blocker.severity}
                            </Badge>
                          </td>
                          <td className="px-6 py-5 font-mono text-muted-foreground">
                            {blocker.age_days}d
                          </td>
                          <td className="px-6 py-5 text-muted-foreground whitespace-nowrap">
                            {blocker.created_at ? format(parseISO(blocker.created_at), "MMM d, yyyy") : "Unknown"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </motion.div>
          )}
        </motion.div>
      )}
    </motion.div>
  )
}

function AnalysisStep({ label, active, done }: { label: string, active: boolean, done: boolean }) {
  return (
    <div className={`flex items-center gap-4 transition-all duration-500 ${active ? 'opacity-100 translate-x-0' : 'opacity-30 -translate-x-4'}`}>
      <div className={`w-6 h-6 rounded-full flex items-center justify-center border-2 transition-colors duration-500 ${done ? 'bg-primary border-primary text-white shadow-[0_0_10px_currentColor]' : active ? 'border-primary text-primary' : 'border-muted text-muted'}`}>
        {done ? <Check className="w-4 h-4 font-bold" /> : <ChevronRight className="w-4 h-4" />}
      </div>
      <span className={`font-bold tracking-wide uppercase text-sm ${active ? 'text-foreground' : 'text-muted-foreground'}`}>{label}</span>
    </div>
  )
}

function Check({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  )
}

function SignalCard({ name, signalKey, projectId, icon, data }: { name: string, signalKey: string, projectId: number, icon: React.ReactNode, data?: any }) {
  const [isExpanded, setIsExpanded] = React.useState(false)
  const [explanation, setExplanation] = React.useState<string | null>(null)
  const [isLoadingExplanation, setIsLoadingExplanation] = React.useState(false)

  const handleToggleExplanation = async () => {
    if (isExpanded) {
      setIsExpanded(false)
      return
    }
    setIsExpanded(true)
    if (explanation) return // Already loaded
    
    setIsLoadingExplanation(true)
    try {
      const result = await api.getSignalExplanation(projectId, signalKey)
      setExplanation(result.explanation)
    } catch (err) {
      setExplanation("Unable to generate explanation. The LLM may be temporarily unavailable.")
    } finally {
      setIsLoadingExplanation(false)
    }
  }

  if (!data || !data.available) {
    return (
      <Card className="opacity-60 bg-black/20 border-dashed border-white/10 rounded-3xl">
        <CardHeader className="pb-2 flex flex-row items-center justify-between">
          <CardTitle className="text-lg font-bold flex items-center gap-3">
            <span className="p-2 rounded-xl bg-white/5 text-muted-foreground">{icon}</span>
            {name}
          </CardTitle>
          <Badge variant="outline" className="bg-black/50 border-white/10">Unavailable</Badge>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground/70">{data?.reason || "Data missing or columns could not be mapped."}</p>
        </CardContent>
      </Card>
    )
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return "bg-rag-green"
    if (score >= 60) return "bg-rag-amber"
    return "bg-rag-red"
  }
  const getTextColor = (score: number) => {
    if (score >= 80) return "text-rag-green"
    if (score >= 60) return "text-rag-amber"
    return "text-rag-red"
  }
  const getBorderColor = (score: number) => {
    if (score >= 80) return "border-rag-green/20"
    if (score >= 60) return "border-rag-amber/20"
    return "border-rag-red/20"
  }

  // Format detail values nicely
  const formatDetailValue = (key: string, value: any): string => {
    if (value === null || value === undefined) return 'N/A'
    if (typeof value === 'number') {
      if (key.includes('pct') || key.includes('rate')) return `${value}%`
      if (key.includes('cpi') || key.includes('spi')) return value.toFixed(3)
      if (key.includes('budget') || key.includes('cost') || key.includes('value')) {
        return value.toLocaleString(undefined, { maximumFractionDigits: 0 })
      }
      return String(value)
    }
    if (typeof value === 'boolean') return value ? 'Yes' : 'No'
    return String(value)
  }

  return (
    <Card className={`bg-card/40 backdrop-blur-xl border-white/5 hover:${getBorderColor(data.score)} transition-colors duration-300 rounded-3xl overflow-hidden group`}>
      <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0 relative z-10 bg-black/20">
        <CardTitle className="text-lg font-bold flex items-center gap-3 tracking-wide">
          <span className="p-2 rounded-xl bg-primary/10 text-primary shadow-inner">{icon}</span>
          {name}
        </CardTitle>
        <div className={`text-2xl font-black flex items-center gap-2 ${getTextColor(data.score)} drop-shadow-sm`}>
          {data.score.toFixed(0)}
          <div className={`w-3 h-3 rounded-full ${getScoreColor(data.score)} shadow-[0_0_10px_currentColor]`} />
        </div>
      </CardHeader>
      
      <CardContent className="pt-6">
        <div className="h-2 w-full bg-black/40 rounded-full overflow-hidden shadow-inner mb-6">
          <motion.div 
            initial={{ width: 0 }}
            animate={{ width: `${data.score}%` }}
            transition={{ duration: 1.5, ease: "easeOut", delay: 0.3 }}
            className={`h-full ${getScoreColor(data.score)}`}
          />
        </div>
        
        <p className="text-sm text-foreground/90 font-medium leading-relaxed bg-black/30 p-4 rounded-2xl border border-white/5 shadow-inner">
          {data.reason}
        </p>
        
        {/* All detail metrics */}
        <div className="mt-4 flex flex-wrap gap-2">
          {Object.entries(data.details).map(([k, v]) => {
            if (typeof v === 'object' || k === 'reason') return null;
            return (
              <Badge key={k} variant="secondary" className="text-xs bg-black/40 border-white/10 font-medium tracking-wide shadow-sm px-2.5 py-1">
                <span className="text-muted-foreground mr-1.5 uppercase">{k.replace(/_/g, ' ')}:</span>
                <span className="text-foreground">{formatDetailValue(k, v)}</span>
              </Badge>
            )
          })}
        </div>

        {/* Expandable LLM Explanation Dropdown */}
        <div className="mt-4">
          <button
            onClick={handleToggleExplanation}
            className="w-full flex items-center justify-between gap-2 px-4 py-3 rounded-2xl bg-primary/5 hover:bg-primary/10 border border-primary/10 hover:border-primary/20 transition-all duration-300 text-sm font-bold text-primary group/explain"
          >
            <span className="flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              Why this score?
            </span>
            <motion.div animate={{ rotate: isExpanded ? 180 : 0 }} transition={{ duration: 0.3 }}>
              <ChevronDown className="w-4 h-4" />
            </motion.div>
          </button>
          
          <AnimatePresence>
            {isExpanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.4, ease: "easeInOut" }}
                className="overflow-hidden"
              >
                <div className="mt-3 p-4 bg-black/30 rounded-2xl border border-primary/10 shadow-inner">
                  {isLoadingExplanation ? (
                    <div className="flex items-center gap-3 py-4 justify-center text-muted-foreground">
                      <Loader2 className="w-5 h-5 animate-spin text-primary" />
                      <span className="text-sm font-medium animate-pulse">AI is analyzing this signal...</span>
                    </div>
                  ) : (
                    <p className="text-sm text-foreground/85 leading-relaxed font-medium whitespace-pre-line">
                      {explanation?.replace(/\*\*/g, '')}
                    </p>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </CardContent>
    </Card>
  )
}
