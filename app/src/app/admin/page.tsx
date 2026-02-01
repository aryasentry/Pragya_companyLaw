'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import AdminSidebar from '@/components/admin/AdminSidebar';
import IngestionForm from '@/components/admin/IngestionForm';
import AuditTab from '@/components/admin/AuditTab';
import NotificationsTab from '@/components/admin/NotificationsTab';
import DashboardTab from '@/components/admin/DashboardTab';
import AnalyticsTab from '@/components/admin/AnalyticsTab';
import SystemHealthTab from '@/components/admin/SystemHealthTab';
import ChatTab from '@/components/admin/ChatTab';
import DocumentsTab from '@/components/admin/DocumentsTab';
import SettingsTab from '@/components/admin/SettingsTab';
import { IngestionFormData } from '@/types/admin';
import { FaUpload } from 'react-icons/fa';

function AdminPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isSubmitting, setIsSubmitting] = useState(false);

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

  const handleIngestionSubmit = async (data: IngestionFormData) => {
    setIsSubmitting(true);
    
    try {
      // Create FormData for file upload
      const formData = new FormData();
      
      // Add all fields
      formData.append('documentType', data.documentType);
      formData.append('isBinding', String(data.isBinding));
      formData.append('inputType', data.inputType);
      formData.append('dateIssued', data.dateIssued);
      
      if (data.section) {
        formData.append('section', data.section);
      }
      if (data.effectiveDateFrom) {
        formData.append('effectiveDateFrom', data.effectiveDateFrom);
      }
      if (data.effectiveDateTo) {
        formData.append('effectiveDateTo', data.effectiveDateTo);
      }
      if (data.complianceArea) {
        formData.append('complianceArea', data.complianceArea);
      }
      if (data.documentLanguage) {
        formData.append('documentLanguage', data.documentLanguage);
      }
      if (data.notificationNumber) {
        formData.append('notificationNumber', data.notificationNumber);
      }
      if (data.issuedBy) {
        formData.append('issuedBy', data.issuedBy);
      }
      
      // Add file or text content
      if (data.inputType === 'pdf' && data.pdfFile) {
        formData.append('pdfFile', data.pdfFile);
      } else if (data.inputType === 'text' && data.textContent) {
        formData.append('textContent', data.textContent);
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
            <IngestionForm onSubmit={handleIngestionSubmit} isSubmitting={isSubmitting} />
          </div>
        );
      
      case 'audit':
        return <AuditTab />;
      
      case 'notifications':
        return <NotificationsTab />;
      
      case 'analytics':
        return <AnalyticsTab />;
      
      case 'health':
        return <SystemHealthTab />;
      
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
