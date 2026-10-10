import React from 'react';
import { RotateCcw } from 'lucide-react';
import { useDuckStore } from '../store/useDuckStore';
import { DuckMascot } from './DuckMascot';

export const ErrorAlert: React.FC = () => {
  const { errorMessage, retryLastMessage } = useDuckStore();

  if (!errorMessage) return null;

  return (
    <div
      role="alert"
      className="my-4 mx-auto max-w-xl p-4 rounded-2xl bg-amber-500/10 dark:bg-amber-500/15 border border-amber-500/30 flex items-center space-x-3.5 shadow-xs animate-fade-in"
    >
      <DuckMascot state="napping" size={48} className="flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-ink-900 dark:text-ink-100 leading-snug">
          {errorMessage}
        </p>
      </div>
      <button
        onClick={retryLastMessage}
        aria-label="Retry previous message"
        className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-duck-400 hover:bg-duck-500 text-ink-950 font-medium text-xs transition-colors shadow-xs flex-shrink-0 focus:outline-none focus:ring-2 focus:ring-duck-500"
      >
        <RotateCcw className="w-3.5 h-3.5" />
        <span>Retry</span>
      </button>
    </div>
  );
};
