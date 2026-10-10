import React, { useState } from 'react';
import { Sun, Moon, Flame, BarChart3, RotateCcw, PanelRight } from 'lucide-react';
import { useDuckStore } from '../store/useDuckStore';
import * as Dialog from '@radix-ui/react-dialog';

export const Header: React.FC = () => {
  const {
    streak,
    theme,
    setTheme,
    startNewChat,
    setStatsOpen,
    toggleSidePanel,
    messages,
  } = useDuckStore();

  const [confirmOpen, setConfirmOpen] = useState(false);

  const toggleTheme = () => {
    if (theme === 'light') setTheme('dark');
    else if (theme === 'dark') setTheme('system');
    else setTheme('light');
  };

  const handleNewChatClick = () => {
    if (messages.length > 0) {
      setConfirmOpen(true);
    } else {
      startNewChat();
    }
  };

  return (
    <header className="sticky top-0 z-30 w-full border-b border-ink-200/80 dark:border-ink-800 bg-white/80 dark:bg-ink-950/80 backdrop-blur-md transition-colors">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-2.5">
          <span className="text-2xl select-none" role="img" aria-label="Duck">
            🦆
          </span>
          <div>
            <h1 className="font-display font-bold text-lg leading-tight tracking-tight text-ink-900 dark:text-ink-50">
              Rubber Duck
            </h1>
            <p className="text-[11px] text-ink-500 dark:text-ink-400 -mt-0.5 hidden sm:block">
              Socratic AI Debugging Companion
            </p>
          </div>
        </div>

        {/* Center / Right controls */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          {/* Streak Badge */}
          <div
            title="Solved without asking for the answer"
            className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-700 dark:text-amber-300 text-xs font-semibold select-none shadow-2xs"
          >
            <Flame className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
            <span>{streak}</span>
            <span className="hidden md:inline font-normal">streak</span>
          </div>

          {/* Stats Button */}
          <button
            onClick={() => setStatsOpen(true)}
            aria-label="View Live Hackathon Stats"
            className="p-2 rounded-xl text-ink-600 dark:text-ink-300 hover:bg-ink-100 dark:hover:bg-ink-800 transition-colors focus:outline-none focus:ring-2 focus:ring-duck-400"
          >
            <BarChart3 className="w-4 h-4" />
          </button>

          {/* New Chat Button */}
          <button
            onClick={handleNewChatClick}
            aria-label="Start new chat session"
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border border-ink-200 dark:border-ink-800 text-ink-700 dark:text-ink-200 hover:bg-ink-50 dark:hover:bg-ink-900 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-duck-400"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">New Chat</span>
          </button>

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            aria-label={`Toggle theme (current: ${theme})`}
            className="p-2 rounded-xl text-ink-600 dark:text-ink-300 hover:bg-ink-100 dark:hover:bg-ink-800 transition-colors focus:outline-none focus:ring-2 focus:ring-duck-400"
          >
            {theme === 'dark' ? (
              <Moon className="w-4 h-4 text-duck-300" />
            ) : (
              <Sun className="w-4 h-4 text-amber-500" />
            )}
          </button>

          {/* Desktop Side Panel Toggle */}
          <button
            onClick={toggleSidePanel}
            aria-label="Toggle Session Side Panel"
            className="hidden lg:flex p-2 rounded-xl text-ink-600 dark:text-ink-300 hover:bg-ink-100 dark:hover:bg-ink-800 transition-colors focus:outline-none focus:ring-2 focus:ring-duck-400"
          >
            <PanelRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Confirmation Dialog for New Chat */}
      <Dialog.Root open={confirmOpen} onOpenChange={setConfirmOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/40 backdrop-blur-xs z-50 animate-fade-in" />
          <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[90vw] max-w-md p-6 bg-white dark:bg-ink-900 rounded-2xl border border-ink-200 dark:border-ink-800 shadow-xl z-50 focus:outline-none">
            <Dialog.Title className="font-display text-lg font-bold text-ink-900 dark:text-ink-100">
              Start a new debugging session?
            </Dialog.Title>
            <Dialog.Description className="mt-2 text-sm text-ink-600 dark:text-ink-400">
              Quack! Your current session history will be archived. Your solved streak of{' '}
              <strong className="text-amber-600 dark:text-amber-400">{streak}</strong> will be preserved.
            </Dialog.Description>

            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => setConfirmOpen(false)}
                className="px-4 py-2 rounded-xl text-sm font-medium text-ink-700 dark:text-ink-300 hover:bg-ink-100 dark:hover:bg-ink-800 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setConfirmOpen(false);
                  startNewChat();
                }}
                className="px-4 py-2 rounded-xl text-sm font-medium bg-duck-400 hover:bg-duck-500 text-ink-950 transition-colors shadow-xs"
              >
                Yes, Start New
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </header>
  );
};
