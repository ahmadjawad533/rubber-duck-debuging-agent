import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { DuckMascotState } from '../types';

interface DuckMascotProps {
  state?: DuckMascotState;
  size?: number;
  className?: string;
  onClick?: () => void;
}

export const DuckMascot: React.FC<DuckMascotProps> = ({
  state = 'idle',
  size = 120,
  className = '',
  onClick,
}) => {
  // Animation variants for head & body
  const bodyVariants = {
    idle: {
      y: [0, -3, 0],
      transition: { duration: 2.4, repeat: Infinity, ease: 'easeInOut' },
    },
    thinking: {
      y: [0, -5, 0],
      rotate: [-2, 3, -2],
      transition: { duration: 1.6, repeat: Infinity, ease: 'easeInOut' },
    },
    celebrating: {
      y: [0, -18, 0, -10, 0],
      scale: [1, 1.08, 1, 1.04, 1],
      transition: { duration: 0.9, repeat: Infinity, ease: 'easeInOut' },
    },
    napping: {
      y: [0, 2, 0],
      rotate: 4,
      transition: { duration: 3.5, repeat: Infinity, ease: 'easeInOut' },
    },
  };

  const wingVariants = {
    idle: { rotate: 0 },
    thinking: { rotate: [0, 4, 0], transition: { duration: 2, repeat: Infinity } },
    celebrating: {
      rotate: [-15, 25, -15],
      transition: { duration: 0.3, repeat: Infinity },
    },
    napping: { rotate: 0 },
  };

  const eyeBlinkVariants = {
    blink: {
      scaleY: [1, 0.1, 1],
      transition: { duration: 0.25, repeat: Infinity, repeatDelay: 3.5 },
    },
  };

  return (
    <div
      className={`relative inline-flex items-center justify-center select-none ${className}`}
      style={{ width: size, height: size }}
      onClick={onClick}
      role="img"
      aria-label={`Rubber Duck mascot in ${state} state`}
    >
      <motion.svg
        width={size}
        height={size}
        viewBox="0 0 160 160"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        animate={state}
        variants={bodyVariants}
        className="overflow-visible"
      >
        {/* Soft water pond ripple at base */}
        <ellipse
          cx="80"
          cy="142"
          rx="52"
          ry="10"
          className="fill-sky-400/20 dark:fill-sky-500/25"
        />

        {/* Duck Tail & Main Body */}
        <motion.path
          d="M 32 108 C 24 96 22 84 34 82 C 40 81 48 88 56 94 C 70 88 95 86 114 96 C 132 106 134 126 118 136 C 96 148 50 144 32 108 Z"
          fill="#FBBF24"
          stroke="#D97706"
          strokeWidth="3.5"
          strokeLinejoin="round"
        />

        {/* Wing */}
        <motion.path
          d="M 52 102 C 50 94 62 90 76 94 C 90 98 94 114 86 122 C 76 130 54 116 52 102 Z"
          fill="#F59E0B"
          stroke="#B45309"
          strokeWidth="3"
          strokeLinejoin="round"
          variants={wingVariants}
          style={{ originX: '60px', originY: '100px' }}
        />

        {/* Duck Neck and Head */}
        <motion.g
          animate={
            state === 'thinking'
              ? { rotate: [-6, 6, -6], transition: { duration: 1.8, repeat: Infinity } }
              : state === 'napping'
              ? { rotate: 8, y: 3 }
              : { rotate: 0 }
          }
          style={{ originX: '105px', originY: '75px' }}
        >
          {/* Head circle */}
          <circle
            cx="106"
            cy="62"
            r="30"
            fill="#FBBF24"
            stroke="#D97706"
            strokeWidth="3.5"
          />

          {/* Cheek blush */}
          <ellipse
            cx="98"
            cy="72"
            rx="5"
            ry="3.5"
            fill="#F59E0B"
            opacity="0.5"
          />

          {/* Duck Beak */}
          <path
            d="M 128 58 C 142 58 152 64 148 70 C 142 76 128 72 124 70 Z"
            fill="#FB923C"
            stroke="#EA580C"
            strokeWidth="3"
            strokeLinejoin="round"
          />

          {/* Eye State */}
          {state === 'napping' ? (
            /* Closed sleeping curved eyes */
            <path
              d="M 102 58 Q 108 65 114 58"
              fill="none"
              stroke="#451A03"
              strokeWidth="3"
              strokeLinecap="round"
            />
          ) : (
            /* Open awake eyes with blink and pupil */
            <motion.g variants={eyeBlinkVariants} animate="blink" style={{ originX: '108px', originY: '56px' }}>
              <circle cx="108" cy="56" r="6" fill="#1E293B" />
              <circle cx="110" cy="54" r="2.2" fill="#FFFFFF" />
            </motion.g>
          )}
        </motion.g>

        {/* State specific overlays */}
        {/* Celebrating Confetti/Sparkles */}
        {state === 'celebrating' && (
          <g className="animate-spin" style={{ transformOrigin: '80px 80px', animationDuration: '6s' }}>
            <circle cx="36" cy="40" r="3" fill="#10B981" />
            <polygon points="135,30 138,36 144,37 140,42 141,48 135,45 130,48 131,42 127,37 133,36" fill="#F59E0B" />
            <circle cx="140" cy="95" r="3.5" fill="#3B82F6" />
            <polygon points="25,75 27,80 32,80 28,84 30,89 25,86 20,89 22,84 18,80 23,80" fill="#EC4899" />
          </g>
        )}
      </motion.svg>

      {/* Floating thought bubble dots when thinking */}
      <AnimatePresence>
        {state === 'thinking' && (
          <motion.div
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="absolute -top-3 right-0 flex space-x-1.5 bg-white dark:bg-ink-800 border border-duck-300 dark:border-ink-700 rounded-full px-2.5 py-1 shadow-md"
          >
            <motion.span
              animate={{ scale: [0.7, 1.2, 0.7] }}
              transition={{ duration: 1, repeat: Infinity, delay: 0 }}
              className="w-2 h-2 rounded-full bg-duck-500 inline-block"
            />
            <motion.span
              animate={{ scale: [0.7, 1.2, 0.7] }}
              transition={{ duration: 1, repeat: Infinity, delay: 0.25 }}
              className="w-2 h-2 rounded-full bg-duck-500 inline-block"
            />
            <motion.span
              animate={{ scale: [0.7, 1.2, 0.7] }}
              transition={{ duration: 1, repeat: Infinity, delay: 0.5 }}
              className="w-2 h-2 rounded-full bg-duck-500 inline-block"
            />
          </motion.div>
        )}

        {/* Floating zZz when napping / error */}
        {state === 'napping' && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: [0, 1, 0], y: [-2, -22], x: [0, 10] }}
            transition={{ duration: 2.2, repeat: Infinity }}
            className="absolute -top-2 right-1 font-display font-bold text-amber-700 dark:text-amber-400 text-sm select-none"
          >
            zZz
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
