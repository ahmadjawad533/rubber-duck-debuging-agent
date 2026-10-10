import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { motion } from 'framer-motion';
import { ChatMessage as ChatMessageType } from '../types';
import { CodeBlock } from './CodeBlock';
import { Sparkles, ThumbsUp, ThumbsDown, CheckCircle2 } from 'lucide-react';
import { useDuckStore } from '../store/useDuckStore';

interface ChatMessageProps {
  message: ChatMessageType;
  isLatestDuckMessage?: boolean;
}

export const ChatMessageItem: React.FC<ChatMessageProps> = ({
  message,
  isLatestDuckMessage = false,
}) => {
  const isDuck = message.role === 'duck';
  const { recap, rated, rateSession } = useDuckStore();

  // Typewriter / word-by-word reveal effect for latest duck reply
  const words = message.content.split(' ');
  const [revealedWordCount, setRevealedWordCount] = useState(
    isLatestDuckMessage ? 1 : words.length
  );
  const isRevealing = isLatestDuckMessage && revealedWordCount < words.length;

  useEffect(() => {
    if (!isLatestDuckMessage) {
      setRevealedWordCount(words.length);
      return;
    }

    if (revealedWordCount < words.length) {
      const timer = setTimeout(() => {
        setRevealedWordCount((prev) => Math.min(prev + 1, words.length));
      }, 45); // Smooth natural reading cadence
      return () => clearTimeout(timer);
    }
  }, [revealedWordCount, words.length, isLatestDuckMessage]);

  const displayedContent = isDuck
    ? words.slice(0, revealedWordCount).join(' ')
    : message.content;

  const handleSkipReveal = () => {
    setRevealedWordCount(words.length);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={`flex flex-col my-3.5 ${isDuck ? 'items-start' : 'items-end'}`}
    >
      <div className={`flex items-start max-w-[92%] sm:max-w-[85%] ${isDuck ? 'space-x-3' : 'space-x-0'}`}>
        {/* Duck Avatar icon */}
        {isDuck && (
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-duck-400/20 border border-duck-400/40 flex items-center justify-center text-base select-none mt-1 shadow-sm">
            🦆
          </div>
        )}

        {/* Message Bubble */}
        <div
          onClick={isRevealing ? handleSkipReveal : undefined}
          className={`relative px-4 py-3 rounded-2xl text-sm sm:text-base leading-relaxed cursor-default transition-all ${
            isDuck
              ? 'bg-white dark:bg-ink-900 border border-ink-200/80 dark:border-ink-800 text-ink-900 dark:text-ink-100 shadow-sm rounded-tl-sm'
              : 'bg-duck-400/15 dark:bg-duck-500/20 border border-duck-400/30 text-ink-900 dark:text-ink-50 rounded-tr-sm'
          }`}
          title={isRevealing ? 'Click to skip reveal' : undefined}
        >
          {/* Header indicator for hints or solutions */}
          {isDuck && message.state === 'hint' && (
            <div className="flex items-center space-x-1.5 text-xs font-semibold text-amber-700 dark:text-amber-400 mb-1.5">
              <span>💡 A Gentle Nudge</span>
            </div>
          )}
          {isDuck && message.state === 'revealed' && (
            <div className="flex items-center space-x-1.5 text-xs font-semibold text-sky-700 dark:text-sky-400 mb-1.5">
              <span>🔍 Full Explanation & Fix</span>
            </div>
          )}
          {isDuck && message.state === 'solved' && (
            <div className="flex items-center space-x-1.5 text-xs font-semibold text-emerald-700 dark:text-emerald-400 mb-1.5">
              <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
              <span>Bug Solved!</span>
            </div>
          )}

          {/* Markdown Content */}
          <div className="prose dark:prose-invert prose-sm max-w-none break-words">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '');
                  const isInline = !match && !String(children).includes('\n');
                  if (isInline) {
                    return (
                      <code
                        className="px-1.5 py-0.5 rounded bg-ink-100 dark:bg-ink-800 text-amber-800 dark:text-duck-300 font-mono text-xs font-medium"
                        {...props}
                      >
                        {children}
                      </code>
                    );
                  }
                  return (
                    <CodeBlock
                      language={match ? match[1] : 'code'}
                      code={String(children).replace(/\n$/, '')}
                    />
                  );
                },
                p({ children }) {
                  return <p className="mb-2 last:mb-0">{children}</p>;
                },
              }}
            >
              {displayedContent}
            </ReactMarkdown>
          </div>

          {/* Skippable indicator hint */}
          {isRevealing && (
            <button
              onClick={handleSkipReveal}
              aria-label="Skip typing animation"
              className="mt-1 text-[11px] text-ink-400 hover:text-ink-600 dark:hover:text-ink-300 block select-none"
            >
              (Click to skip animation)
            </button>
          )}
        </div>
      </div>

      {/* Solved Recap Card & Rating Buttons */}
      {isDuck && message.state === 'solved' && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          className="mt-3 ml-11 p-4 rounded-xl border border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-950/20 text-ink-900 dark:text-ink-100 max-w-[92%] sm:max-w-[85%] shadow-sm"
        >
          <div className="flex items-center space-x-2 text-emerald-700 dark:text-emerald-400 font-semibold text-xs tracking-wider uppercase mb-1.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>What You Learned</span>
          </div>
          <p className="text-sm font-medium leading-relaxed text-ink-800 dark:text-ink-200">
            {message.recap || recap || 'Stepping through one assumption at a time reveals what assumptions were broken.'}
          </p>

          {/* Feedback Rating */}
          <div className="mt-3.5 pt-3 border-t border-emerald-500/20 flex items-center justify-between">
            <span className="text-xs text-ink-600 dark:text-ink-400">
              Did this coaching session help you learn?
            </span>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => rateSession('up')}
                disabled={rated !== null}
                aria-label="Helpful"
                className={`p-1.5 rounded-lg border transition-all ${
                  rated === 'up'
                    ? 'bg-emerald-500 text-white border-emerald-500'
                    : 'bg-white dark:bg-ink-800 border-ink-200 dark:border-ink-700 text-ink-600 dark:text-ink-300 hover:bg-emerald-50 dark:hover:bg-emerald-950/30'
                }`}
              >
                <ThumbsUp className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => rateSession('down')}
                disabled={rated !== null}
                aria-label="Not helpful"
                className={`p-1.5 rounded-lg border transition-all ${
                  rated === 'down'
                    ? 'bg-rose-500 text-white border-rose-500'
                    : 'bg-white dark:bg-ink-800 border-ink-200 dark:border-ink-700 text-ink-600 dark:text-ink-300 hover:bg-rose-50 dark:hover:bg-rose-950/30'
                }`}
              >
                <ThumbsDown className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
};
