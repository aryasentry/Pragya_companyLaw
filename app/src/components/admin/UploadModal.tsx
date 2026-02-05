'use client';

import { useState, useRef } from 'react';
import { FaTimes, FaUpload, FaFile, FaSpinner } from 'react-icons/fa';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: () => void;
}

export default function UploadModal({ isOpen, onClose, onUploadSuccess }: UploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState('Act');
  const [category, setCategory] = useState<'companies_act' | 'non_binding'>('companies_act');
  const [section, setSection] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Document types by category
  const companiesActTypes = [
    'Act', 'Rule', 'Regulation', 'Order', 'Notification', 
    'Circular', 'Form', 'Schedule', 'Register', 'Return', 'Q&A', 'Others'
  ];
  
  const nonBindingTypes = [
    'SOP', 'Guideline', 'Practice Note', 'Commentary', 'Textbook', 'Q&A', 'Others'
  ];

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file');
      return;
    }

    if (category === 'companies_act' && !section.trim()) {
      setError('Please enter a section number for Companies Act documents');
      return;
    }

    setUploading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('documentType', documentType);
      formData.append('category', category);
      formData.append('section', section || '0');

      const response = await fetch('/api/admin/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (data.success) {
        onUploadSuccess();
        handleClose();
      } else {
        setError(data.error || 'Upload failed');
      }
    } catch (err) {
      setError('Failed to upload file. Please try again.');
      console.error('Upload error:', err);
    } finally {
      setUploading(false);
    }
  };

  const handleClose = () => {
    setFile(null);
    setDocumentType('Act');
    setCategory('companies_act');
    setSection('');
    setError('');
    setUploading(false);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">Upload Document</h2>
          <button
            onClick={handleClose}
            disabled={uploading}
            className="text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
          >
            <FaTimes className="text-xl" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-6 space-y-6">
          {/* File Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              File
            </label>
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-orange-400 transition-colors"
            >
              {file ? (
                <div className="flex items-center justify-center gap-3">
                  <FaFile className="text-2xl text-orange-500" />
                  <div className="text-left">
                    <p className="font-medium text-gray-900">{file.name}</p>
                    <p className="text-sm text-gray-500">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <FaUpload className="text-3xl text-gray-400 mx-auto" />
                  <p className="text-gray-600">Click to select file</p>
                  <p className="text-xs text-gray-400">PDF, TXT, DOC supported</p>
                </div>
              )}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileChange}
              accept=".pdf,.txt,.doc,.docx"
              className="hidden"
              disabled={uploading}
            />
          </div>

          {/* Category Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Document Category
            </label>
            <select
              value={category}
              onChange={(e) => {
                const newCategory = e.target.value as 'companies_act' | 'non_binding';
                setCategory(newCategory);
                // Reset document type to first option of new category
                setDocumentType(newCategory === 'companies_act' ? companiesActTypes[0] : nonBindingTypes[0]);
                if (newCategory === 'non_binding') {
                  setSection(''); // Clear section for non-binding
                }
              }}
              disabled={uploading}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            >
              <option value="companies_act">Companies Act Documents</option>
              <option value="non_binding">Non-Binding Documents</option>
            </select>
          </div>

          {/* Document Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Document Type
            </label>
            <select
              value={documentType}
              onChange={(e) => setDocumentType(e.target.value)}
              disabled={uploading}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            >
              {category === 'companies_act' ? (
                companiesActTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))
              ) : (
                nonBindingTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))
              )}
            </select>
          </div>

          {/* Section Number - Only for Companies Act */}
          {category === 'companies_act' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Section Number <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                min="1"
                max="43"
                value={section}
                onChange={(e) => setSection(e.target.value)}
                disabled={uploading}
                placeholder="Enter section (1-43)"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-end gap-3">
          <button
            onClick={handleClose}
            disabled={uploading}
            className="px-4 py-2 text-gray-700 font-medium rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={uploading || !file}
            className="px-6 py-2 bg-orange-500 text-white font-medium rounded-lg hover:bg-orange-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {uploading ? (
              <>
                <FaSpinner className="animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <FaUpload />
                Upload
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
