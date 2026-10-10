import React, { useState, useRef, useEffect } from 'react';
import { Send, Code2, Sparkles, HelpCircle, Eye } from 'lucide-react';
import { useDuckStore } from '../store/useDuckStore';

const MAX_CHAR_LIMIT = 4000;

export const Composer: React.FC = () => {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const {
    duckState,
    isCodeMode,
    toggleCodeMode,
    sendMessage,
    triggerHint,
    triggerShowMe,
    markFoundIt,
    isSolved,
  } = useDuckStore();

  const isThinking = duckState === 'thinking';

  // Auto-grow textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(scrollHeight, 220)}px`;
    }
  }, [text]);

  const handleSend = async () => {
    if (!text.trim() || isThinking) return;
    const msg = text;
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    await sendMessage(msg);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-4 pt-2">
      {/* Quick Action Chips */}
      <div className="flex items-center space-x-2 mb-2 overflow-x-auto no-scrollbar py-1">
        <button
          onClick={triggerHint}
          disabled={isThinking}
          aria-label="Ask for a hint"
          className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-medium border border-duck-300 dark:border-ink-700 bg-white dark:bg-ink-900 text-ink-700 dark:text-ink-200 hover:bg-duck-50 dark:hover:bg-ink-800 disabled:opacity-50 transition-colors shadow-xs flex-shrink-0"
        >
          <HelpCircle className="w-3.5 h-3.5 text-duck-600 dark:text-duck-400" />
          <span>Hint</span>
        </button>

        <button
          onClick={triggerShowMe}
          disabled={isThinking}
          aria-label="Request the full explanation and fix"
          className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-medium border border-duck-300 dark:border-ink-700 bg-white dark:bg-ink-900 text-ink-700 dark:text-ink-200 hover:bg-duck-50 dark:hover:bg-ink-800 disabled:opacity-50 transition-colors shadow-xs flex-shrink-0"
        >
          <Eye className="w-3.5 h-3.5 text-sky-600 dark:text-sky-400" />
          <span>Show me</span>
        </button>

        <button
          onClick={markFoundIt}
          disabled={isThinking || isSolved}
          aria-label="Mark bug as solved"
          className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-medium border border-emerald-300 dark:border-emerald-800/80 bg-white dark:bg-ink-900 text-emerald-800 dark:text-emerald-300 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 disabled:opacity-50 transition-colors shadow-xs flex-shrink-0"
        >
          <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
          <span>I found it!</span>
        </button>

        <button
          onClick={toggleCodeMode}
          aria-label={isCodeMode ? 'Switch to text mode' : 'Switch to code paste mode'}
          className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-colors shadow-xs flex-shrink-0 ml-auto ${
            isCodeMode
              ? 'bg-ink-900 text-duck-300 border-ink-800 dark:bg-duck-400/20 dark:text-duck-300 dark:border-duck-400/50'
              : 'bg-white dark:bg-ink-900 text-ink-600 dark:text-ink-300 border-ink-200 dark:border-ink-700 hover:bg-ink-50 dark:hover:bg-ink-800'
          }`}
        >
          <Code2 className="w-3.5 h-3.5" />
          <span>{isCodeMode ? 'Code Mode (Monospace)' : 'Paste Code'}</span>
        </button>
      </div>

      {/* Textarea Input Container */}
      <div className="relative rounded-2xl border border-ink-300 dark:border-ink-700 bg-white dark:bg-ink-900 shadow-sm focus-within:ring-2 focus-within:ring-duck-400 focus-within:border-transparent transition-all">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value.slice(0, MAX_CHAR_LIMIT))}
          onKeyDown={handleKeyDown}
          disabled={isThinking}
          placeholder={
            isCodeMode
              ? '// Paste your error stack trace or broken function here...'
              : "Describe what's breaking, or paste your error message..."
          }
          rows={1}
          aria-label="Debug message composer"
          className={`w-full resize-none bg-transparent px-4 py-3.5 pr-24 text-sm sm:text-base text-ink-900 dark:text-ink-100 placeholder:text-ink-400 dark:placeholder:text-ink-500 focus:outline-none max-h-56 leading-relaxed ${
            isCodeMode ? 'font-mono text-xs sm:text-sm' : 'font-sans'
          }`}
        />

        {/* Bottom controls inside container */}
        <div className="absolute right-3 bottom-3 flex items-center space-x-2">
          {/* Character counter */}
          <span
            className={`text-[11px] font-mono select-none ${
              text.length > MAX_CHAR_LIMIT - 200
                ? 'text-rose-500 font-bold'
                : 'text-ink-400 dark:text-ink-500'
            }`}
          >
            {text.length}/{MAX_CHAR_LIMIT}
          </span>

          {/* Send button */}
          <button
            onClick={handleSend}
            disabled={!text.trim() || isThinking}
            aria-label="Send message to duck"
            className="p-2 rounded-xl bg-duck-400 text-ink-950 hover:bg-duck-500 disabled:opacity-40 disabled:hover:bg-duck-400 transition-colors shadow-xs focus:outline-none focus:ring-2 focus:ring-duck-500"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
      <div className="flex justify-between items-center px-1 mt-1 text-[11px] text-ink-400 dark:text-ink-500">
        <span>Press Enter to send, Shift+Enter for a new line</span>
        <span>The duck asks one question at a time</span>
      </div>
    </div>
  );
};
