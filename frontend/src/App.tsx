import React, { useEffect, useRef } from 'react';
import { useDuckStore } from './store/useDuckStore';
import { Header } from './components/Header';
import { OfflineBanner } from './components/OfflineBanner';
import { EmptyState } from './components/EmptyState';
import { ChatMessageItem } from './components/ChatMessage';
import { Composer } from './components/Composer';
import { SessionPanel } from './components/SessionPanel';
import { StatsModal } from './components/StatsModal';
import { ErrorAlert } from './components/ErrorAlert';
import { DuckMascot } from './components/DuckMascot';

export const App: React.FC = () => {
  const {
    messages,
    duckState,
    theme,
    isSidePanelOpen,
    startNewChat,
  } = useDuckStore();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Sync dark class on document element
  useEffect(() => {
    const root = document.documentElement;
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const applyTheme = () => {
      if (theme === 'dark' || (theme === 'system' && mediaQuery.matches)) {
        root.classList.add('dark');
      } else {
        root.classList.remove('dark');
      }
    };

    applyTheme();
    mediaQuery.addEventListener('change', applyTheme);
    return () => mediaQuery.removeEventListener('change', applyTheme);
  }, [theme]);

  // Keyboard shortcut: Cmd/Ctrl + K to start new chat
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        startNewChat();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [startNewChat]);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, duckState]);

  return (
    <div className="flex flex-col min-h-screen bg-parchment-50 dark:bg-ink-950 text-ink-900 dark:text-ink-50 transition-colors">
      <OfflineBanner />
      <Header />

      <div className="flex-1 flex max-w-6xl w-full mx-auto overflow-hidden">
        {/* Main Chat Area */}
        <main className="flex-1 flex flex-col h-[calc(100vh-4rem)] max-w-3xl mx-auto w-full">
          {/* Scrollable Chat Stream */}
          <div className="flex-1 overflow-y-auto px-4 py-6 scroll-smooth">
            {(messages ?? []).length === 0 ? (
              <EmptyState />
            ) : (
              <div className="space-y-1">
                {(messages ?? []).map((msg, index) => {
                  const isLatestDuck =
                    msg?.role === 'duck' &&
                    index === (messages ?? []).length - 1;
                  return (
                    <ChatMessageItem
                      key={msg?.id ?? index}
                      message={msg}
                      isLatestDuckMessage={isLatestDuck}
                    />
                  );
                })}

                {/* Thinking typing indicator */}
                {duckState === 'thinking' && (
                  <div className="flex items-center space-x-3 my-4 animate-fade-in">
                    <DuckMascot state="thinking" size={38} className="flex-shrink-0" />
                    <div className="px-4 py-2.5 rounded-2xl bg-white dark:bg-ink-900 border border-ink-200 dark:border-ink-800 text-xs text-ink-500 dark:text-ink-400 italic shadow-2xs">
                      The duck is bobbing and pondering your code...
                    </div>
                  </div>
                )}

                {/* Error Banner with Retry */}
                <ErrorAlert />

                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* Fixed Composer at bottom */}
          <Composer />
        </main>

        {/* Collapsible Session Side Panel on Desktop */}
        {isSidePanelOpen && <SessionPanel />}
      </div>

      <StatsModal />
    </div>
  );
};

export default App;
