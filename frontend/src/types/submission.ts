export type SubmissionStatus = 'in_progress' | 'evaluating' | 'completed' | 'cancelled'

export interface Answer {
  id: string
  submission_id: string
  question_id: string
  student_answer?: string
  annotation_data?: any
  score?: number
  feedback?: string
  created_at: string
  updated_at: string
}

export interface Submission {
  id: string
  student_id: string
  variant_id: string
  test_id?: string
  test_title?: string
  status: SubmissionStatus
  started_at: string
  submitted_at?: string
  completed_at?: string
  is_hidden: boolean
  result?: {
    total_score: number
    max_score: number
    percentage: number
    grade?: string
    feedback?: string
  }
  answers?: Answer[]
}
