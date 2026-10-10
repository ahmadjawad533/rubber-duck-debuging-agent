import React, { useState } from 'react';
import { Check, Copy } from 'lucide-react';

interface CodeBlockProps {
  language?: string;
  code: string;
}

export const CodeBlock: React.FC<CodeBlockProps> = ({ language = 'text', code }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.warn('Failed to copy to clipboard', err);
    }
  };

  return (
    <div className="relative my-3 rounded-lg overflow-hidden border border-ink-200 dark:border-ink-800 bg-ink-900 text-ink-50 font-mono text-xs sm:text-sm shadow-sm group">
      {/* Code Header Bar */}
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-ink-950/80 border-b border-ink-800/80 text-ink-400 select-none">
        <span className="text-xs uppercase tracking-wider font-semibold text-duck-400">
          {language || 'code'}
        </span>
        <button
          onClick={handleCopy}
          aria-label="Copy code snippet to clipboard"
          className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded text-xs text-ink-300 hover:text-ink-100 hover:bg-ink-800/80 transition-colors focus:outline-none focus:ring-1 focus:ring-duck-400"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400 font-sans">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span className="font-sans">Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Code Content */}
      <div className="p-3.5 overflow-x-auto leading-relaxed">
        <pre className="font-mono">
          <code>{code}</code>
        </pre>
      </div>
    </div>
  );
};
