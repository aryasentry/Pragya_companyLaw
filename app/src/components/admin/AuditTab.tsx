'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  FaFilter,
  FaSearch,
  FaDownload,
  FaEye,
  FaCheckCircle,
  FaTimesCircle,
  FaClock,
  FaUpload,
  FaEdit,
  FaTrash,
  FaSync,
} from 'react-icons/fa';
import { AuditLogEntry, IngestionFormData, COMPLIANCE_AREAS, DOCUMENT_LANGUAGES } from '@/types/admin';

const actionIcons: Record<string, React.ReactNode> = {
  INGEST: <FaUpload className="text-blue-500" />,
  CREATE: <FaCheckCircle className="text-green-500" />,
  UPDATE: <FaEdit className="text-amber-500" />,
  DELETE: <FaTrash className="text-red-500" />,
  VISION_UPLOADED: <FaUpload className="text-indigo-500" />,
  VISION_EXTRACTED: <FaUpload className="text-indigo-500" />,
};

const statusStyles: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
  SUCCESS: {
    bg: 'bg-green-100',
    text: 'text-green-700',
    icon: <FaCheckCircle className="text-green-500" />,
  },
  FAILED: {
    bg: 'bg-red-100',
    text: 'text-red-700',
    icon: <FaTimesCircle className="text-red-500" />,
  },
  PENDING: {
    bg: 'bg-amber-100',
    text: 'text-amber-700',
    icon: <FaClock className="text-amber-500" />,
  },
  PENDING_APPROVAL: {
    bg: 'bg-blue-100',
    text: 'text-blue-700',
    icon: <FaEye className="text-blue-500" />,
  },
  REJECTED: {
    bg: 'bg-gray-100',
    text: 'text-gray-700',
    icon: <FaTimesCircle className="text-gray-500" />,
  },
  PROCESSING: {
    bg: 'bg-indigo-100',
    text: 'text-indigo-700',
    icon: <FaSync className="animate-spin text-indigo-500" />,
  },
  APPROVED: {
    bg: 'bg-emerald-100',
    text: 'text-emerald-700',
    icon: <FaCheckCircle className="text-emerald-500" />,
  },
};

interface PaginationInfo {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

export default function AuditTab() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterAction, setFilterAction] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [pagination, setPagination] = useState<PaginationInfo>({
    page: 1,
    limit: 10,
    total: 0,
    totalPages: 0,
  });
  const [previewEntry, setPreviewEntry] = useState<AuditLogEntry | null>(null);
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [editData, setEditData] = useState<Partial<IngestionFormData>>({});
  const [approveError, setApproveError] = useState<string | null>(null);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [retryError, setRetryError] = useState<string | null>(null);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterAction !== 'all') params.set('action', filterAction);
      if (filterStatus !== 'all') params.set('status', filterStatus);
      if (searchQuery) params.set('search', searchQuery);
      params.set('page', pagination.page.toString());
      params.set('limit', pagination.limit.toString());

      const response = await fetch(`/api/admin/audit?${params}`);
      const data = await response.json();

      if (data.success) {
        setLogs(data.data);
        setPagination(data.pagination);
      }
    } catch (error) {
      console.error('Failed to fetch audit logs:', error);
    } finally {
      setLoading(false);
    }
  }, [filterAction, filterStatus, searchQuery, pagination.page, pagination.limit]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const handlePageChange = (newPage: number) => {
    setPagination(prev => ({ ...prev, page: newPage }));
  };

  const openPreview = (log: AuditLogEntry) => {
    setPreviewEntry(log);
    setEditData(log.extractedData || {});
    setApproveError(null);
  };

  const handleApprove = async () => {
    if (!previewEntry) return;
    setApprovingId(previewEntry.id);
    setApproveError(null);
    try {
      const res = await fetch('/api/admin/approve-vision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ auditId: previewEntry.id, metadata: Object.keys(editData).length ? editData : undefined }),
      });
      const data = await res.json();
      if (data.success) {
        setPreviewEntry(null);
        fetchLogs();
      } else {
        setApproveError(data.error || 'Approve failed');
      }
    } catch (e) {
      setApproveError(e instanceof Error ? e.message : 'Request failed');
    } finally {
      setApprovingId(null);
    }
  };

  const handleRetry = async (auditId: string) => {
    setRetryingId(auditId);
    setRetryError(null);
    try {
      const res = await fetch('/api/admin/retry-vision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ auditId }),
      });
      const data = await res.json();
      if (data.success && data.data?.processed) {
        fetchLogs();
      } else {
        setRetryError(data.error || 'Retry failed');
      }
    } catch (e) {
      setRetryError(e instanceof Error ? e.message : 'Retry failed');
    } finally {
      setRetryingId(null);
    }
  };

  const handleReject = async () => {
    if (!previewEntry) return;
    setApprovingId(previewEntry.id);
    try {
      const res = await fetch('/api/admin/reject-vision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ auditId: previewEntry.id }),
      });
      const data = await res.json();
      if (data.success) {
        setPreviewEntry(null);
        fetchLogs();
      }
    } finally {
      setApprovingId(null);
    }
  };

  const statusStyle = (status: string) =>
    statusStyles[status] || { bg: 'bg-gray-100', text: 'text-gray-700', icon: null };
  const actionIcon = (action: string) => actionIcons[action] ?? <FaEdit className="text-gray-500" />;

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Audit Log</h2>
          <p className="text-gray-600">Track all document operations and changes</p>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={fetchLogs}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-50 transition-colors"
          >
            <FaSync className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-50 transition-colors">
            <FaDownload />
            Export Logs
          </button>
        </div>
      </div>

      {retryError && (
        <div className="bg-red-50 text-red-700 px-4 py-2 rounded-lg text-sm flex items-center justify-between">
          {retryError}
          <button onClick={() => setRetryError(null)} className="text-red-500 hover:text-red-700">×</button>
        </div>
      )}
      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search by document ID, user, or details..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
            />
          </div>

          {/* Action Filter */}
          <div className="flex items-center gap-2">
            <FaFilter className="text-gray-400" />
            <select
              value={filterAction}
              onChange={(e) => setFilterAction(e.target.value)}
              className="px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
            >
              <option value="all">All Actions</option>
              <option value="INGEST">Ingest</option>
              <option value="VISION_UPLOADED">Vision Uploaded</option>
              <option value="VISION_EXTRACTED">Vision Extracted</option>
              <option value="CREATE">Create</option>
              <option value="UPDATE">Update</option>
              <option value="DELETE">Delete</option>
            </select>
          </div>

          {/* Status Filter */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
          >
            <option value="all">All Status</option>
            <option value="SUCCESS">Success</option>
            <option value="FAILED">Failed</option>
            <option value="PENDING">Pending</option>
            <option value="PENDING_APPROVAL">Pending Approval</option>
            <option value="PROCESSING">Processing</option>
            <option value="APPROVED">Approved</option>
            <option value="REJECTED">Rejected</option>
          </select>
        </div>
      </div>

      {/* Audit Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center">
            <FaSync className="animate-spin text-2xl text-orange-500 mx-auto mb-2" />
            <p className="text-gray-500">Loading audit logs...</p>
          </div>
        ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Action
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Document
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Details
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  User
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Timestamp
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      {actionIcon(log.action)}
                      <span className="text-sm font-medium text-gray-900">{log.action}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm font-mono text-gray-600">{log.documentId}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 capitalize">
                      {log.documentType.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-gray-600 line-clamp-1">{log.details}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-600">{log.performedBy}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-500">{formatDate(log.performedAt)}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${statusStyle(log.status).bg} ${statusStyle(log.status).text}`}>
                      {statusStyle(log.status).icon}
                      {log.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap flex items-center gap-2">
                    {log.status === 'FAILED' && log.filePath && (
                      <button
                        onClick={() => handleRetry(log.id)}
                        disabled={!!retryingId}
                        className="text-amber-600 hover:text-amber-700 transition-colors disabled:opacity-50"
                        title="Retry vision extraction"
                      >
                        <FaSync className={retryingId === log.id ? 'animate-spin' : ''} />
                      </button>
                    )}
                    <button
                      onClick={() => (log.extractedData || log.status === 'PENDING_APPROVAL') ? openPreview(log) : undefined}
                      className="text-gray-400 hover:text-orange-500 transition-colors disabled:opacity-50"
                      title={log.extractedData ? 'Preview & approve' : 'View'}
                    >
                      <FaEye />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        )}

        {/* Pagination */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
          <span className="text-sm text-gray-600">
            Showing {logs.length} of {pagination.total} entries
          </span>
          <div className="flex items-center gap-2">
            <button 
              onClick={() => handlePageChange(pagination.page - 1)}
              disabled={pagination.page <= 1}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-white transition-colors disabled:opacity-50"
            >
              Previous
            </button>
            {Array.from({ length: Math.min(pagination.totalPages, 5) }, (_, i) => i + 1).map(page => (
              <button
                key={page}
                onClick={() => handlePageChange(page)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
                  page === pagination.page
                    ? 'bg-orange-500 text-white'
                    : 'border border-gray-300 text-gray-600 hover:bg-white'
                }`}
              >
                {page}
              </button>
            ))}
            <button 
              onClick={() => handlePageChange(pagination.page + 1)}
              disabled={pagination.page >= pagination.totalPages}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-white transition-colors disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* Preview modal for vision-extracted entries */}
      {previewEntry && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Preview – {previewEntry.documentType}</h3>
              <button onClick={() => setPreviewEntry(null)} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
            </div>
            <div className="p-6 space-y-4">
              {(previewEntry.extractedData || Object.keys(editData).length > 0) && (
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <label className="text-gray-500 block">Document type</label>
                    <input
                      value={editData.documentType ?? ''}
                      onChange={(e) => setEditData((d) => ({ ...d, documentType: e.target.value as IngestionFormData['documentType'] }))}
                      className="mt-1 w-full px-2 py-1.5 border rounded text-gray-900"
                    />
                  </div>
                  <div>
                    <label className="text-gray-500 block">Section</label>
                    <input
                      value={editData.section ?? ''}
                      onChange={(e) => setEditData((d) => ({ ...d, section: e.target.value }))}
                      className="mt-1 w-full px-2 py-1.5 border rounded text-gray-900"
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="text-gray-500 block">Title</label>
                    <input
                      value={editData.title ?? ''}
                      onChange={(e) => setEditData((d) => ({ ...d, title: e.target.value }))}
                      className="mt-1 w-full px-2 py-1.5 border rounded text-gray-900"
                    />
                  </div>
                  <div>
                    <label className="text-gray-500 block">Date issued</label>
                    <input
                      type="date"
                      value={editData.dateIssued ?? ''}
                      onChange={(e) => setEditData((d) => ({ ...d, dateIssued: e.target.value }))}
                      className="mt-1 w-full px-2 py-1.5 border rounded text-gray-900"
                    />
                  </div>
                  <div>
                    <label className="text-gray-500 block">Compliance area</label>
                    <select
                      value={editData.complianceArea ?? ''}
                      onChange={(e) => setEditData((d) => ({ ...d, complianceArea: e.target.value }))}
                      className="mt-1 w-full px-2 py-1.5 border rounded text-gray-900"
                    >
                      {COMPLIANCE_AREAS.map((a) => (
                        <option key={a} value={a}>{a}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-gray-500 block">Document language</label>
                    <select
                      value={editData.documentLanguage ?? ''}
                      onChange={(e) => setEditData((d) => ({ ...d, documentLanguage: e.target.value }))}
                      className="mt-1 w-full px-2 py-1.5 border rounded text-gray-900"
                    >
                      {DOCUMENT_LANGUAGES.map((l) => (
                        <option key={l} value={l}>{l}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-gray-500 block">Notification number</label>
                    <input
                      value={editData.notificationNumber ?? ''}
                      onChange={(e) => setEditData((d) => ({ ...d, notificationNumber: e.target.value }))}
                      className="mt-1 w-full px-2 py-1.5 border rounded text-gray-900"
                    />
                  </div>
                  <div>
                    <label className="text-gray-500 block">Issued by</label>
                    <input
                      value={editData.issuedBy ?? ''}
                      onChange={(e) => setEditData((d) => ({ ...d, issuedBy: e.target.value }))}
                      className="mt-1 w-full px-2 py-1.5 border rounded text-gray-900"
                    />
                  </div>
                  <div>
                    <label className="text-gray-500 block">Binding</label>
                    <select
                      value={editData.isBinding === true ? 'true' : editData.isBinding === false ? 'false' : ''}
                      onChange={(e) => setEditData((d) => ({ ...d, isBinding: e.target.value === 'true' }))}
                      className="mt-1 w-full px-2 py-1.5 border rounded text-gray-900"
                    >
                      <option value="">—</option>
                      <option value="true">Yes</option>
                      <option value="false">No</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-gray-500 block">Copyright status</label>
                    <input
                      value={editData.copyrightStatus ?? ''}
                      onChange={(e) => setEditData((d) => ({ ...d, copyrightStatus: e.target.value as IngestionFormData['copyrightStatus'] }))}
                      className="mt-1 w-full px-2 py-1.5 border rounded text-gray-900"
                    />
                  </div>
                </div>
              )}
              {!previewEntry.extractedData && Object.keys(editData).length === 0 && (
                <p className="text-gray-500">{previewEntry.details || 'No extracted data'}</p>
              )}
            </div>
            {approveError && (
              <div className="px-6 pb-2 text-sm text-red-600 bg-red-50 p-3 rounded-lg">{approveError}</div>
            )}
            {previewEntry.status === 'PENDING_APPROVAL' && (
              <div className="p-6 border-t border-gray-200 flex gap-3 justify-end">
                <button onClick={handleReject} disabled={!!approvingId} className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50">
                  Reject
                </button>
                <button onClick={handleApprove} disabled={!!approvingId} className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50">
                  {approvingId ? 'Processing...' : 'Approve & ingest'}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
