import React, { useEffect, useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { X, Trophy, BarChart2, CheckCircle, RefreshCw } from 'lucide-react';

import { useDuckStore } from '../store/useDuckStore';
import { fetchStats } from '../lib/api';
import { StatsResponse } from '../types';

export const StatsModal: React.FC = () => {
  const { isStatsOpen, setStatsOpen } = useDuckStore();
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchStats();
      setStats(data);
    } catch {
      setError('Could not fetch live hackathon statistics. The pond may be unreachable.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isStatsOpen) {
      loadData();
    }
  }, [isStatsOpen]);

  return (
    <Dialog.Root open={isStatsOpen} onOpenChange={setStatsOpen}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-xs z-50 animate-fade-in" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[92vw] max-w-xl max-h-[90vh] overflow-y-auto p-6 bg-white dark:bg-ink-900 rounded-3xl border border-ink-200 dark:border-ink-800 shadow-2xl z-50 focus:outline-none">
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-ink-100 dark:border-ink-800">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 rounded-xl bg-duck-400/20 text-duck-600 dark:text-duck-400">
                <BarChart2 className="w-5 h-5" />
              </div>
              <div>
                <Dialog.Title className="font-display text-lg font-bold text-ink-900 dark:text-ink-50">
                  Live Hackathon Results & Metrics
                </Dialog.Title>
                <p className="text-xs text-ink-500 dark:text-ink-400">
                  Aggregated in real-time by Amazon DynamoDB & CloudWatch EMF
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-1">
              <button
                onClick={loadData}
                disabled={loading}
                aria-label="Refresh stats"
                className="p-2 rounded-xl text-ink-500 hover:text-ink-900 dark:hover:text-ink-100 transition-colors"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </button>
              <Dialog.Close asChild>
                <button
                  aria-label="Close"
                  className="p-2 rounded-xl text-ink-500 hover:text-ink-900 dark:hover:text-ink-100 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </Dialog.Close>
            </div>
          </div>

          {/* Content */}
          <div className="mt-5 space-y-5">
            {loading && !stats ? (
              <div className="py-12 text-center text-sm text-ink-500">
                Retrieving live stats from AWS...
              </div>
            ) : error ? (
              <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-sm">
                {error}
              </div>
            ) : stats ? (
              <>
                {/* 4 Stats Cards */}
                <div className="grid grid-cols-2 gap-3.5">
                  <div className="p-4 rounded-2xl bg-parchment-100 dark:bg-ink-800/60 border border-ink-200/80 dark:border-ink-700/60">
                    <span className="text-xs text-ink-500 dark:text-ink-400 block mb-1">
                      Total Debugging Sessions
                    </span>
                    <span className="text-2xl sm:text-3xl font-display font-bold text-ink-900 dark:text-ink-50">
                      {stats.total_sessions}
                    </span>
                  </div>

                  <div className="p-4 rounded-2xl bg-parchment-100 dark:bg-ink-800/60 border border-ink-200/80 dark:border-ink-700/60">
                    <span className="text-xs text-ink-500 dark:text-ink-400 block mb-1">
                      Solved Without "Show Me"
                    </span>
                    <div className="flex items-baseline space-x-1">
                      <span className="text-2xl sm:text-3xl font-display font-bold text-emerald-600 dark:text-emerald-400">
                        {stats.solved_without_show_me_pct}%
                      </span>
                    </div>
                  </div>

                  <div className="p-4 rounded-2xl bg-parchment-100 dark:bg-ink-800/60 border border-ink-200/80 dark:border-ink-700/60">
                    <span className="text-xs text-ink-500 dark:text-ink-400 block mb-1">
                      Avg Questions to Solution
                    </span>
                    <span className="text-2xl sm:text-3xl font-display font-bold text-sky-600 dark:text-sky-400">
                      {stats.avg_questions}
                    </span>
                  </div>

                  <div className="p-4 rounded-2xl bg-parchment-100 dark:bg-ink-800/60 border border-ink-200/80 dark:border-ink-700/60">
                    <span className="text-xs text-ink-500 dark:text-ink-400 block mb-1">
                      Learner Approval Rate
                    </span>
                    <div className="flex items-baseline space-x-1">
                      <span className="text-2xl sm:text-3xl font-display font-bold text-amber-600 dark:text-amber-400">
                        {stats.thumbs_up_pct}%
                      </span>
                    </div>
                  </div>
                </div>

                {/* Visual Performance Gauge / Bar */}
                <div className="p-4 rounded-2xl border border-ink-200 dark:border-ink-800 bg-white dark:bg-ink-950/40 space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-ink-700 dark:text-ink-300 flex items-center space-x-1.5">
                      <Trophy className="w-4 h-4 text-duck-500" />
                      <span>Coaching Success Rate</span>
                    </span>
                    <span className="font-mono text-ink-500">
                      {stats.solved_without_show_me} of {stats.bugs_solved} solved autonomously
                    </span>
                  </div>

                  {/* Progress bar */}
                  <div className="w-full h-3 rounded-full bg-ink-100 dark:bg-ink-800 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-emerald-500 to-duck-400 transition-all duration-500"
                      style={{ width: `${Math.max(5, stats.solved_without_show_me_pct)}%` }}
                    />
                  </div>
                </div>

                {/* Proof Notes for article / hackathon judges */}
                <div className="p-3.5 rounded-xl bg-duck-500/10 border border-duck-400/30 text-xs text-ink-800 dark:text-ink-200 leading-relaxed space-y-1">
                  <div className="font-semibold text-duck-800 dark:text-duck-300 flex items-center space-x-1">
                    <CheckCircle className="w-3.5 h-3.5 text-duck-600 dark:text-duck-400" />
                    <span>AWS Architecture Verified</span>
                  </div>
                  <p>
                    All metrics shown above are continuously published via <strong>Amazon CloudWatch EMF</strong> and aggregated into <strong>Amazon DynamoDB</strong> via atomic <code>ADD</code> expressions with zero external dependencies.
                  </p>
                </div>
              </>
            ) : null}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
