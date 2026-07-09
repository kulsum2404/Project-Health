// API Client for the Project Health Reporting backend

const API_BASE_URL = "http://localhost:8000/api"

export interface SignalDetails {
  score: number
  available: boolean
  details: Record<string, any>
  reason: string
}

export interface Snapshot {
  id: number
  project_id: number
  created_at: string
  rag_status: "red" | "amber" | "green"
  weighted_score: number
  confidence: number
  schedule_score: number | null
  budget_score: number | null
  milestone_score: number | null
  blocker_score: number | null
  sentiment_score: number | null
  signal_details: Record<string, SignalDetails>
  signals_used: string[]
  signals_skipped: string[]
  reasoning: string
  signal_summaries: Record<string, string>
  source_file: string
  sheet_count: number
  total_tasks: number
}

export interface Project {
  id: number
  name: string
  description: string
  manager_name: string
  start_date: string | null
  end_date: string | null
  schema_mapping: Record<string, string>
  created_at: string
  updated_at: string
  is_active: boolean
  latest_rag_status: "red" | "amber" | "green" | null
  latest_score: number | null
  latest_confidence: number | null
  latest_reasoning: string | null
}

export interface Blocker {
  id: number
  description: string
  severity: string
  created_at: string
  age_days: number
}

export interface ReportResponse {
  project_id: number
  project_name: string
  snapshot: Snapshot
  blockers: Blocker[]
}

export interface MonthlyReport {
  id: number
  created_at: string
  period_start: string
  period_end: string
  portfolio_name: string
  total_projects: number
  green_count: number
  amber_count: number
  red_count: number
  synthesis_data: any
  has_pptx: boolean
}

class ApiClient {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          "Accept": "application/json",
          ...options.headers,
        },
      })
      
      if (!response.ok) {
        let errorData
        try {
          errorData = await response.json()
        } catch {
          errorData = { detail: response.statusText }
        }
        throw new Error(errorData.detail || `API request failed: ${response.status}`)
      }
      
      if (response.status === 204) {
        return undefined as any
      }
      
      return response.json()
    } catch (error) {
      console.error(`API Error (${endpoint}):`, error)
      throw error
    }
  }

  // Project endpoints
  getProjects() {
    return this.request<Project[]>("/projects")
  }

  getProject(id: number) {
    return this.request<Project>(`/projects/${id}`)
  }

  updateProject(id: number, updates: Partial<{name: string, manager_name: string}>) {
    return this.request<Project>(`/projects/${id}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(updates),
    })
  }

  deleteProject(id: number) {
    return this.request<void>(`/projects/${id}`, {
      method: "DELETE",
    })
  }

  uploadProject(file: File) {
    const formData = new FormData()
    formData.append("file", file)
    return this.request<{ project_id: number; message: string; detected_mapping: any }>("/projects/upload", {
      method: "POST",
      body: formData,
    })
  }

  analyzeProject(id: number) {
    return this.request<Snapshot>(`/projects/${id}/analyze`, { method: "POST" })
  }

  // Report endpoints
  getLatestReport(id: number) {
    return this.request<ReportResponse>(`/projects/${id}/report`)
  }

  getProjectHistory(id: number) {
    return this.request<Snapshot[]>(`/projects/${id}/history`)
  }

  getPortfolioHistory() {
    return this.request<Record<number, Snapshot[]>>(`/projects/all/history`)
  }

  getSignalExplanation(projectId: number, signalName: string) {
    return this.request<{ signal_name: string; explanation: string }>(
      `/projects/${projectId}/signal-explanation/${signalName}`
    )
  }

  // Monthly synthesis
  synthesizeMonthly() {
    return this.request<MonthlyReport>("/monthly/synthesize", { method: "POST" })
  }
  
  getMonthlyReports() {
    return this.request<MonthlyReport[]>("/monthly/reports")
  }
  
  getMonthlyReportDownloadUrl(id: number) {
    return `${API_BASE_URL}/monthly/${id}/download`
  }
}

export const api = new ApiClient()
