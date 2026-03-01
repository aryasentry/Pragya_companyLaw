'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import AdminSidebar from '@/components/admin/AdminSidebar';
import IngestionForm from '@/components/admin/IngestionForm';
import PipelineStatus from '@/components/admin/PipelineStatus';
import AuditTab from '@/components/admin/AuditTab';
import NotificationsTab from '@/components/admin/NotificationsTab';
import DashboardTab from '@/components/admin/DashboardTab';
import ChatTab from '@/components/admin/ChatTab';
import DocumentsTab from '@/components/admin/DocumentsTab';
import SettingsTab from '@/components/admin/SettingsTab';
import { IngestionFormData, IngestionMode, VisionModelOption, VISION_MODEL_OPTIONS } from '@/types/admin';
import { FaUpload, FaEye, FaCogs } from 'react-icons/fa';

function AdminPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [ingestionMode, setIngestionMode] = useState<IngestionMode>('manual');
  const [visionModel, setVisionModel] = useState<VisionModelOption>('ollama_qwen3_vl');
  const [batchFiles, setBatchFiles] = useState<File[]>([]);
  const [batchUploading, setBatchUploading] = useState(false);
  const [batchProcessing, setBatchProcessing] = useState(false);
  const [lastBatchId, setLastBatchId] = useState<string | null>(null);
  const [batchError, setBatchError] = useState<string | null>(null);
  const [batchSuccess, setBatchSuccess] = useState<string | null>(null);

  // Initialize tab from URL on mount and when searchParams change
  useEffect(() => {
    const tabFromUrl = searchParams.get('tab');
    if (tabFromUrl) {
      setActiveTab(tabFromUrl);
    }
  }, [searchParams]);

  // Update URL when tab changes
  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    router.push(`/admin?tab=${tab}`, { scroll: false });
  };

  const handleBatchUpload = async () => {
    if (!batchFiles.length) return;
    setBatchUploading(true);
    setBatchError(null);
    setBatchSuccess(null);
    try {
      const formData = new FormData();
      formData.append('visionModel', visionModel);
      batchFiles.forEach((f) => formData.append('files', f));
      const res = await fetch('/api/admin/batch-upload', { method: 'POST', body: formData });
      const result = await res.json();
      if (!result.success) {
        setBatchError(result.error || 'Batch upload failed');
        return;
      }
      if (!result.data?.batchId) {
        setBatchError('No batch ID returned');
        return;
      }
      setLastBatchId(result.data.batchId);
      const fileCount = result.data?.files?.length ?? batchFiles.length;
      const processRes = await fetch('/api/admin/process-vision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ batchId: result.data.batchId }),
      });
      const processResult = await processRes.json();
      if (!processResult.success) {
        setBatchError(processResult.error || 'Vision processing failed');
        return;
      }
      const processed = processResult.data?.processed ?? 0;
      const total = processResult.data?.total ?? 0;
      setBatchSuccess(`Uploaded ${fileCount} file(s). Processed ${processed}/${total} with vision. Check Audit tab to preview and approve.`);
      setBatchFiles([]);
      setActiveTab('audit');
    } catch (e) {
      setBatchError(e instanceof Error ? e.message : 'Upload or process failed');
      console.error(e);
    } finally {
      setBatchUploading(false);
    }
  };

  const handleBatchFilesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const added = e.target.files ? Array.from(e.target.files) : [];
    if (added.length) setBatchFiles((prev) => [...prev, ...added]);
    e.target.value = '';
  };

  const handleIngestionSubmit = async (data: IngestionFormData) => {
    setIsSubmitting(true);

    try {
      // Create FormData for file upload
      const formData = new FormData();

      // Create metadata object
      const metadata = {
        documentType: data.documentType,
        isBinding: data.isBinding,
        inputType: data.inputType,
        dateIssued: data.dateIssued,
        complianceArea: data.complianceArea,
        documentLanguage: data.documentLanguage,
        ...(data.section && { section: data.section }),
        ...(data.title && { title: data.title }),
        ...(data.effectiveDateFrom && { effectiveDateFrom: data.effectiveDateFrom }),
        ...(data.effectiveDateTo && { effectiveDateTo: data.effectiveDateTo }),
        ...(data.notificationNumber && { notificationNumber: data.notificationNumber }),
        ...(data.issuedBy && { issuedBy: data.issuedBy }),
        ...(data.textContent && { textContent: data.textContent }),
        ...(data.copyrightStatus && { copyrightStatus: data.copyrightStatus }),
        ...(data.copyrightAttribution && { copyrightAttribution: data.copyrightAttribution }),
      };

      // Add metadata as JSON string
      formData.append('metadata', JSON.stringify(metadata));

      // Add file if present
      if (data.inputType === 'pdf' && data.pdfFile) {
        formData.append('file', data.pdfFile);
      }

      const response = await fetch('/api/admin/ingest', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (result.success) {
        console.log('Ingestion job created:', result.data.jobId);
        // Could show success toast or redirect to audit tab
      } else {
        console.error('Ingestion failed:', result.error);
      }
    } catch (error) {
      console.error('Ingestion error:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <DashboardTab />;

      case 'ingestion':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                  <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                    <FaUpload className="text-orange-500" />
                  </div>
                  Document Ingestion
                </h2>
                <p className="text-gray-600 mt-1">
                  Upload and ingest new documents into the governance knowledge base
                </p>
              </div>
            </div>

            {/* Mode: Manual vs Vision */}
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex flex-wrap items-center gap-6">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-700">Mode:</span>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="ingestionMode"
                      checked={ingestionMode === 'manual'}
                      onChange={() => setIngestionMode('manual')}
                      className="text-orange-500"
                    />
                    <span>Manual</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="ingestionMode"
                      checked={ingestionMode === 'vision'}
                      onChange={() => setIngestionMode('vision')}
                      className="text-orange-500"
                    />
                    <span>Vision</span>
                  </label>
                </div>
                {ingestionMode === 'vision' && (
                  <div className="flex items-center gap-2">
                    <FaCogs className="text-gray-400" />
                    <span className="text-sm font-medium text-gray-700">Vision model:</span>
                    <select
                      value={visionModel}
                      onChange={(e) => setVisionModel(e.target.value as VisionModelOption)}
                      className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500"
                    >
                      {VISION_MODEL_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            </div>

            {/* Pipeline Status - Shows real-time progress */}
            <PipelineStatus />

            {ingestionMode === 'manual' && (
              <IngestionForm onSubmit={handleIngestionSubmit} isSubmitting={isSubmitting} />
            )}

            {ingestionMode === 'vision' && (
              <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
                <h3 className="text-lg font-semibold text-gray-900">Batch upload (Vision)</h3>
                <p className="text-sm text-gray-600">
                  Add PDFs or text files (select multiple in one go, or use &quot;Add files&quot; again to add more). They are saved to uploads, then processed with the selected vision model. Review and approve in the Audit tab.
                </p>
                <div className="flex flex-wrap items-center gap-4">
                  <input
                    type="file"
                    multiple
                    accept=".pdf,.txt,.png,.jpg,.jpeg,.webp"
                    onChange={handleBatchFilesChange}
                    className="text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border file:border-orange-500 file:bg-orange-50 file:text-orange-700"
                  />
                  <button
                    type="button"
                    onClick={() => setBatchFiles([])}
                    disabled={batchFiles.length === 0 || batchUploading}
                    className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    Clear list
                  </button>
                  <button
                    type="button"
                    onClick={handleBatchUpload}
                    disabled={batchFiles.length === 0 || batchUploading}
                    className="flex items-center gap-2 px-4 py-2 bg-orange-500 text-white rounded-lg font-medium hover:bg-orange-600 disabled:opacity-50"
                  >
                    {batchUploading ? (
                      <>
                        <span className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                        Uploading...
                      </>
                    ) : (
                      <>
                        <FaUpload />
                        Upload {batchFiles.length} file(s) & process
                      </>
                    )}
                  </button>
                </div>
                {batchFiles.length > 0 && (
                  <ul className="text-sm text-gray-600 list-disc list-inside">
                    {batchFiles.map((f, i) => (
                      <li key={i}>{f.name}</li>
                    ))}
                  </ul>
                )}
                {batchError && (
                  <p className="text-sm text-red-600 bg-red-50 p-3 rounded-lg">{batchError}</p>
                )}
                {batchSuccess && (
                  <p className="text-sm text-green-600 bg-green-50 p-3 rounded-lg">{batchSuccess}</p>
                )}
              </div>
            )}
          </div>
        );

      case 'audit':
        return <AuditTab />;

      case 'notifications':
        return <NotificationsTab />;

      case 'chat':
        return <ChatTab />;

      case 'documents':
        return <DocumentsTab />;

      case 'settings':
        return <SettingsTab />;

      default:
        return <DashboardTab />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar - Fixed position */}
      <div className="w-64 shrink-0">
        <div className="fixed top-0 left-0 h-screen w-64 z-20">
          <AdminSidebar activeTab={activeTab} onTabChange={handleTabChange} />
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        {/* Top Header */}
        <header className="bg-white border-b border-gray-200 px-8 py-4 flex items-center justify-between sticky top-0 z-10">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 capitalize">
              {activeTab === 'health' ? 'System Health' : activeTab}
            </h1>
            <p className="text-sm text-gray-500">
              {new Date().toLocaleDateString('en-IN', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
              })}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm font-medium text-gray-900">Welcome back</p>
              <p className="text-xs text-gray-500">Administrator</p>
            </div>
            <div className="w-10 h-10 bg-linear-to-br from-orange-400 to-orange-600 rounded-full flex items-center justify-center text-white font-semibold">
              A
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="p-8">
          {renderContent()}
        </main>
      </div>
    </div>
  );
}

// Wrap with Suspense for useSearchParams
export default function AdminPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
      </div>
    }>
      <AdminPageContent />
    </Suspense>
  );
}
