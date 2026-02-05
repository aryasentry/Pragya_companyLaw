'use client';

import { useState, useRef, ChangeEvent, DragEvent } from 'react';
import { FaCloudUploadAlt, FaFilePdf, FaTimes, FaCheck } from 'react-icons/fa';

interface DocumentUploadProps {
  onFileSelect: (file: File | null) => void;
  selectedFile: File | null;
  accept?: string;
}

export default function DocumentUpload({
  onFileSelect,
  selectedFile,
  accept = '.pdf',
}: DocumentUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      const file = files[0];
      if (file.type === 'application/pdf') {
        simulateUpload(file);
      }
    }
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      simulateUpload(files[0]);
    }
  };

  const simulateUpload = (file: File) => {
    setUploadProgress(0);
    const interval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev === null) return 0;
        if (prev >= 100) {
          clearInterval(interval);
          // Defer the callback to avoid updating parent during render
          setTimeout(() => onFileSelect(file), 0);
          return 100;
        }
        return prev + 10;
      });
    }, 100);
  };

  const handleRemoveFile = () => {
    onFileSelect(null);
    setUploadProgress(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-gray-700">
        Upload Document
      </label>

      {!selectedFile ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 ${
            isDragging
              ? 'border-orange-500 bg-orange-50'
              : 'border-gray-300 hover:border-orange-400 hover:bg-gray-50'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={accept}
            onChange={handleFileChange}
            className="hidden"
          />
          
          <div className="flex flex-col items-center gap-3">
            <div className={`w-16 h-16 rounded-full flex items-center justify-center ${
              isDragging ? 'bg-orange-100' : 'bg-gray-100'
            }`}>
              <FaCloudUploadAlt className={`text-3xl ${
                isDragging ? 'text-orange-500' : 'text-gray-400'
              }`} />
            </div>
            
            <div>
              <p className="text-sm font-medium text-gray-700">
                {isDragging ? 'Drop your file here' : 'Drag and drop your PDF here'}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                or click to browse from your computer
              </p>
            </div>

            <div className="flex items-center gap-2 text-xs text-gray-400">
              <FaFilePdf className="text-red-400" />
              <span>PDF files only, max 50MB</span>
            </div>
          </div>

          {uploadProgress !== null && uploadProgress < 100 && (
            <div className="absolute inset-0 bg-white/90 flex flex-col items-center justify-center rounded-xl">
              <div className="w-48 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-orange-500 transition-all duration-200"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-sm text-gray-600 mt-2">Uploading... {uploadProgress}%</p>
            </div>
          )}
        </div>
      ) : (
        <div className="border border-gray-200 rounded-xl p-4 bg-gray-50">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center">
              <FaFilePdf className="text-2xl text-red-500" />
            </div>
            
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {selectedFile.name}
              </p>
              <p className="text-xs text-gray-500">
                {formatFileSize(selectedFile.size)}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center">
                <FaCheck className="text-xs text-green-600" />
              </div>
              <button
                onClick={handleRemoveFile}
                className="w-8 h-8 bg-gray-100 hover:bg-red-100 rounded-full flex items-center justify-center transition-colors group"
              >
                <FaTimes className="text-gray-400 group-hover:text-red-500" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
