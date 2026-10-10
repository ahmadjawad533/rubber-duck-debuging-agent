import React from 'react';
import { HelpCircle, MessageSquare, Flame, CheckCircle, ShieldCheck } from 'lucide-react';
import { useDuckStore } from '../store/useDuckStore';

export const SessionPanel: React.FC = () => {
  const { questionCount, hintsUsed, streak, isSolved } = useDuckStore();

  return (
    <aside className="w-80 flex-shrink-0 border-l border-ink-200/80 dark:border-ink-800 bg-white/50 dark:bg-ink-950/40 p-5 space-y-6 hidden lg:block overflow-y-auto">
      {/* Session Card */}
      <div className="bg-white dark:bg-ink-900 rounded-2xl border border-ink-200/80 dark:border-ink-800 p-4 shadow-2xs">
        <h3 className="font-display font-semibold text-sm text-ink-900 dark:text-ink-100 flex items-center space-x-2">
          <span>Session Overview</span>
        </h3>

        <div className="mt-4 space-y-3">
          <div className="flex items-center justify-between text-xs">
            <span className="text-ink-500 dark:text-ink-400 flex items-center space-x-1.5">
              <MessageSquare className="w-3.5 h-3.5" />
              <span>Questions Asked</span>
            </span>
            <span className="font-semibold text-ink-800 dark:text-ink-200">
              {questionCount}
            </span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className="text-ink-500 dark:text-ink-400 flex items-center space-x-1.5">
              <HelpCircle className="w-3.5 h-3.5" />
              <span>Hints Used</span>
            </span>
            <span className="font-semibold text-ink-800 dark:text-ink-200">
              {hintsUsed}
            </span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className="text-ink-500 dark:text-ink-400 flex items-center space-x-1.5">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Current Status</span>
            </span>
            <span
              className={`font-semibold ${
                isSolved
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : 'text-amber-600 dark:text-amber-400'
              }`}
            >
              {isSolved ? 'Solved! 🎉' : 'In Progress'}
            </span>
          </div>
        </div>
      </div>

      {/* Streak Showcase */}
      <div className="bg-gradient-to-br from-amber-500/10 via-amber-400/5 to-transparent rounded-2xl border border-amber-500/20 p-4 shadow-2xs">
        <div className="flex items-center justify-between">
          <span className="text-xs uppercase font-semibold text-amber-700 dark:text-amber-400 tracking-wider">
            Debugging Streak
          </span>
          <Flame className="w-4 h-4 text-amber-500 fill-amber-500" />
        </div>
        <div className="mt-2 flex items-baseline space-x-2">
          <span className="text-3xl font-display font-bold text-ink-900 dark:text-ink-50">
            {streak}
          </span>
          <span className="text-xs text-ink-500 dark:text-ink-400">
            bugs solved without asking for the fix
          </span>
        </div>
        <p className="mt-3 text-xs text-ink-600 dark:text-ink-400 italic">
          "A bug discovered by yourself is an error you'll never make twice."
        </p>
      </div>

      {/* Socratic Rubber Ducking Rules */}
      <div className="bg-white dark:bg-ink-900 rounded-2xl border border-ink-200/80 dark:border-ink-800 p-4 shadow-2xs">
        <h4 className="font-display font-semibold text-xs text-ink-900 dark:text-ink-100 flex items-center space-x-1.5 uppercase tracking-wider">
          <CheckCircle className="w-3.5 h-3.5 text-duck-500" />
          <span>The Duck's Method</span>
        </h4>
        <ul className="mt-3 space-y-2 text-xs text-ink-600 dark:text-ink-400 leading-relaxed">
          <li>• Answer each question truthfully based on your actual runtime values.</li>
          <li>• Don't guess what the code does; inspect what actually happened.</li>
          <li>• Need a nudge? Type <code className="text-amber-700 dark:text-amber-300 font-mono">hint</code>.</li>
          <li>• Genuinely stuck? Type <code className="text-sky-700 dark:text-sky-300 font-mono">show me</code>.</li>
        </ul>
      </div>
    </aside>
  );
};
