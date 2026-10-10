export type DuckMascotState = 'idle' | 'thinking' | 'celebrating' | 'napping';

export type ResponseState = 'asking' | 'hint' | 'solved' | 'revealed';

export interface ChatMessage {
  id: string;
  role: 'user' | 'duck';
  content: string;
  timestamp: number;
  state?: ResponseState;
  recap?: string;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  state: ResponseState;
  streak: number;
  hints_used: number;
  question_count: number;
  recap?: string;
}

export interface StatsResponse {
  total_sessions: number;
  bugs_solved: number;
  solved_without_show_me: number;
  solved_without_show_me_pct: number;
  avg_questions: number;
  total_ratings: number;
  positive_ratings: number;
  thumbs_up_pct: number;
}

export interface SessionInfo {
  sessionId: string;
  streak: number;
  hintsUsed: number;
  questionCount: number;
  solved: boolean;
  rated?: 'up' | 'down';
}
