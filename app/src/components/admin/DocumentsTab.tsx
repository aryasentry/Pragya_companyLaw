'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  FaFolder,
  FaFolderOpen,
  FaFilePdf,
  FaFileAlt,
  FaChevronRight,
  FaSearch,
  FaDownload,
  FaEye,
  FaFilter,
  FaSync,
  FaUpload,
} from 'react-icons/fa';
import UploadModal from './UploadModal';
import PipelineStatus from './PipelineStatus';

interface FolderNode {
  name: string;
  type: 'folder' | 'file';
  children?: FolderNode[];
  fileType?: string;
  size?: string;
}

interface DocumentStats {
  totalDocuments: number;
  sectionsCovered: number;
  totalSize: string;
}

interface RecentDocument {
  name: string;
  section: string;
  type: string;
  date: string;
}

interface FolderTreeProps {
  nodes: FolderNode[];
  level?: number;
}

function FolderTree({ nodes, level = 0 }: FolderTreeProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const toggleExpand = (name: string) => {
    setExpanded(prev => ({ ...prev, [name]: !prev[name] }));
  };

  return (
    <div className="space-y-1">
      {(Array.isArray(nodes) ? nodes : []).map((node) => (
        <div key={node.name}>
          <div
            className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors hover:bg-gray-100 ${
              level > 0 ? 'ml-' + (level * 4) : ''
            }`}
            style={{ marginLeft: level * 16 }}
            onClick={() => node.type === 'folder' && toggleExpand(node.name)}
          >
            {node.type === 'folder' ? (
              <>
                <FaChevronRight 
                  className={`text-gray-400 text-xs transition-transform ${
                    expanded[node.name] ? 'rotate-90' : ''
                  }`}
                />
                {expanded[node.name] 
                  ? <FaFolderOpen className="text-amber-500" />
                  : <FaFolder className="text-amber-500" />
                }
              </>
            ) : (
              <>
                <span className="w-3" />
                {node.fileType === 'pdf' 
                  ? <FaFilePdf className="text-red-500" />
                  : <FaFileAlt className="text-gray-400" />
                }
              </>
            )}
            <span className="text-sm text-gray-700 flex-1">{node.name}</span>
            {node.size && (
              <span className="text-xs text-gray-400">{node.size}</span>
            )}
            {node.type === 'file' && (
              <button className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-orange-500">
                <FaEye className="text-sm" />
              </button>
            )}
          </div>
          {node.type === 'folder' && expanded[node.name] && node.children && (
            <FolderTree nodes={node.children} level={level + 1} />
          )}
        </div>
      ))}
    </div>
  );
}

export default function DocumentsTab() {
  const [searchQuery, setSearchQuery] = useState('');
  const [fileTree, setFileTree] = useState<FolderNode[]>([]);
  const [stats, setStats] = useState<DocumentStats | null>(null);
  const [recentDocs, setRecentDocs] = useState<RecentDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUploadModal, setShowUploadModal] = useState(false);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    try {
      // Fetch tree view
      const treeResponse = await fetch('/api/admin/documents?view=tree');
      const treeData = await treeResponse.json();
      if (treeData.success) {
        setFileTree(treeData.data);
      }

      // Fetch stats
      const statsResponse = await fetch('/api/admin/documents?view=stats');
      const statsData = await statsResponse.json();
      if (statsData.success) {
        setStats(statsData.data);
      }

      // Fetch recent documents
      const listResponse = await fetch('/api/admin/documents?view=list&limit=4');
      const listData = await listResponse.json();
      if (listData.success) {
        setRecentDocs(listData.data);
      }
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleUploadSuccess = () => {
    fetchDocuments();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <FaSync className="animate-spin text-3xl text-orange-500 mx-auto mb-3" />
          <p className="text-gray-500">Loading documents...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Documents</h2>
          <p className="text-gray-600">Browse and manage document repository</p>
        </div>
        <button 
          onClick={() => setShowUploadModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-orange-500 text-white font-medium rounded-lg hover:bg-orange-600 transition-colors"
        >
          <FaUpload />
          Upload Document
        </button>
      </div>

      {/* Pipeline Status */}
      <PipelineStatus />

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Folder Tree */}
        <div className="lg:col-span-1 bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="p-4 border-b border-gray-200">
            <div className="relative">
              <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search files..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent text-sm"
              />
            </div>
          </div>
          <div className="p-4 max-h-[500px] overflow-y-auto">
            <FolderTree nodes={fileTree} />
          </div>
        </div>

        {/* Document Stats */}
        <div className="lg:col-span-2 space-y-6">
          {/* Stats */}
          <div className="grid md:grid-cols-3 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="text-3xl font-bold text-gray-900">{stats?.totalDocuments.toLocaleString() || 0}</div>
              <div className="text-sm text-gray-500">Total Documents</div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="text-3xl font-bold text-gray-900">{stats?.sectionsCovered || 0}</div>
              <div className="text-sm text-gray-500">Sections Covered</div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="text-3xl font-bold text-gray-900">{stats?.totalSize || '0 MB'}</div>
              <div className="text-sm text-gray-500">Total Size</div>
            </div>
          </div>

          {/* Recent Documents */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">Recently Added</h3>
              <button className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900">
                <FaFilter />
                Filter
              </button>
            </div>
            <div className="divide-y divide-gray-200">
              {recentDocs.map((doc) => (
                <div key={doc.name} className="px-6 py-4 flex items-center gap-4 hover:bg-gray-50">
                  <FaFilePdf className="text-red-500 text-xl" />
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{doc.name}</p>
                    <p className="text-sm text-gray-500">
                      Section {doc.section} • {doc.type}
                    </p>
                  </div>
                  <span className="text-sm text-gray-400">{doc.date}</span>
                  <button className="text-gray-400 hover:text-orange-500">
                    <FaEye />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Upload Modal */}
      <UploadModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUploadSuccess={handleUploadSuccess}
      />
    </div>
  );
}
