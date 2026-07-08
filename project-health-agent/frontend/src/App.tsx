import React from "react"
import { BrowserRouter as Router, Routes, Route, useLocation } from "react-router-dom"
import { AnimatePresence } from "framer-motion"
import { Dashboard } from "./pages/Dashboard"
import { ProjectDetail } from "./pages/ProjectDetail"
import { AnimatedBackground } from "./components/AnimatedBackground"

function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/projects/:id" element={<ProjectDetail />} />
      </Routes>
    </AnimatePresence>
  );
}

function App() {
  return (
    <Router>
      <AnimatedBackground>
        <div className="min-h-screen font-sans pb-12">
          <header className="border-b border-border/40 bg-background/40 backdrop-blur-xl sticky top-0 z-40">
            <div className="container mx-auto px-4 h-16 flex items-center justify-between">
              <div className="flex items-center gap-2 font-bold tracking-tight text-xl text-primary drop-shadow-sm">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center text-white text-xs font-black shadow-lg shadow-purple-500/20">
                  P
                </div>
                Project Health
              </div>
            </div>
          </header>
          
          <main>
            <AnimatedRoutes />
          </main>
        </div>
      </AnimatedBackground>
    </Router>
  )
}

export default App
