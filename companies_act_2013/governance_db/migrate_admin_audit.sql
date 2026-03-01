-- Run this on existing DB if schema.sql was applied before admin_audit_log existed
CREATE TABLE IF NOT EXISTS admin_audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  action TEXT NOT NULL CHECK (action IN ('CREATE', 'UPDATE', 'DELETE', 'INGEST', 'VISION_UPLOADED', 'VISION_EXTRACTED')),
  document_id TEXT,
  document_type TEXT,
  performed_by TEXT DEFAULT 'admin',
  performed_at TIMESTAMP DEFAULT now(),
  details TEXT,
  status TEXT NOT NULL CHECK (status IN ('SUCCESS', 'FAILED', 'PENDING', 'PENDING_APPROVAL', 'REJECTED', 'PROCESSING')),
  file_path TEXT,
  extracted_data JSONB,
  batch_id UUID,
  vision_model TEXT,
  created_at TIMESTAMP DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_admin_audit_status ON admin_audit_log(status);
CREATE INDEX IF NOT EXISTS idx_admin_audit_batch ON admin_audit_log(batch_id);
CREATE INDEX IF NOT EXISTS idx_admin_audit_performed_at ON admin_audit_log(performed_at DESC);
