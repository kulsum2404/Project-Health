import React, { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Activity, LayoutDashboard, PlusCircle } from "lucide-react"
import { api, type Project } from "@/api/client"
import { RagCard } from "@/components/RagCard"
import { UploadDialog } from "@/components/UploadDialog"
import { MonthlyReportButton } from "@/components/MonthlyReportButton"
import type { Variants } from "framer-motion"
import { motion, AnimatePresence } from "framer-motion"
import { Button } from "@/components/ui/button"
import { PortfolioComparisonChart } from "@/components/PortfolioComparisonChart"
import type { Snapshot } from "@/api/client"

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
}

const itemVariants: Variants = {
  hidden: { y: 20, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: {
      type: "spring",
      stiffness: 100,
      damping: 15,
    },
  },
}

export function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([])
  const [history, setHistory] = useState<Record<number, Snapshot[]>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showSplash, setShowSplash] = useState(true)
  const [splashText, setSplashText] = useState("Loading Workspace...")

  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })

  useEffect(() => {
    const textTimer1 = setTimeout(() => setSplashText("Analyzing Portfolio Data..."), 1500)
    const textTimer2 = setTimeout(() => setSplashText("Generating Insights..."), 3000)
    const timer = setTimeout(() => setShowSplash(false), 4500)
    
    return () => {
      clearTimeout(textTimer1)
      clearTimeout(textTimer2)
      clearTimeout(timer)
    }
  }, [])

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePos({ 
        x: (e.clientX / window.innerWidth - 0.5) * 20, 
        y: (e.clientY / window.innerHeight - 0.5) * 20 
      })
    }
    if (showSplash) {
      window.addEventListener('mousemove', handleMouseMove)
    }
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [showSplash])

  const fetchProjects = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [projData, histData] = await Promise.all([
        api.getProjects(),
        api.getPortfolioHistory()
      ])
      setProjects(projData)
      setHistory(histData)
    } catch (err: any) {
      setError(err.message || "Failed to load projects")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchProjects()
  }, [])

  const handleUploadSuccess = (projectId: number) => {
    fetchProjects()
  }

  const total = projects.length
  const analyzed = projects.filter(p => p.latest_rag_status !== null)
  const green = analyzed.filter(p => p.latest_rag_status === "green").length
  const amber = analyzed.filter(p => p.latest_rag_status === "amber").length
  const red = analyzed.filter(p => p.latest_rag_status === "red").length

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.4 }}
      className="container mx-auto py-8 px-4 max-w-7xl relative z-10"
    >
      <AnimatePresence>
        {showSplash && (
          <motion.div
            initial={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 1.1, filter: "blur(20px)" }}
            transition={{ duration: 1, ease: "easeInOut" }}
            onClick={() => setShowSplash(false)}
            className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#030712] overflow-hidden cursor-pointer"
          >
            {/* Animated Background Orbs with Parallax */}
            <motion.div 
              animate={{ 
                x: -mousePos.x * 2,
                y: -mousePos.y * 2,
                scale: [1, 1.2, 1],
                opacity: [0.3, 0.5, 0.3],
                rotate: [0, 90, 0]
              }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
              className="absolute -top-1/4 -left-1/4 w-[800px] h-[800px] bg-indigo-600/20 rounded-full blur-[120px] pointer-events-none" 
            />
            <motion.div 
              animate={{ 
                x: mousePos.x * 2,
                y: mousePos.y * 2,
                scale: [1, 1.5, 1],
                opacity: [0.2, 0.4, 0.2],
                rotate: [0, -90, 0]
              }}
              transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
              className="absolute -bottom-1/4 -right-1/4 w-[600px] h-[600px] bg-purple-600/20 rounded-full blur-[100px] pointer-events-none" 
            />

            <motion.div
              initial={{ scale: 0.8, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              transition={{ duration: 1, ease: "easeOut", delay: 0.2 }}
              className="flex flex-col items-center justify-center relative z-10 pointer-events-none"
            >
              <div className="relative">
                {/* Outer rotating ring */}
                <motion.div 
                  animate={{ rotate: 360 }}
                  transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                  className="absolute -inset-4 rounded-full border-t-2 border-r-2 border-primary/50 opacity-50"
                />
                <motion.div 
                  animate={{ rotate: -360 }}
                  transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                  className="absolute -inset-8 rounded-full border-b-2 border-l-2 border-indigo-500/30 opacity-40"
                />
                
                <div className="w-32 h-32 rounded-3xl bg-primary/10 flex items-center justify-center mb-10 shadow-[0_0_80px_rgba(99,102,241,0.2)] border border-primary/20 relative overflow-hidden backdrop-blur-xl">
                  <div className="absolute inset-0 bg-gradient-to-tr from-primary/30 to-transparent animate-pulse" />
                  <Activity className="w-16 h-16 text-primary relative z-10" />
                </div>
              </div>
              
              <h1 className="text-6xl font-black tracking-tighter mb-6 text-transparent bg-clip-text bg-gradient-to-r from-white via-indigo-200 to-white/60 drop-shadow-lg">
                Project Health Agent
              </h1>
              
              <div className="flex flex-col items-center gap-4 w-80">
                <div className="h-1.5 w-full bg-white/10 overflow-hidden rounded-full shadow-inner relative">
                  <motion.div 
                    initial={{ width: "0%" }}
                    animate={{ width: "100%" }}
                    transition={{ duration: 4.5, ease: "linear" }}
                    className="h-full bg-primary shadow-[0_0_10px_currentColor]"
                  />
                </div>
                <motion.p 
                  key={splashText}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-sm font-bold uppercase tracking-[0.2em] text-indigo-300/80 animate-pulse"
                >
                  {splashText}
                </motion.p>
              </div>

              <motion.p 
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.5 }}
                transition={{ delay: 2, duration: 1 }}
                className="absolute -bottom-24 text-xs font-semibold tracking-wider text-white/50 uppercase"
              >
                Click anywhere to skip
              </motion.p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 gap-4">
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <h1 className="text-4xl font-black tracking-tight flex items-center gap-3 drop-shadow-md">
            <div className="p-3 bg-indigo-500/10 rounded-xl text-indigo-400 border border-indigo-500/20 shadow-[0_0_15px_rgba(99,102,241,0.2)]">
              <LayoutDashboard className="w-7 h-7" />
            </div>
            Portfolio Dashboard
          </h1>
          <p className="text-muted-foreground mt-3 text-lg font-medium">
            AI-powered health monitoring and RAG classification engine
          </p>
        </motion.div>
        
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="flex items-center gap-4"
        >
          <MonthlyReportButton />
          <UploadDialog onUploadSuccess={handleUploadSuccess} />
        </motion.div>
      </div>

      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12"
      >
        <StatCard title="Total Projects" value={total} icon={<Activity className="w-5 h-5" />} />
        <StatCard title="Green Status" value={green} color="text-rag-green" bg="bg-rag-green/10" border="border-rag-green/20" glow="shadow-[0_0_15px_rgba(16,185,129,0.1)]" />
        <StatCard title="Amber Status" value={amber} color="text-rag-amber" bg="bg-rag-amber/10" border="border-rag-amber/20" glow="shadow-[0_0_15px_rgba(245,158,11,0.1)]" />
        <StatCard title="Red Status" value={red} color="text-rag-red" bg="bg-rag-red/10" border="border-rag-red/20" glow="shadow-[0_0_15px_rgba(244,63,94,0.1)]" />
      </motion.div>

      {!isLoading && !error && projects.length > 0 && (
        <motion.div variants={itemVariants} initial="hidden" animate="visible">
          <PortfolioComparisonChart history={history} projects={projects} />
        </motion.div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map(i => (
            <motion.div 
              key={i} 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.1 }}
              className="h-72 rounded-2xl border border-white/5 bg-card/30 backdrop-blur-xl animate-pulse" 
            />
          ))}
        </div>
      ) : error ? (
        <motion.div 
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="p-8 text-center text-destructive bg-destructive/10 rounded-2xl border border-destructive/20 backdrop-blur-md shadow-lg"
        >
          <p className="font-bold text-xl">Failed to load dashboard</p>
          <p className="text-sm mt-2 opacity-80">{error}</p>
          <Button variant="outline" className="mt-6 border-destructive/50 hover:bg-destructive/20" onClick={fetchProjects}>Retry Connection</Button>
        </motion.div>
      ) : projects.length === 0 ? (
        <motion.div 
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="flex flex-col items-center justify-center p-16 text-center border rounded-2xl bg-card/40 backdrop-blur-xl border-dashed border-white/10 shadow-2xl"
        >
          <motion.div 
            animate={{ y: [0, -10, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
            className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mb-6 shadow-[0_0_30px_rgba(255,255,255,0.05)]"
          >
            <PlusCircle className="w-10 h-10 text-primary/70" />
          </motion.div>
          <h3 className="text-2xl font-bold tracking-tight">No projects found</h3>
          <p className="text-muted-foreground mt-3 max-w-md text-lg">
            Upload your first project plan spreadsheet to start analyzing health metrics with AI.
          </p>
          <div className="mt-8">
            <UploadDialog onUploadSuccess={handleUploadSuccess} />
          </div>
        </motion.div>
      ) : (
        <motion.div 
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="grid grid-cols-1 md:grid-cols-2 gap-8"
        >
          {projects.map(project => (
            <motion.div key={project.id} variants={itemVariants}>
              <Link to={`/projects/${project.id}`} className="block h-full group/link">
                <RagCard project={project} onUpdate={fetchProjects} />
              </Link>
            </motion.div>
          ))}
        </motion.div>
      )}
    </motion.div>
  )
}

function StatCard({ title, value, color = "text-foreground", bg = "bg-primary/10", border = "border-white/5", glow = "", icon }: { title: string, value: number, color?: string, bg?: string, border?: string, glow?: string, icon?: React.ReactNode }) {
  return (
    <motion.div 
      variants={itemVariants}
      whileHover={{ y: -5, scale: 1.02 }}
      className={`bg-card/40 backdrop-blur-xl border ${border} rounded-2xl p-6 flex items-center gap-5 ${glow} transition-all duration-300`}
    >
      <div className={`p-4 rounded-xl ${bg} ${color} shadow-inner`}>
        {icon || <span className="font-black text-2xl leading-none">{value}</span>}
      </div>
      <div>
        <p className="text-sm text-muted-foreground font-semibold uppercase tracking-wider">{title}</p>
        {icon && <h3 className={`text-3xl font-black mt-1 ${color} drop-shadow-sm`}>{value}</h3>}
      </div>
    </motion.div>
  )
}
