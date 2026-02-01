'use client';

import { FaLightbulb, FaClipboardList } from 'react-icons/fa';

interface SynthesizedAnswerProps {
  answer: string;
  citations?: string[];
}

// Simple markdown to HTML converter
function markdownToHtml(text: string): string {
  if (!text) return '';
  
  let html = text;
  
  // Headers (### )
  html = html.replace(/^### (.+)$/gm, '<h3 class="mt-4 mb-2 text-lg font-semibold">$1</h3>');
  
  // Bold (**text** or __text__)
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');
  
  // Italic (*text* or _text_)
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  html = html.replace(/_(.+?)_/g, '<em>$1</em>');
  
  // Code blocks (```code```)
  html = html.replace(/```(.+?)```/gs, '<code class="block bg-white/20 p-2.5 rounded my-2">$1</code>');
  
  // Inline code (`code`)
  html = html.replace(/`(.+?)`/g, '<code class="bg-white/20 px-1.5 py-0.5 rounded">$1</code>');
  
  // Blockquotes (> text)
  html = html.replace(/^> (.+)$/gm, '<blockquote class="border-l-2 border-white/50 pl-4 my-2 italic">$1</blockquote>');
  
  // Unordered lists (- item or * item)
  html = html.replace(/^- (.+)$/gm, '<li class="ml-5">$1</li>');
  html = html.replace(/^\* (.+)$/gm, '<li class="ml-5">$1</li>');
  
  // Ordered lists (1. item)
  html = html.replace(/^\d+\. (.+)$/gm, '<li class="ml-5">$1</li>');
  
  // Wrap consecutive <li> in <ul>
  html = html.replace(/(<li[^>]*>.*?<\/li>\s*)+/gs, '<ul class="my-2">$&</ul>');
  
  // Paragraphs (double newline creates paragraph breaks)
  html = html.replace(/\n\n/g, '</p><p class="my-4">');
  html = '<p class="my-4">' + html + '</p>';
  
  // Single newlines become <br>
  html = html.replace(/\n/g, '<br>');
  
  return html;
}

export default function SynthesizedAnswer({ answer, citations }: SynthesizedAnswerProps) {
  return (
    <div className="bg-linear-to-r from-blue-900 to-blue-800 text-white p-8 mb-8 rounded-lg shadow-lg">
      <h3 className="text-2xl font-semibold mb-4 pb-3 border-b-2 border-white/30 flex items-center gap-2">
        <FaLightbulb className="text-2xl" />
        Synthesized Answer
      </h3>
      <div 
        className="leading-relaxed text-lg mb-5"
        dangerouslySetInnerHTML={{ __html: markdownToHtml(answer) }}
      />
      {citations && citations.length > 0 && (
        <div className="bg-white/10 p-4 rounded-lg border-l-4 border-white/50">
          <h4 className="text-sm font-semibold mb-2 opacity-90">Citations:</h4>
          <ul className="list-none p-0">
            {citations.map((citation, index) => (
              <li key={index} className="py-1 text-sm opacity-95 flex items-start gap-2">
                <FaClipboardList className="mt-1 flex-shrink-0" />
                {citation}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
