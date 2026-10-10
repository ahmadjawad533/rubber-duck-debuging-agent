import React from 'react';
import { DuckMascot } from './DuckMascot';
import { useDuckStore } from '../store/useDuckStore';
import { Terminal, Bug, Zap } from 'lucide-react';

export const EmptyState: React.FC = () => {
  const { sendMessage, duckState } = useDuckStore();

  const exampleBugs = [
    {
      title: 'JavaScript Undefined Error',
      icon: <Terminal className="w-4 h-4 text-duck-500" />,
      snippet: "TypeError: Cannot read properties of undefined (reading 'items') in fetchUserData()",
    },
    {
      title: 'Python Index Error',
      icon: <Bug className="w-4 h-4 text-emerald-500" />,
      snippet: "IndexError: list index out of range in process_batch(items[i]) at line 42",
    },
    {
      title: 'React Render Loop',
      icon: <Zap className="w-4 h-4 text-sky-500" />,
      snippet: "Maximum update depth exceeded. This can happen when a component repeatedly calls setState inside useEffect.",
    },
  ];

  return (
    <div className="flex flex-col items-center justify-center text-center px-4 py-8 max-w-xl mx-auto my-auto animate-fade-in">
      <div className="mb-4">
        <DuckMascot state={duckState} size={130} />
      </div>

      <h2 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-ink-900 dark:text-ink-50">
        Quack. What's broken?
      </h2>

      <p className="mt-2 text-sm text-ink-600 dark:text-ink-300 max-w-md leading-relaxed">
        I won't just dump code for you to blindly copy. Tell me what's failing, and I'll ask you{' '}
        <strong>one question at a time</strong> until you spot the root cause.
      </p>

      {/* 3 Clickable Example Bugs */}
      <div className="mt-6 w-full space-y-2.5 text-left">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-400 dark:text-ink-500 px-1">
          Or try a classic debugging scenario:
        </span>
        {(exampleBugs ?? []).map((bug, idx) => (
          <button
            key={idx}
            onClick={() => sendMessage(bug.snippet)}
            aria-label={`Test with scenario: ${bug.title}`}
            className="w-full p-3 rounded-2xl border border-ink-200/90 dark:border-ink-800 bg-white dark:bg-ink-900 hover:border-duck-400 dark:hover:border-duck-500/60 hover:bg-duck-50/50 dark:hover:bg-ink-800/80 transition-all text-left group shadow-2xs focus:outline-none focus:ring-2 focus:ring-duck-400"
          >
            <div className="flex items-center space-x-2 text-xs font-semibold text-ink-800 dark:text-ink-200 group-hover:text-duck-700 dark:group-hover:text-duck-300">
              {bug.icon}
              <span>{bug.title}</span>
            </div>
            <p className="mt-1 text-xs text-ink-500 dark:text-ink-400 font-mono truncate">
              {bug.snippet}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
};
