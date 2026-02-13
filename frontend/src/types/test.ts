export type TestStatus = 'draft' | 'published' | 'archived'

export interface TestQuestion {
  id: string
  test_id: string
  question_id: string
  question?: Question
  order: number
}

export interface TestSettings {
  time_limit?: number
  [key: string]: any
}

export interface TestStructureItem {
  topic_id: string
  question_type: QuestionType
  count: number
  difficulty: number
}

export interface Test {
  id: string
  author_id: string
  title: string
  description?: string
  settings: TestSettings
  structure?: TestStructureItem[]
  status: TestStatus
  published_at?: string
  created_at: string
  updated_at: string
  test_questions?: TestQuestion[]
}

export interface TestCreate {
  title: string
  description?: string
  settings?: TestSettings
  structure?: TestStructureItem[]
  questions: Array<{
    question_id: string
    order: number
  }>
}

export interface TestUpdate {
  title?: string
  description?: string
  settings?: TestSettings
  structure?: TestStructureItem[]
  status?: TestStatus
}

export interface TestVariant {
  id: string
  test_id: string
  variant_code: string
  question_order: string[]
  created_at: string
}

export type QuestionType = 'text' | 'image_annotation' | 'choice'

export interface ImageAsset {
  id: string
  filename: string
  storage_path: string
  width: number
  height: number
  file_size: number
  coco_annotations?: any
  presigned_url?: string
}

export interface Topic {
  id: string
  name: string
  description?: string
  created_by: string
  created_at: string
  updated_at: string
}

export interface TopicCreate {
  name: string
  description?: string
}

export interface Question {
  id: string
  author_id: string
  type: QuestionType
  content: string
  topic_id?: string
  difficulty: number
  topic?: Topic
  reference_data?: any
  scoring_criteria?: any
  ai_check_enabled?: boolean
  plagiarism_check_enabled?: boolean
  event_log_check_enabled?: boolean
  image_id?: string
  image?: ImageAsset
  created_at: string
  updated_at: string
}

export interface QuestionCreate {
  type: QuestionType
  content: string
  topic_id?: string
  difficulty: number
  reference_data?: any
  scoring_criteria?: any
  ai_check_enabled?: boolean
  plagiarism_check_enabled?: boolean
  event_log_check_enabled?: boolean
  image_id?: string
}
