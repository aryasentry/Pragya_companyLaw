'use client';

import { useState } from 'react';

interface SearchBarProps {
  onSearch: (query: string) => void;
  loading: boolean;
}

const exampleQueries = [
  {
    label: 'Incorporation process',
    query: 'What is the process for incorporation of a company?',
  },
  {
    label: 'Registered office requirements',
    query: 'What are the requirements for registered office?',
  },
  {
    label: 'Registration forms',
    query: 'What forms are required for company registration?',
  },
  {
    label: 'Director requirements',
    query: 'What are the requirements for directors?',
  },
];

export default function SearchBar({ onSearch, loading }: SearchBarProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    const trimmedQuery = query.trim();
    if (trimmedQuery && !loading) {
      onSearch(trimmedQuery);
    }
  };

  const handleExampleClick = (exampleQuery: string) => {
    setQuery(exampleQuery);
    onSearch(exampleQuery);
  };

  return (
    <div className="p-8 bg-linear-to-b from-gray-50 to-white border-b-2 border-gray-200">
      <form onSubmit={handleSubmit} className="flex gap-4 mb-4">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question about the Companies Act 2013..."
          className="flex-1 px-5 py-4 text-base text-gray-900 placeholder:text-gray-500 
                   border-2 border-gray-300 rounded-lg bg-white
                   focus:outline-none focus:border-blue-800 focus:ring-2 focus:ring-blue-800/10
                   transition-all duration-200"
          disabled={loading}
          autoComplete="off"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="px-10 py-4 text-base font-semibold bg-linear-to-r from-blue-900 to-blue-800 
                   text-white rounded-lg transition-all duration-200
                   hover:shadow-lg hover:-translate-y-0.5 disabled:opacity-60 
                   disabled:cursor-not-allowed disabled:hover:translate-y-0"
        >
          Search
        </button>
      </form>

      <div className="flex flex-wrap gap-2.5">
        {exampleQueries.map((example, index) => (
          <button
            key={index}
            onClick={() => handleExampleClick(example.query)}
            disabled={loading}
            className="px-4 py-2 text-sm text-gray-900 bg-gray-200 border border-transparent rounded-full
                     transition-all duration-200 hover:bg-blue-800 hover:text-white 
                     hover:border-blue-800 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {example.label}
          </button>
        ))}
      </div>
    </div>
  );
}
