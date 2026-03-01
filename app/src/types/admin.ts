// Admin Types - Based on governance_db schema.sql

export type DocumentType =
  | 'act'
  | 'rule'
  | 'regulation'
  | 'order'
  | 'notification'
  | 'circular'
  | 'sop'
  | 'form'
  | 'guideline'
  | 'practice_note'
  | 'commentary'
  | 'textbook'
  | 'qa_book'
  | 'schedule'
  | 'register'
  | 'return'
  | 'qa'
  | 'other';

export type AuthorityLevel =
  | 'statutory'
  | 'interpretive'
  | 'procedural'
  | 'commentary';

export type LifecycleStatus = 'DRAFT' | 'ACTIVE' | 'RETIRED';

export type RetrievalPriority = '1' | '2' | '3' | '4';

export type InputType = 'text' | 'pdf';

// Ingestion mode: manual (form) vs vision (batch + AI extraction)
export type IngestionMode = 'manual' | 'vision';

// Vision model options for document extraction
export type VisionModelOption = 'ollama_qwen3_vl' | 'gemini_flash';
export const VISION_MODEL_OPTIONS: { value: VisionModelOption; label: string }[] = [
  { value: 'ollama_qwen3_vl', label: 'Ollama - qwen3-vl:235b-cloud' },
  { value: 'gemini_flash', label: 'Gemini 3.0 Flash' },
];

// Binding document types (belong to Companies Act sections)
export const BINDING_DOCUMENT_TYPES: DocumentType[] = [
  'act',
  'rule',
  'notification',
  'form',
  'schedule',
  'return',
  'circular',
  'order',
  'regulation',
  'register',
];

// Non-binding document types
export const NON_BINDING_DOCUMENT_TYPES: DocumentType[] = [
  'sop',
  'guideline',
  'practice_note',
  'commentary',
  'textbook',
  'qa_book',
  'qa',
  'other',
];

export type CopyrightStatus = 'copyrighted' | 'public_domain';

export interface IngestionFormData {
  // Document Classification
  documentType: DocumentType;
  isBinding: boolean;
  section?: string; // Companies Act section (e.g., "001", "042")

  // Content Input
  inputType: InputType;
  textContent?: string;
  pdfFile?: File;

  // Temporal Information
  dateIssued: string; // ISO date string
  effectiveDateFrom?: string;
  effectiveDateTo?: string;

  // Metadata
  complianceArea: string;
  documentLanguage: string;
  title?: string;

  // Administrative
  notificationNumber?: string;
  issuedBy?: string;

  // Copyright Attribution
  copyrightStatus?: CopyrightStatus;
  copyrightAttribution?: string; // e.g., "Courtesy by [Publisher Name]" or "General Public"
}

export type AuditAction = 'CREATE' | 'UPDATE' | 'DELETE' | 'INGEST' | 'VISION_UPLOADED' | 'VISION_EXTRACTED';
export type AuditStatus = 'SUCCESS' | 'FAILED' | 'PENDING' | 'PENDING_APPROVAL' | 'REJECTED' | 'PROCESSING' | 'APPROVED';

export interface AuditLogEntry {
  id: string;
  action: AuditAction;
  documentId: string;
  documentType: DocumentType;
  performedBy: string;
  performedAt: string;
  details: string;
  status: AuditStatus;
  /** Path in uploads folder (vision flow); set when awaiting approval */
  filePath?: string;
  /** Extracted metadata from vision (same shape as IngestionFormData); for preview/edit */
  extractedData?: Partial<IngestionFormData>;
  /** Batch id to group batch-uploaded documents */
  batchId?: string;
  /** Vision model used for extraction */
  visionModel?: VisionModelOption;
}

export interface SystemNotification {
  id: string;
  type: 'INFO' | 'WARNING' | 'ERROR' | 'SUCCESS';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}

export interface SystemHealthMetrics {
  databaseStatus: 'healthy' | 'degraded' | 'down';
  embeddingServiceStatus: 'healthy' | 'degraded' | 'down';
  apiLatency: number;
  totalDocuments: number;
  totalChunks: number;
  lastIngestionTime?: string;
  diskUsage: number;
  memoryUsage: number;
}

// Available sections for the Companies Act 2013
export const COMPANIES_ACT_SECTIONS = Array.from({ length: 470 }, (_, i) =>
  String(i + 1).padStart(3, '0')
);

export const DOCUMENT_LANGUAGES = [
  'English',
  'Hindi',
  'Bengali',
  'Telugu',
  'Marathi',
  'Tamil',
  'Gujarati',
  'Kannada',
  'Malayalam',
  'Odia',
  'Punjabi',
  'Assamese',
  'Other',
];

export const COMPLIANCE_AREAS = [
  'Corporate Governance',
  'Financial Reporting',
  'Secretarial Compliance',
  'Board Meetings',
  'Annual Filings',
  'Share Capital',
  'Directors',
  'Auditors',
  'Accounts',
  'Dividends',
  'Mergers & Acquisitions',
  'Winding Up',
  'NCLT Matters',
  'CSR',
  'Related Party Transactions',
  'Loans & Investments',
  'Registers & Records',
  'Other',
];
