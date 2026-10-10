import { create } from 'zustand';
import { ChatMessage, DuckMascotState, ResponseState } from '../types';
import { generateId } from '../lib/utils';
import { sendChatMessage, sendRating, DuckApiError } from '../lib/api';
import confetti from 'canvas-confetti';

interface DuckStore {
  sessionId: string;
  messages: ChatMessage[];
  duckState: DuckMascotState;
  streak: number;
  hintsUsed: number;
  questionCount: number;
  isSolved: boolean;
  recap: string | null;
  theme: 'light' | 'dark' | 'system';
  isCodeMode: boolean;
  isSidePanelOpen: boolean;
  isStatsOpen: boolean;
  isOnline: boolean;
  errorMessage: string | null;
  lastUserMessage: string | null;
  rated: 'up' | 'down' | null;

  // Actions
  sendMessage: (text: string) => Promise<void>;
  retryLastMessage: () => Promise<void>;
  triggerHint: () => Promise<void>;
  triggerShowMe: () => Promise<void>;
  markFoundIt: () => Promise<void>;
  rateSession: (rating: 'up' | 'down') => Promise<void>;
  startNewChat: () => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  toggleCodeMode: () => void;
  toggleSidePanel: () => void;
  setStatsOpen: (open: boolean) => void;
  setOnline: (online: boolean) => void;
}

const STORAGE_KEY = 'rubber_duck_session_v1';

function loadPersistedState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      return JSON.parse(raw);
    }
  } catch (e) {
    console.warn('Failed to load local storage session:', e);
  }
  return null;
}

function saveStateToStorage(state: Partial<DuckStore>) {
  try {
    const toSave = {
      sessionId: state.sessionId,
      messages: state.messages,
      streak: state.streak,
      hintsUsed: state.hintsUsed,
      questionCount: state.questionCount,
      isSolved: state.isSolved,
      recap: state.recap,
      theme: state.theme,
      rated: state.rated,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
  } catch (e) {
    console.warn('Failed to persist session to local storage:', e);
  }
}

const initialSaved = loadPersistedState();
const initialSessionId = initialSaved?.sessionId || generateId();
const initialStreak = initialSaved?.streak || 0;

export const useDuckStore = create<DuckStore>((set, get) => ({
  sessionId: initialSessionId,
  messages: initialSaved?.messages || [],
  duckState: 'idle',
  streak: initialStreak,
  hintsUsed: initialSaved?.hintsUsed || 0,
  questionCount: initialSaved?.questionCount || 0,
  isSolved: initialSaved?.isSolved || false,
  recap: initialSaved?.recap || null,
  theme: initialSaved?.theme || 'system',
  isCodeMode: false,
  isSidePanelOpen: true,
  isStatsOpen: false,
  isOnline: navigator.onLine,
  errorMessage: null,
  lastUserMessage: null,
  rated: initialSaved?.rated || null,

  sendMessage: async (text: string) => {
    const clean = text.trim();
    if (!clean) return;

    const { sessionId, messages, isSolved } = get();

    // Optimistic user message
    const userMsg: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: clean,
      timestamp: Date.now(),
    };

    set({
      messages: [...messages, userMsg],
      duckState: 'thinking',
      errorMessage: null,
      lastUserMessage: clean,
    });

    try {
      const resp = await sendChatMessage(sessionId, clean);

      const duckMsg: ChatMessage = {
        id: generateId(),
        role: 'duck',
        content: resp.reply,
        timestamp: Date.now(),
        state: resp.state as ResponseState,
        recap: resp.recap,
      };

      const nowSolved = resp.state === 'solved';
      const newDuckState: DuckMascotState = nowSolved ? 'celebrating' : 'idle';

      if (nowSolved && !isSolved) {
        // Trigger celebratory confetti burst
        try {
          confetti({
            particleCount: 80,
            spread: 70,
            origin: { y: 0.6 },
            colors: ['#F59E0B', '#FBBF24', '#10B981', '#3B82F6'],
          });
        } catch {
          // ignore if canvas-confetti unsupported
        }
      }

      set((state) => {
        const nextState = {
          messages: [...state.messages, duckMsg],
          duckState: newDuckState,
          streak: resp.streak,
          hintsUsed: resp.hints_used,
          questionCount: resp.question_count,
          isSolved: state.isSolved || nowSolved,
          recap: resp.recap || state.recap,
          errorMessage: null,
        };
        saveStateToStorage({ ...state, ...nextState });
        return nextState;
      });
    } catch (err: unknown) {
      let msg = 'The duck is napping. Try again in a few seconds.';
      if (err instanceof DuckApiError) {
        msg = err.message;
      }
      set({
        duckState: 'napping',
        errorMessage: msg,
      });
    }
  },

  retryLastMessage: async () => {
    const { lastUserMessage, sendMessage } = get();
    if (lastUserMessage) {
      await sendMessage(lastUserMessage);
    }
  },

  triggerHint: async () => {
    await get().sendMessage('hint');
  },

  triggerShowMe: async () => {
    await get().sendMessage('show me');
  },

  markFoundIt: async () => {
    await get().sendMessage('I found it!');
  },

  rateSession: async (rating: 'up' | 'down') => {
    const { sessionId } = get();
    try {
      await sendRating(sessionId, rating);
      set({ rated: rating });
      saveStateToStorage({ ...get(), rated: rating });
    } catch (err) {
      console.warn('Failed to submit rating:', err);
    }
  },

  startNewChat: () => {
    const nextSessionId = generateId();
    const currentStreak = get().streak;
    const newState = {
      sessionId: nextSessionId,
      messages: [],
      duckState: 'idle' as DuckMascotState,
      hintsUsed: 0,
      questionCount: 0,
      isSolved: false,
      recap: null,
      errorMessage: null,
      lastUserMessage: null,
      rated: null,
      streak: currentStreak,
    };
    set(newState);
    saveStateToStorage({ ...get(), ...newState });
  },

  setTheme: (theme: 'light' | 'dark' | 'system') => {
    set({ theme });
    saveStateToStorage({ ...get(), theme });
  },

  toggleCodeMode: () => {
    set((state) => ({ isCodeMode: !state.isCodeMode }));
  },

  toggleSidePanel: () => {
    set((state) => ({ isSidePanelOpen: !state.isSidePanelOpen }));
  },

  setStatsOpen: (open: boolean) => {
    set({ isStatsOpen: open });
  },

  setOnline: (online: boolean) => {
    set({ isOnline: online });
  },
}));
