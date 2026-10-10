import { ChatResponse, StatsResponse } from '../types';

const rawApiUrl = import.meta.env.VITE_API_URL;
const API_BASE_URL = (rawApiUrl ? String(rawApiUrl).trim() : '/api').replace(/\/+$/, '');

export class DuckApiError extends Error {
  code: string;
  statusCode?: number;

  constructor(message: string, code = 'UNKNOWN_ERROR', statusCode?: number) {
    super(message);
    this.name = 'DuckApiError';
    this.code = code;
    this.statusCode = statusCode;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });

    if (res.status === 429) {
      throw new DuckApiError(
        'The duck is still digesting your last thought. Wait a brief second.',
        'RATE_LIMIT',
        429
      );
    }

    if (!res.ok) {
      let errorMsg = 'The duck is napping. Try again in a few seconds.';
      let code = 'SERVER_ERROR';
      try {
        const errorJson = await res.json();
        if (errorJson.message) errorMsg = errorJson.message;
        if (errorJson.error) code = errorJson.error;
      } catch {
        // use default message
      }
      console.error(`[Rubber Duck API HTTP ${res.status}]`, {
        endpoint,
        url,
        status: res.status,
        statusText: res.statusText,
        error: errorMsg,
      });
      throw new DuckApiError(errorMsg, code, res.status);
    }

    return (await res.json()) as T;
  } catch (err: unknown) {
    if (err instanceof DuckApiError) {
      throw err;
    }
    // Fetch failed due to network / CORS / offline - print detailed real cause to browser console
    console.error('[Rubber Duck API Network/CORS Error]', {
      endpoint,
      url,
      apiBaseUrl: API_BASE_URL,
      cause: err,
      message: err instanceof Error ? err.message : String(err),
      stack: err instanceof Error ? err.stack : undefined,
    });
    throw new DuckApiError(
      'The duck could not reach the pond. Please check your internet connection.',
      'NETWORK_ERROR'
    );
  }
}

export async function sendChatMessage(
  sessionId: string,
  message: string
): Promise<ChatResponse> {
  return request<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, message }),
  });
}

export async function sendRating(
  sessionId: string,
  rating: 'up' | 'down'
): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>('/rate', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, rating }),
  });
}

export async function fetchStats(): Promise<StatsResponse> {
  return request<StatsResponse>('/stats', {
    method: 'GET',
  });
}

export async function checkHealth(): Promise<{ status: string }> {
  return request<{ status: string }>('/health', {
    method: 'GET',
  });
}
