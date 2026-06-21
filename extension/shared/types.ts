export interface PrefillData {
  name: string;
  email: string;
  phone: string;
  resume_highlights: string[];
  cover_letter: string;
  skills: string[];
}

export interface ExtensionTask {
  task_id: string;
  job_title: string;
  company: string;
  apply_url: string | null;
  application_id: string | null;
  prefill_data: PrefillData;
  status: 'pending' | 'filled' | 'applied' | 'skipped';
  created_at: string;
}

export type CompleteStatus = 'applied' | 'skipped';

export interface CompleteTaskRequest {
  task_id: string;
  status: CompleteStatus;
  note?: string;
}

export const API_BASE = 'http://localhost:8001';
