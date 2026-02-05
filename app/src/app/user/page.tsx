'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { FaBalanceScale, FaUser, FaBook, FaInbox } from 'react-icons/fa';
import { HiChevronLeft } from 'react-icons/hi';
import SearchBar from '@/components/SearchBar';
import SynthesizedAnswer from '@/components/SynthesizedAnswer';
import SectionResults from '@/components/SectionResults';
import LoadingSpinner from '@/components/LoadingSpinner';

interface RetrievedSection {
  chunk_id: string;
  section: string;
  document_type: string;
  text: string;
  title?: string;
  compliance_area?: string;
  priority?: number;
  authority_level?: string;
  citation?: string;
  similarity_score?: number;
}

interface QueryResult {
  synthesized_answer?: string;
  answer_citations?: string[];
  retrieved_sections?: RetrievedSection[];
  retrieved_chunks?: RetrievedSection[]; // New FAISS format
}

export default function UserPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResult | null>(null);

  const handleSearch = async (query: string) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Search failed');
      }

      setResult(data.result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-linear-to-br from-blue-900 via-blue-800 to-blue-900 p-5">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center text-white mb-8 py-5">
          <div className="flex items-center justify-between mb-3">
            <button
              onClick={() => router.push('/')}
              className="text-white/80 hover:text-white transition-colors flex items-center gap-2"
            >
              <HiChevronLeft className="w-5 h-5" />
              Back
            </button>
            <div className="flex items-center gap-3 bg-white/10 px-4 py-2 rounded-full">
              <FaUser className="text-xl" />
              <span className="font-semibold">User Mode</span>
            </div>
          </div>
          <div className="flex items-center justify-center gap-3 mb-3">
            <FaBalanceScale className="text-5xl" />
            <h1 className="text-5xl font-bold drop-shadow-lg">
              Pragya - Company Law
            </h1>
          </div>
          <p className="text-xl opacity-90">CompanyGPT</p>
        </div>

        {/* Main Card */}
        <div className="bg-white rounded-2xl shadow-2xl overflow-hidden">
          <SearchBar onSearch={handleSearch} loading={loading} />

          {loading && <LoadingSpinner />}

          {error && (
            <div className="p-8">
              <div className="bg-red-50 border border-red-200 rounded-lg p-5 text-red-800">
                <strong className="block mb-2 text-lg">⚠️ Error</strong>
                <p>{error}</p>
              </div>
            </div>
          )}

          {result && !loading && (
            <div className="p-8">
              {result.synthesized_answer && (
                <SynthesizedAnswer
                  answer={result.synthesized_answer}
                  citations={result.answer_citations}
                />
              )}

              {((result.retrieved_sections && result.retrieved_sections.length > 0) || 
                (result.retrieved_chunks && result.retrieved_chunks.length > 0)) ? (
                <>
                  <h2 className="text-2xl font-semibold text-gray-700 mt-8 mb-5 pb-3 border-b-2 border-gray-300 flex items-center gap-2">
                    <FaBook className="text-2xl" />
                    Source Documents
                  </h2>
                  <SectionResults sections={result.retrieved_sections || result.retrieved_chunks || []} />
                </>
              ) : (
                <div className="text-center py-16 text-gray-500">
                  <FaInbox className="text-6xl mb-5 mx-auto" />
                  <h3 className="text-2xl font-semibold mb-2">No results found</h3>
                  <p>Try rephrasing your query or use different keywords</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
