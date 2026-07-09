import React from "react"
import { Link } from "react-router-dom"
import { format } from "date-fns"
import { ArrowRight, AlertTriangle, CheckCircle, Clock, Edit2, Check as CheckIcon, X, Trash2 } from "lucide-react"
import { motion } from "framer-motion"

import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "./ui/card"
import { Badge } from "./ui/badge"
import { Input } from "./ui/input"
import { Button } from "./ui/button"
import { api, type Project } from "@/api/client"

interface RagCardProps {
  project: Project
  onUpdate?: () => void
}

export function RagCard({ project, onUpdate }: RagCardProps) {
  const [isEditing, setIsEditing] = React.useState(false)
  const [isDeleting, setIsDeleting] = React.useState(false)
  const [isAnalyzing, setIsAnalyzing] = React.useState(false)
  const [editedName, setEditedName] = React.useState(project.name)
  const [currentName, setCurrentName] = React.useState(project.name)
  
  const isAnalyzed = project.latest_rag_status !== null
  const status = project.latest_rag_status || "amber"

  const handleRename = async (e: React.MouseEvent | React.KeyboardEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!editedName.trim() || editedName === currentName) {
      setIsEditing(false)
      return
    }
    
    try {
      await api.updateProject(project.id, { name: editedName })
      setCurrentName(editedName)
      setIsEditing(false)
    } catch (err) {
      console.error("Failed to rename project", err)
    }
  }
  
  const handleDelete = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!confirm("Are you sure you want to delete this project?")) return
    
    setIsDeleting(true)
    try {
      await api.deleteProject(project.id)
      if (onUpdate) onUpdate()
      else window.location.reload()
    } catch (err) {
      console.error("Failed to delete project", err)
      setIsDeleting(false)
    }
  }

  const handleAnalyze = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsAnalyzing(true)
    try {
      await api.analyzeProject(project.id)
      if (onUpdate) onUpdate()
    } catch (err) {
      console.error("Analysis failed", err)
    } finally {
      setIsAnalyzing(false)
    }
  }
  
  const statusColors = {
    red: "bg-rag-red text-white",
    amber: "bg-rag-amber text-black",
    green: "bg-rag-green text-white",
  }
  
  const borderColors = {
    red: "group-hover:border-rag-red/50 shadow-[0_0_20px_rgba(244,63,94,0)] group-hover:shadow-[0_0_20px_rgba(244,63,94,0.15)]",
    amber: "group-hover:border-rag-amber/50 shadow-[0_0_20px_rgba(245,158,11,0)] group-hover:shadow-[0_0_20px_rgba(245,158,11,0.15)]",
    green: "group-hover:border-rag-green/50 shadow-[0_0_20px_rgba(16,185,129,0)] group-hover:shadow-[0_0_20px_rgba(16,185,129,0.15)]",
  }

  const barColors = {
    red: "bg-rag-red",
    amber: "bg-rag-amber",
    green: "bg-rag-green",
  }
  
  const StatusIcon = {
    red: AlertTriangle,
    amber: Clock,
    green: CheckCircle,
  }[status]

  const bgColors = {
    red: "bg-rag-red/10 hover:bg-rag-red/15",
    amber: "bg-rag-amber/10 hover:bg-rag-amber/15",
    green: "bg-rag-green/10 hover:bg-rag-green/15",
  }

  return (
    <Card className={`flex flex-col group relative overflow-hidden transition-all duration-500 backdrop-blur-xl border border-white/5 ${isAnalyzed ? `${borderColors[status]} ${bgColors[status]}` : 'bg-card/40 hover:border-white/20'}`}>
      {/* Top color bar with glow */}
      <div className="absolute top-0 left-0 right-0 h-1 z-10 opacity-70">
        <div className={`h-full w-full ${isAnalyzed ? statusColors[status] : 'bg-muted'} shadow-[0_0_10px_currentColor]`} />
      </div>
      
      <CardHeader className="pb-3 pt-6 relative z-20">
        <div className="flex justify-between items-start gap-4">
          {isEditing ? (
            <div className="flex items-center gap-1 w-full" onClick={e => e.stopPropagation()}>
              <Input 
                value={editedName}
                onChange={(e) => setEditedName(e.target.value)}
                className="h-8 text-sm bg-black/40 border-white/20 px-2"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleRename(e)
                  if (e.key === 'Escape') {
                    setIsEditing(false)
                    setEditedName(currentName)
                  }
                }}
              />
              <Button size="icon" variant="ghost" onClick={handleRename} className="h-8 w-8 text-green-500 hover:text-green-400 hover:bg-green-500/10 shrink-0">
                <CheckIcon className="w-4 h-4" />
              </Button>
              <Button size="icon" variant="ghost" onClick={(e) => { e.stopPropagation(); setIsEditing(false); setEditedName(currentName) }} className="h-8 w-8 text-muted-foreground hover:text-foreground shrink-0">
                <X className="w-4 h-4" />
              </Button>
            </div>
          ) : (
            <CardTitle className="text-xl line-clamp-1 group-hover:text-primary transition-colors drop-shadow-sm font-bold flex items-center gap-2 group/title">
              {currentName}
              <div className="flex items-center gap-1 opacity-0 group-hover/title:opacity-100 transition-opacity">
                <Button size="icon" variant="ghost" onClick={(e) => { e.preventDefault(); e.stopPropagation(); setIsEditing(true); }} className="w-6 h-6 rounded-full bg-white/5 shrink-0">
                  <Edit2 className="w-3 h-3 text-muted-foreground hover:text-foreground" />
                </Button>
                <Button size="icon" variant="ghost" disabled={isDeleting} onClick={handleDelete} className="w-6 h-6 rounded-full bg-white/5 shrink-0 hover:bg-destructive/20">
                  <Trash2 className="w-3 h-3 text-destructive/70 hover:text-destructive" />
                </Button>
              </div>
            </CardTitle>
          )}
          {isAnalyzed && (
            <Badge variant={status} className="uppercase flex items-center gap-1.5 px-3 py-1 shadow-sm font-bold tracking-wider text-[10px]">
              <StatusIcon className="w-3.5 h-3.5" />
              {status}
            </Badge>
          )}
          {!isAnalyzed && <Badge variant="outline" className="text-xs bg-black/20 backdrop-blur-md">Unanalyzed</Badge>}
        </div>
        <p className="text-sm text-muted-foreground/80 line-clamp-2 mt-2 font-medium leading-relaxed">
          {project.description}
        </p>
        
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
          <div className="flex flex-col gap-1">
            <span className="font-semibold uppercase tracking-wider text-[10px]">Manager</span>
            <span className="text-foreground truncate">{project.manager_name || 'Unassigned'}</span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="font-semibold uppercase tracking-wider text-[10px]">Timeline</span>
            <span className="text-foreground truncate">
              {project.start_date ? format(new Date(project.start_date), 'MMM d, yy') : 'N/A'} - {project.end_date ? format(new Date(project.end_date), 'MMM d, yy') : 'N/A'}
            </span>
          </div>
        </div>
        
        {isAnalyzed && project.latest_reasoning && (
          <div className="mt-3 text-xs bg-black/20 p-2 rounded-md border border-white/5">
            <span className="font-semibold text-primary block mb-1">Analysis</span>
            <p className="text-muted-foreground line-clamp-2">{project.latest_reasoning}</p>
          </div>
        )}
      </CardHeader>
      
      <CardContent className="flex-grow relative z-20">
        {isAnalyzed ? (
          <div className="space-y-5 mt-2">
            <div>
              <div className="flex justify-between text-xs mb-2 font-bold uppercase tracking-wider">
                <span className="text-muted-foreground">Health Score</span>
                <span className={barColors[status].replace('bg-', 'text-')}>{project.latest_score?.toFixed(0)}/100</span>
              </div>
              <div className="h-2 w-full bg-black/40 rounded-full overflow-hidden shadow-inner">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${project.latest_score || 0}%` }}
                  transition={{ duration: 1.5, ease: "easeOut", delay: 0.2 }}
                  className={`h-full ${barColors[status]}`}
                />
              </div>
            </div>
            
            <div>
              <div className="flex justify-between text-xs mb-2 font-bold uppercase tracking-wider">
                <span className="text-muted-foreground flex items-center gap-1">
                  Data Confidence
                </span>
                <span>{((project.latest_confidence || 0) * 100).toFixed(0)}%</span>
              </div>
              <div className="h-1.5 w-full bg-black/40 rounded-full overflow-hidden shadow-inner">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${(project.latest_confidence || 0) * 100}%` }}
                  transition={{ duration: 1.5, ease: "easeOut", delay: 0.4 }}
                  className="h-full bg-primary/70"
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-sm text-muted-foreground mt-4 italic bg-black/20 rounded-xl py-6 border border-dashed border-white/10 backdrop-blur-sm">
            <span className="opacity-70">Run analysis to generate</span>
            <span className="opacity-70">RAG status</span>
          </div>
        )}
      </CardContent>
      
      <CardFooter className="border-t border-white/5 pt-4 bg-black/20 flex items-center justify-between relative z-20">
        <span className="text-xs text-muted-foreground/60 font-semibold uppercase tracking-wider hidden sm:inline-block">
          {isAnalyzed ? `Updated ${format(new Date(project.updated_at), "MMM d")}` : "Needs analysis"}
        </span>
        <div className="flex items-center gap-3 w-full sm:w-auto justify-between sm:justify-end">
          <Button 
            size="sm" 
            variant="outline" 
            className="h-8 text-xs bg-primary/10 hover:bg-primary/20 text-primary border-primary/20"
            onClick={handleAnalyze}
            disabled={isAnalyzing}
          >
            {isAnalyzing ? (
              <span className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                Analyzing
              </span>
            ) : (
              isAnalyzed ? "Update Analysis" : "Run Analysis"
            )}
          </Button>
          <Link 
            to={`/projects/${project.id}`}
            className="text-sm font-bold text-primary flex items-center gap-1 group-hover:gap-2 transition-all hover:text-white"
          >
            Details
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </CardFooter>
    </Card>
  )
}
