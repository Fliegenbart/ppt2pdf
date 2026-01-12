export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface SlideElement {
  id: string;
  element_type: 'text' | 'image' | 'table' | 'chart' | 'shape';
  reading_order: number;
  bounds: BoundingBox;
  text?: string;
  heading_level?: number | null;
  alt_text?: string | null;
  alt_text_generated?: boolean;
  is_decorative?: boolean;
  content_type?: string;
  has_image?: boolean;
  chart_type?: string;
  chart_title?: string;
  chart_summary?: string;
  table_rows?: number;
  table_cols?: number;
  language?: string;
}

export interface Slide {
  slide_number: number;
  title: string | null;
  speaker_notes: string | null;
  reading_order_analyzed: boolean;
  reading_order_confidence: number;
  elements: SlideElement[];
}

export interface PresentationSummary {
  title: string | null;
  author: string | null;
  slide_count: number;
  analyzed: boolean;
  default_language: string | null;
}

export interface Job {
  job_id: string;
  status: 'pending' | 'uploaded' | 'parsing' | 'parsed' | 'analyzing' | 'analyzed' | 'converting' | 'complete' | 'error';
  progress: number;
  current_step: string | null;
  error_message: string | null;
  presentation?: PresentationSummary;
}

export interface AccessibilityIssue {
  issue_type: string;
  severity: 'error' | 'warning' | 'info';
  slide_number: number;
  element_id: string | null;
  message: string;
  suggestion: string | null;
  details?: Record<string, unknown>;
}

export interface AccessibilityReport {
  job_id: string;
  total_slides: number;
  total_elements: number;
  total_images: number;
  images_with_alt_text: number;
  issues: AccessibilityIssue[];
  score: number;
  pdf_ua_ready: boolean;
}

export interface ElementUpdate {
  element_id: string;
  slide_number: number;
  alt_text?: string;
  reading_order?: number;
  is_decorative?: boolean;
  heading_level?: number;
}
