-- Add PROCESSING status to admin_audit_log (for vision queue)
ALTER TABLE admin_audit_log DROP CONSTRAINT IF EXISTS admin_audit_log_status_check;
ALTER TABLE admin_audit_log ADD CONSTRAINT admin_audit_log_status_check
  CHECK (status IN ('SUCCESS', 'FAILED', 'PENDING', 'PENDING_APPROVAL', 'REJECTED', 'PROCESSING', 'APPROVED'));
