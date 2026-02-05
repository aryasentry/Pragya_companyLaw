import { FaBook, FaFileAlt, FaChartLine } from 'react-icons/fa';

interface SectionResultsProps {
  sections: Array<{
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
  }>;
}

export default function SectionResults({ sections }: SectionResultsProps) {
  // Group chunks by section
  const groupedSections = sections.reduce((acc, chunk) => {
    const section = chunk.section || 'Unknown';
    if (!acc[section]) {
      acc[section] = [];
    }
    acc[section].push(chunk);
    return acc;
  }, {} as Record<string, typeof sections>);

  return (
    <div className="space-y-8">
      {Object.entries(groupedSections).map(([sectionNumber, chunks], index) => {
        // Sort by priority and similarity
        const sortedChunks = [...chunks].sort((a, b) => {
          if (a.priority !== b.priority) return (a.priority || 999) - (b.priority || 999);
          return (b.similarity_score || 0) - (a.similarity_score || 0);
        });

        return (
          <div key={index} className="rounded-lg overflow-hidden border border-gray-300">
            {/* Section Header */}
            <div className="bg-linear-to-r from-blue-900 to-blue-800 text-white p-5 text-xl font-semibold">
              Section {sectionNumber}
              {sortedChunks[0]?.title && ` - ${sortedChunks[0].title}`}
            </div>

            {/* Chunks */}
            <div className="bg-white p-6 space-y-5">
              {sortedChunks.map((chunk, chunkIndex) => {
                const isHighPriority = (chunk.priority || 999) <= 2;
                const borderColor = isHighPriority ? 'border-blue-800' : 'border-yellow-500';
                const badgeColor = isHighPriority ? 'bg-green-600' : 'bg-yellow-500';
                const badgeText = isHighPriority ? 'text-white' : 'text-gray-900';

                return (
                  <div
                    key={chunk.chunk_id}
                    className={`p-5 bg-gray-50 rounded-lg border-l-4 ${borderColor}`}
                  >
                    {/* Badge and Metadata */}
                    <div className="flex items-center justify-between mb-3">
                      <span className={`inline-block ${badgeColor} ${badgeText} px-3 py-1 rounded text-sm font-semibold`}>
                        {chunk.document_type.toUpperCase()} - Priority {chunk.priority || 'N/A'}
                      </span>
                      {chunk.similarity_score !== undefined && (
                        <div className="flex items-center gap-2 text-sm text-gray-600">
                          <FaChartLine />
                          <span>Match: {(chunk.similarity_score * 100).toFixed(1)}%</span>
                        </div>
                      )}
                    </div>

                    {/* Citation */}
                    {chunk.citation && (
                      <div className="text-sm text-gray-700 mb-4 p-2.5 bg-white border-l-4 border-blue-800 rounded flex items-start gap-2">
                        <FaBook className="mt-0.5 text-blue-800 flex-shrink-0" />
                        {chunk.citation}
                      </div>
                    )}

                    {/* Compliance Area */}
                    {chunk.compliance_area && (
                      <div className="text-sm font-semibold text-blue-800 mb-2">
                        📋 {chunk.compliance_area}
                      </div>
                    )}

                    {/* Text Content */}
                    <div className="leading-relaxed text-gray-900 bg-white p-5 rounded text-sm">
                      {chunk.text}
                    </div>

                    {/* Authority Level */}
                    {chunk.authority_level && (
                      <div className="mt-3 text-xs text-gray-600">
                        Authority: <span className="font-semibold">{chunk.authority_level}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
