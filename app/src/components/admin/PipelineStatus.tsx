'use client';

import { useEffect, useState } from 'react';
import { FaSpinner, FaCheckCircle, FaTimesCircle, FaFile, FaClock } from 'react-icons/fa';

interface PipelineStatusData {
  running: boolean;
  current_file: string | null;
  stage: string | null;
  message: string | null;
  logs: string[];
  progress?: number;
}

const STAGE_STEPS = [
  { name: 'Starting', icon: FaClock },
  { name: 'Parsing', icon: FaFile },
  { name: 'Chunking', icon: FaFile },
  { name: 'Summarizing', icon: FaFile },
  { name: 'Relationships', icon: FaFile },
  { name: 'Building Embeddings', icon: FaFile },
  { name: 'Completed', icon: FaCheckCircle }
];

export default function PipelineStatus() {
  const [status, setStatus] = useState<PipelineStatusData | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/pipeline/status');
        const data = await response.json();
        setStatus(data);
        setLastUpdate(new Date());

        // Auto-expand when processing starts
        if (data.running && !expanded) {
          setExpanded(true);
        }

        // Auto-collapse 5 seconds after completion
        if (data.stage === 'Completed' && !data.running && expanded) {
          setTimeout(() => setExpanded(false), 5000);
        }
      } catch (error) {
        console.error('Failed to fetch pipeline status:', error);
      }
    };

    // Poll every 500ms when running, every 5 seconds when idle
    const interval = setInterval(fetchStatus, status?.running ? 500 : 5000);
    fetchStatus();

    return () => clearInterval(interval);
  }, [status?.running, expanded]);

  if (!status) return null;

  // Don't show if never run
  if (!status.running && !status.current_file && status.logs.length === 0) {
    return null;
  }

  const currentStepIndex = STAGE_STEPS.findIndex(s =>
    status.stage?.toLowerCase().includes(s.name.toLowerCase())
  );

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6 border-l-4 border-orange-500">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-start gap-4 flex-1">
          <div className="mt-1">
            {status.running ? (
              <FaSpinner className="text-orange-500 animate-spin text-2xl" />
            ) : status.stage === 'Completed' ? (
              <FaCheckCircle className="text-green-500 text-2xl" />
            ) : status.stage === 'Failed' ? (
              <FaTimesCircle className="text-red-500 text-2xl" />
            ) : (
              <FaCheckCircle className="text-gray-400 text-2xl" />
            )}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h3 className="font-semibold text-gray-900 text-lg">
                {status.running ? 'Processing Document' : status.stage || 'Pipeline Ready'}
              </h3>
              {status.current_file && (
                <span className="text-sm bg-gray-100 px-3 py-1 rounded-full text-gray-600">
                  {status.current_file}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-600 mb-3">
              {status.stage === 'Completed'
                ? '✓ Document successfully processed and indexed!'
                : status.message || 'Ready for new uploads'}
            </p>

            {/* Progress Steps */}
            {status.running && currentStepIndex >= 0 && (
              <div className="space-y-3">
                <div className="flex items-center gap-2 mt-4">
                  {STAGE_STEPS.map((step, index) => {
                    const Icon = step.icon;
                    const isActive = index === currentStepIndex;
                    const isCompleted = index < currentStepIndex;

                    return (
                      <div key={step.name} className="flex items-center">
                        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-colors ${isActive ? 'bg-orange-100 text-orange-700' :
                            isCompleted ? 'bg-green-100 text-green-700' :
                              'bg-gray-100 text-gray-400'
                          }`}>
                          <Icon className="text-sm" />
                          <span className="text-xs font-medium">{step.name}</span>
                        </div>
                        {index < STAGE_STEPS.length - 1 && (
                          <div className={`w-8 h-0.5 mx-1 ${isCompleted ? 'bg-green-400' : 'bg-gray-300'
                            }`} />
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Embedding Progress Bar */}
                {status.stage === 'Building Embeddings' && status.progress !== undefined && (
                  <div className="mt-2">
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-gray-600">Generating embeddings</span>
                      <span className="text-orange-600 font-semibold">{status.progress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-orange-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${status.progress}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          {status.logs.length > 0 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-sm text-orange-600 hover:text-orange-700 font-medium"
            >
              {expanded ? 'Hide Logs' : 'Show Logs'}
            </button>
          )}
          {lastUpdate && (
            <span className="text-xs text-gray-400">
              Updated {lastUpdate.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {expanded && status.logs.length > 0 && (
        <div className="mt-4 bg-gray-900 text-gray-100 rounded-lg p-4 font-mono text-xs max-h-96 overflow-y-auto">
          {status.logs.map((log, idx) => (
            <div key={idx} className="mb-1 leading-relaxed">{log}</div>
          ))}
        </div>
      )}
    </div>
  );
}
