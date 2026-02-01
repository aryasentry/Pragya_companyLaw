'use client';

import { useState, FormEvent } from 'react';
import {
  FaUpload,
  FaFileAlt,
  FaFilePdf,
  FaInfoCircle,
  FaCalendar,
  FaGlobe,
  FaCheckCircle,
} from 'react-icons/fa';
import DocumentUpload from './DocumentUpload';
import {
  IngestionFormData,
  DocumentType,
  BINDING_DOCUMENT_TYPES,
  COMPANIES_ACT_SECTIONS,
  DOCUMENT_LANGUAGES,
  COMPLIANCE_AREAS,
} from '@/types/admin';

interface IngestionFormProps {
  onSubmit: (data: IngestionFormData) => void;
  isSubmitting?: boolean;
}

const ALL_DOCUMENT_TYPES: { value: DocumentType; label: string; binding: boolean }[] = [
  { value: 'act', label: 'Act', binding: true },
  { value: 'rule', label: 'Rule', binding: true },
  { value: 'regulation', label: 'Regulation', binding: true },
  { value: 'order', label: 'Order', binding: true },
  { value: 'notification', label: 'Notification', binding: true },
  { value: 'circular', label: 'Circular', binding: true },
  { value: 'sop', label: 'SOP', binding: false },
  { value: 'form', label: 'Form', binding: true },
  { value: 'guideline', label: 'Guideline', binding: false },
  { value: 'practice_note', label: 'Practice Note', binding: false },
  { value: 'commentary', label: 'Commentary', binding: false },
  { value: 'textbook', label: 'Textbook', binding: false },
  { value: 'qa_book', label: 'Q&A Book', binding: false },
  { value: 'schedule', label: 'Schedule', binding: true },
  { value: 'register', label: 'Register', binding: true },
  { value: 'return', label: 'Return', binding: true },
  { value: 'qa', label: 'Q&A', binding: false },
  { value: 'other', label: 'Other', binding: false },
];

export default function IngestionForm({ onSubmit, isSubmitting = false }: IngestionFormProps) {
  const [formData, setFormData] = useState<Partial<IngestionFormData>>({
    documentType: undefined,
    isBinding: true,
    inputType: 'pdf',
    dateIssued: new Date().toISOString().split('T')[0],
    documentLanguage: 'English',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showSuccess, setShowSuccess] = useState(false);

  const selectedDocType = ALL_DOCUMENT_TYPES.find(d => d.value === formData.documentType);
  const isBindingType = selectedDocType?.binding ?? true;
  const requiresSection = formData.isBinding && BINDING_DOCUMENT_TYPES.includes(formData.documentType as DocumentType);

  const handleChange = (field: keyof IngestionFormData, value: unknown) => {
    setFormData(prev => {
      const updated = { ...prev, [field]: value };
      
      // Auto-set binding status based on document type
      if (field === 'documentType') {
        const docType = ALL_DOCUMENT_TYPES.find(d => d.value === value);
        if (docType) {
          updated.isBinding = docType.binding;
          if (!docType.binding) {
            updated.section = undefined;
          }
        }
      }
      
      return updated;
    });
    
    // Clear error for this field
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.documentType) {
      newErrors.documentType = 'Document type is required';
    }

    if (requiresSection && !formData.section) {
      newErrors.section = 'Section is required for binding documents';
    }

    if (!formData.dateIssued) {
      newErrors.dateIssued = 'Date issued is required';
    }

    if (!formData.complianceArea) {
      newErrors.complianceArea = 'Compliance area is required';
    }

    if (!formData.documentLanguage) {
      newErrors.documentLanguage = 'Document language is required';
    }

    if (formData.inputType === 'pdf' && !formData.pdfFile) {
      newErrors.pdfFile = 'Please upload a PDF document';
    }

    if (formData.inputType === 'text' && !formData.textContent?.trim()) {
      newErrors.textContent = 'Please enter document text';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    
    if (validateForm()) {
      onSubmit(formData as IngestionFormData);
      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 3000);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {/* Success Message */}
      {showSuccess && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-center gap-3">
          <FaCheckCircle className="text-green-500 text-xl" />
          <div>
            <p className="font-medium text-green-800">Document queued for ingestion</p>
            <p className="text-sm text-green-600">Processing will begin shortly</p>
          </div>
        </div>
      )}

      {/* Section 1: Document Classification */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <span className="w-6 h-6 bg-orange-100 rounded-full flex items-center justify-center text-orange-600 text-sm font-bold">
            1
          </span>
          Document Classification
        </h3>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Document Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Document Type <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.documentType || ''}
              onChange={(e) => handleChange('documentType', e.target.value)}
              className={`w-full px-4 py-3 border rounded-lg text-gray-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all ${
                errors.documentType ? 'border-red-500' : 'border-gray-300'
              }`}
            >
              <option value="">Select document type...</option>
              <optgroup label="Binding Documents">
                {ALL_DOCUMENT_TYPES.filter(d => d.binding).map(type => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </optgroup>
              <optgroup label="Non-Binding Documents">
                {ALL_DOCUMENT_TYPES.filter(d => !d.binding).map(type => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </optgroup>
            </select>
            {errors.documentType && (
              <p className="text-red-500 text-sm mt-1">{errors.documentType}</p>
            )}
          </div>

          {/* Binding Status */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Binding Status
            </label>
            <div className="flex gap-4">
              <label className={`flex-1 flex items-center gap-3 px-4 py-3 border rounded-lg cursor-pointer transition-all ${
                formData.isBinding 
                  ? 'border-orange-500 bg-orange-50 ring-2 ring-orange-500' 
                  : 'border-gray-300 hover:border-gray-400'
              }`}>
                <input
                  type="radio"
                  name="binding"
                  checked={formData.isBinding === true}
                  onChange={() => handleChange('isBinding', true)}
                  className="sr-only"
                />
                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                  formData.isBinding ? 'border-orange-500 bg-orange-500' : 'border-gray-300'
                }`}>
                  {formData.isBinding && <div className="w-2 h-2 bg-white rounded-full" />}
                </div>
                <span className="font-medium text-gray-900">Binding</span>
              </label>
              <label className={`flex-1 flex items-center gap-3 px-4 py-3 border rounded-lg cursor-pointer transition-all ${
                formData.isBinding === false
                  ? 'border-orange-500 bg-orange-50 ring-2 ring-orange-500' 
                  : 'border-gray-300 hover:border-gray-400'
              }`}>
                <input
                  type="radio"
                  name="binding"
                  checked={formData.isBinding === false}
                  onChange={() => handleChange('isBinding', false)}
                  className="sr-only"
                />
                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                  !formData.isBinding ? 'border-orange-500 bg-orange-500' : 'border-gray-300'
                }`}>
                  {!formData.isBinding && <div className="w-2 h-2 bg-white rounded-full" />}
                </div>
                <span className="font-medium text-gray-900">Non-Binding</span>
              </label>
            </div>
            {!isBindingType && (
              <p className="text-sm text-amber-600 mt-2 flex items-center gap-1">
                <FaInfoCircle />
                This document type is typically non-binding
              </p>
            )}
          </div>

          {/* Section Selection (only for binding) */}
          {formData.isBinding && (
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Companies Act Section {requiresSection && <span className="text-red-500">*</span>}
              </label>
              <select
                value={formData.section || ''}
                onChange={(e) => handleChange('section', e.target.value)}
                className={`w-full px-4 py-3 border rounded-lg text-gray-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all ${
                  errors.section ? 'border-red-500' : 'border-gray-300'
                }`}
              >
                <option value="">Select section...</option>
                {COMPANIES_ACT_SECTIONS.slice(0, 100).map(section => (
                  <option key={section} value={section}>
                    Section {parseInt(section)}
                  </option>
                ))}
              </select>
              {errors.section && (
                <p className="text-red-500 text-sm mt-1">{errors.section}</p>
              )}
              <p className="text-sm text-gray-500 mt-1">
                Select the Companies Act 2013 section this document relates to
              </p>
            </div>
          )}

          {!formData.isBinding && (
            <div className="md:col-span-2 bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
              <FaInfoCircle className="text-blue-500 mt-0.5" />
              <div>
                <p className="font-medium text-blue-800">Non-Binding Document</p>
                <p className="text-sm text-blue-700">
                  This document will be stored in the non-binding folder (raw/non-binding) and categorized 
                  based on its type (qa, textbooks, etc.)
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Section 2: Document Content */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <span className="w-6 h-6 bg-orange-100 rounded-full flex items-center justify-center text-orange-600 text-sm font-bold">
            2
          </span>
          Document Content
        </h3>

        {/* Input Type Toggle */}
        <div className="flex gap-2 mb-6">
          <button
            type="button"
            onClick={() => handleChange('inputType', 'pdf')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
              formData.inputType === 'pdf'
                ? 'bg-orange-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <FaFilePdf />
            Upload PDF
          </button>
          <button
            type="button"
            onClick={() => handleChange('inputType', 'text')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
              formData.inputType === 'text'
                ? 'bg-orange-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <FaFileAlt />
            Enter Text
          </button>
        </div>

        {/* PDF Upload */}
        {formData.inputType === 'pdf' && (
          <div>
            <DocumentUpload
              onFileSelect={(file) => handleChange('pdfFile', file)}
              selectedFile={formData.pdfFile || null}
            />
            {errors.pdfFile && (
              <p className="text-red-500 text-sm mt-2">{errors.pdfFile}</p>
            )}
          </div>
        )}

        {/* Text Input */}
        {formData.inputType === 'text' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Document Text <span className="text-red-500">*</span>
            </label>
            <textarea
              value={formData.textContent || ''}
              onChange={(e) => handleChange('textContent', e.target.value)}
              placeholder="Paste or type the document content here..."
              rows={10}
              className={`w-full px-4 py-3 border rounded-lg text-gray-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all resize-none ${
                errors.textContent ? 'border-red-500' : 'border-gray-300'
              }`}
            />
            {errors.textContent && (
              <p className="text-red-500 text-sm mt-1">{errors.textContent}</p>
            )}
            <p className="text-sm text-gray-500 mt-1">
              {(formData.textContent?.length || 0).toLocaleString()} characters
            </p>
          </div>
        )}

        {/* Document Title */}
        <div className="mt-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Document Title
          </label>
          <input
            type="text"
            value={formData.title || ''}
            onChange={(e) => handleChange('title', e.target.value)}
            placeholder="Enter a descriptive title for this document"
            className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all"
          />
        </div>
      </div>

      {/* Section 3: Temporal Information */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <span className="w-6 h-6 bg-orange-100 rounded-full flex items-center justify-center text-orange-600 text-sm font-bold">
            3
          </span>
          Temporal Information
          <FaCalendar className="text-gray-400 ml-2" />
        </h3>

        <div className="grid md:grid-cols-3 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Date Issued <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              value={formData.dateIssued || ''}
              onChange={(e) => handleChange('dateIssued', e.target.value)}
              className={`w-full px-4 py-3 border rounded-lg text-gray-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all ${
                errors.dateIssued ? 'border-red-500' : 'border-gray-300'
              }`}
            />
            {errors.dateIssued && (
              <p className="text-red-500 text-sm mt-1">{errors.dateIssued}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Effective From
            </label>
            <input
              type="date"
              value={formData.effectiveDateFrom || ''}
              onChange={(e) => handleChange('effectiveDateFrom', e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Effective To
            </label>
            <input
              type="date"
              value={formData.effectiveDateTo || ''}
              onChange={(e) => handleChange('effectiveDateTo', e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all"
            />
            <p className="text-sm text-gray-500 mt-1">Leave blank if still effective</p>
          </div>
        </div>
      </div>

      {/* Section 4: Metadata */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <span className="w-6 h-6 bg-orange-100 rounded-full flex items-center justify-center text-orange-600 text-sm font-bold">
            4
          </span>
          Document Metadata
        </h3>

        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Compliance Area <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.complianceArea || ''}
              onChange={(e) => handleChange('complianceArea', e.target.value)}
              className={`w-full px-4 py-3 border rounded-lg text-gray-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all ${
                errors.complianceArea ? 'border-red-500' : 'border-gray-300'
              }`}
            >
              <option value="">Select compliance area...</option>
              {COMPLIANCE_AREAS.map(area => (
                <option key={area} value={area}>{area}</option>
              ))}
            </select>
            {errors.complianceArea && (
              <p className="text-red-500 text-sm mt-1">{errors.complianceArea}</p>
            )}
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
              <FaGlobe className="text-gray-400" />
              Document Language <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.documentLanguage || ''}
              onChange={(e) => handleChange('documentLanguage', e.target.value)}
              className={`w-full px-4 py-3 border rounded-lg text-gray-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all ${
                errors.documentLanguage ? 'border-red-500' : 'border-gray-300'
              }`}
            >
              <option value="">Select language...</option>
              {DOCUMENT_LANGUAGES.map(lang => (
                <option key={lang} value={lang}>{lang}</option>
              ))}
            </select>
            {errors.documentLanguage && (
              <p className="text-red-500 text-sm mt-1">{errors.documentLanguage}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Notification Number
            </label>
            <input
              type="text"
              value={formData.notificationNumber || ''}
              onChange={(e) => handleChange('notificationNumber', e.target.value)}
              placeholder="e.g., G.S.R. 123(E)"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Issued By
            </label>
            <input
              type="text"
              value={formData.issuedBy || ''}
              onChange={(e) => handleChange('issuedBy', e.target.value)}
              placeholder="e.g., Ministry of Corporate Affairs"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all"
            />
          </div>
        </div>
      </div>

      {/* Submit Button */}
      <div className="flex justify-end gap-4">
        <button
          type="button"
          onClick={() => setFormData({
            documentType: undefined,
            isBinding: true,
            inputType: 'pdf',
            dateIssued: new Date().toISOString().split('T')[0],
            documentLanguage: 'English',
          })}
          className="px-6 py-3 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors"
        >
          Clear Form
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="flex items-center gap-2 px-8 py-3 bg-linear-to-r from-orange-500 to-orange-600 text-white font-semibold rounded-lg hover:from-orange-600 hover:to-orange-700 transition-all shadow-lg shadow-orange-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? (
            <>
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <FaUpload />
              Ingest Document
            </>
          )}
        </button>
      </div>
    </form>
  );
}
