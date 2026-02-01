import { FaBook, FaFileAlt } from 'react-icons/fa';

interface SectionResultsProps {
  sections: Array<{
    section: string;
    primary_chunk: {
      sub_section?: string;
      citation: string;
      text: string;
    };
    supporting_chunks: Array<{
      document_type: string;
      citation: string;
      llm_summary?: string;
      text: string;
    }>;
  }>;
}

export default function SectionResults({ sections }: SectionResultsProps) {
  return (
    <div className="space-y-8">
      {sections.map((section, index) => (
        <div key={index} className="rounded-lg overflow-hidden border border-gray-300">
          {/* Section Header */}
          <div className="bg-linear-to-r from-blue-900 to-blue-800 text-white p-5 text-xl font-semibold">
            Section {section.section}
            {section.primary_chunk.sub_section && ` (${section.primary_chunk.sub_section})`}
          </div>

          {/* Primary Chunk */}
          <div className="bg-gray-50 p-6 border-b-2 border-gray-300">
            <span className="inline-block bg-green-600 text-white px-3 py-1 rounded text-sm font-semibold mb-3">
              PRIMARY ACT TEXT
            </span>
            <div className="text-sm text-gray-700 mb-4 p-2.5 bg-white border-l-4 border-blue-800 rounded flex items-start gap-2">
              <FaBook className="mt-0.5 text-blue-800 flex-shrink-0" />
              {section.primary_chunk.citation}
            </div>
            <div className="leading-relaxed text-gray-900 bg-white p-5 rounded text-sm">
              {section.primary_chunk.text}
            </div>
          </div>

          {/* Supporting Chunks */}
          {section.supporting_chunks.length > 0 && (
            <div className="p-6 bg-white">
              <div className="text-lg font-semibold text-gray-700 mb-4 pb-2.5 border-b-2 border-gray-200">
                Supporting Documents
              </div>
              <div className="space-y-5">
                {section.supporting_chunks.map((chunk, chunkIndex) => (
                  <div
                    key={chunkIndex}
                    className="p-5 bg-gray-50 rounded-lg border-l-4 border-yellow-500"
                  >
                    <span className="inline-block bg-yellow-500 text-gray-900 px-3 py-1 rounded text-sm font-semibold mb-3">
                      {chunk.document_type.toUpperCase()}
                    </span>
                    <div className="text-sm text-gray-700 mb-4 p-2.5 bg-white border-l-4 border-blue-800 rounded flex items-start gap-2">
                      <FaFileAlt className="mt-0.5 text-blue-800 flex-shrink-0" />
                      {chunk.citation}
                    </div>
                    {chunk.llm_summary ? (
                      <div className="mt-4 p-4 bg-yellow-50 rounded border-l-4 border-yellow-500">
                        <div className="font-semibold text-yellow-800 mb-2 text-sm">
                          AI Summary:
                        </div>
                        <div className="text-yellow-800 leading-relaxed text-sm">
                          {chunk.llm_summary}
                        </div>
                      </div>
                    ) : (
                      <div className="leading-relaxed text-gray-900 bg-white p-5 rounded text-sm">
                        {chunk.text.substring(0, 500)}
                        {chunk.text.length > 500 && '...'}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
