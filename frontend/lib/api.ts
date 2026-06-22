export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8001'

export interface Job {
  id: string
  title: string
  company: string
  source: string
  source_id: string
  jd_text: string
  apply_url?: string
  created_at: string
}

export interface Application {
  id: string
  job_id: string
  user_id: string
  status: 'pending' | 'applied' | 'interview' | 'offer' | 'rejected'
  resume_used?: string
  created_at: string
  updated_at: string
}

export interface MatchReport {
  report_id: string
  match_score: number
  recommendation: string
  priority: string
  strengths: string[]
  gaps: string[]
}

export interface PipelineResult {
  pipeline_status: string
  match_score: number
  priority: string
  application_id?: string
  errors: string[]
}

export const fetcher = (url: string) =>
  fetch(`${API_BASE}${url}`).then(r => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    return r.json()
  })

export async function runPipeline(resumeText: string): Promise<PipelineResult> {
  const resp = await fetch(`${API_BASE}/api/agents/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resume_text: resumeText }),
  })
  if (!resp.ok) throw new Error(`Pipeline failed: ${resp.status}`)
  return resp.json()
}

export async function matchJob(resumeText: string, jdText: string): Promise<MatchReport> {
  const resp = await fetch(`${API_BASE}/api/match`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resume_text: resumeText, jd_text: jdText }),
  })
  if (!resp.ok) throw new Error(`Match failed: ${resp.status}`)
  return resp.json()
}

export interface DailyStat {
  date: string
  jobs: number
  applications: number
  cost: number
}

export interface StatsResponse {
  totals: { jobs: number; applications: number }
  daily: DailyStat[]
  cost_total: number
}

export async function patchApplicationStatus(id: string, status: string): Promise<Application> {
  const resp = await fetch(`${API_BASE}/api/applications/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })
  if (!resp.ok) throw new Error(`Update failed: ${resp.status}`)
  return resp.json()
}
