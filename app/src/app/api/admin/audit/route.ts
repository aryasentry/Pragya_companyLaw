import { NextResponse } from 'next/server';

// Audit log data - will be replaced with database queries
const auditLogs = [
  {
    id: 'audit-001',
    action: 'INGEST',
    documentId: 'DOC-2026-001',
    documentType: 'notification',
    performedBy: 'admin@pragya.in',
    performedAt: '2026-02-01T10:30:00Z',
    details: 'New notification ingested for Section 134',
    status: 'SUCCESS',
  },
  {
    id: 'audit-002',
    action: 'UPDATE',
    documentId: 'DOC-2026-002',
    documentType: 'circular',
    performedBy: 'admin@pragya.in',
    performedAt: '2026-02-01T09:15:00Z',
    details: 'Updated metadata for circular on Annual Returns',
    status: 'SUCCESS',
  },
  {
    id: 'audit-003',
    action: 'INGEST',
    documentId: 'DOC-2026-003',
    documentType: 'rule',
    performedBy: 'admin@pragya.in',
    performedAt: '2026-01-31T16:45:00Z',
    details: 'Attempted to ingest new rule - embedding failed',
    status: 'FAILED',
  },
  {
    id: 'audit-004',
    action: 'CREATE',
    documentId: 'DOC-2026-004',
    documentType: 'qa',
    performedBy: 'content@pragya.in',
    performedAt: '2026-01-31T14:20:00Z',
    details: 'Created new Q&A entry for Director obligations',
    status: 'SUCCESS',
  },
  {
    id: 'audit-005',
    action: 'DELETE',
    documentId: 'DOC-2026-005',
    documentType: 'commentary',
    performedBy: 'admin@pragya.in',
    performedAt: '2026-01-30T11:00:00Z',
    details: 'Removed outdated commentary on Section 185',
    status: 'SUCCESS',
  },
  {
    id: 'audit-006',
    action: 'INGEST',
    documentId: 'DOC-2026-006',
    documentType: 'order',
    performedBy: 'admin@pragya.in',
    performedAt: '2026-01-30T10:00:00Z',
    details: 'Processing order document - awaiting embedding',
    status: 'PENDING',
  },
];

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const action = searchParams.get('action');
  const status = searchParams.get('status');
  const search = searchParams.get('search');
  const page = parseInt(searchParams.get('page') || '1');
  const limit = parseInt(searchParams.get('limit') || '10');

  let filteredLogs = [...auditLogs];

  // Filter by action
  if (action && action !== 'all') {
    filteredLogs = filteredLogs.filter(log => log.action === action);
  }

  // Filter by status
  if (status && status !== 'all') {
    filteredLogs = filteredLogs.filter(log => log.status === status);
  }

  // Search filter
  if (search) {
    const searchLower = search.toLowerCase();
    filteredLogs = filteredLogs.filter(log =>
      log.documentId.toLowerCase().includes(searchLower) ||
      log.details.toLowerCase().includes(searchLower) ||
      log.performedBy.toLowerCase().includes(searchLower)
    );
  }

  // Pagination
  const total = filteredLogs.length;
  const startIndex = (page - 1) * limit;
  const paginatedLogs = filteredLogs.slice(startIndex, startIndex + limit);

  return NextResponse.json({
    success: true,
    data: paginatedLogs,
    pagination: {
      page,
      limit,
      total,
      totalPages: Math.ceil(total / limit),
    },
  });
}
