import axios from 'axios';
import {
  Player,
  Country,
  Game,
  GameState,
  DevelopmentResult,
  ActionResult,
  GameAction,
  LeaderboardEntry,
  AuthToken,
  TradeOffer,
  TradePropose,
} from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

/**
 * Build a WebSocket URL for a given game room.
 * Derives ws:// or wss:// from the current page protocol.
 */
export function getWebSocketUrl(gameId: number, token: string): string {
  const wsBase = process.env.REACT_APP_WS_URL;
  if (wsBase) {
    return `${wsBase}/ws/${gameId}?token=${encodeURIComponent(token)}`;
  }
  // Derive from current location
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}/ws/${gameId}?token=${encodeURIComponent(token)}`;
}

const api = axios.create({
  baseURL: API_BASE_URL,
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth API
export const authAPI = {
  register: async (username: string, email: string, password: string): Promise<Player> => {
    const response = await api.post('/auth/register', { username, email, password });
    return response.data;
  },

  login: async (username: string, password: string): Promise<AuthToken> => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await api.post('/auth/token', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },

  getCurrentUser: async (): Promise<Player> => {
    const response = await api.get('/auth/me');
    return response.data;
  }
};

// Players API
export const playersAPI = {
  getCountries: async (): Promise<Country[]> => {
    const response = await api.get('/players/countries');
    return response.data;
  },

  getCurrentPlayer: async (): Promise<Player> => {
    const response = await api.get('/players/me');
    return response.data;
  }
};

// Games API
export const gamesAPI = {
  createGame: async (rounds: number, countries: string[]): Promise<Game> => {
    const response = await api.post('/games/', { rounds, countries });
    return response.data;
  },

  listGames: async (): Promise<Game[]> => {
    const response = await api.get('/games/');
    return response.data;
  },

  getGameState: async (gameId: number): Promise<GameState> => {
    const response = await api.get(`/games/${gameId}`);
    return response.data;
  },

  joinGame: async (gameId: number, countryId: number): Promise<{ spawned_country_id: number; message: string }> => {
    const response = await api.post(`/games/${gameId}/join`, { country_id: countryId });
    return response.data;
  },

  startGame: async (gameId: number): Promise<{ status: string; current_phase: string }> => {
    const response = await api.post(`/games/${gameId}/start`);
    return response.data;
  },

  executeDevelopment: async (gameId: number, spawnedCountryId: number): Promise<DevelopmentResult> => {
    const response = await api.post(`/games/${gameId}/countries/${spawnedCountryId}/develop`);
    return response.data;
  },

  performAction: async (gameId: number, spawnedCountryId: number, action: GameAction): Promise<ActionResult> => {
    const response = await api.post(`/games/${gameId}/countries/${spawnedCountryId}/actions`, action);
    return response.data;
  },

  nextRound: async (gameId: number): Promise<{ message: string; phase: string }> => {
    const response = await api.post(`/games/${gameId}/next-round`);
    return response.data;
  },

  getLeaderboard: async (gameId: number): Promise<LeaderboardEntry[]> => {
    const response = await api.get(`/games/${gameId}/leaderboard`);
    return response.data;
  },

  // Trade endpoints
  listTrades: async (gameId: number): Promise<TradeOffer[]> => {
    const response = await api.get(`/games/${gameId}/trades`);
    return response.data;
  },

  proposeTrade: async (gameId: number, trade: TradePropose): Promise<TradeOffer> => {
    const response = await api.post(`/games/${gameId}/trades`, trade);
    return response.data;
  },

  acceptTrade: async (gameId: number, tradeId: number): Promise<TradeOffer> => {
    const response = await api.post(`/games/${gameId}/trades/${tradeId}/accept`);
    return response.data;
  },

  rejectTrade: async (gameId: number, tradeId: number): Promise<TradeOffer> => {
    const response = await api.post(`/games/${gameId}/trades/${tradeId}/reject`);
    return response.data;
  },

  cancelTrade: async (gameId: number, tradeId: number): Promise<TradeOffer> => {
    const response = await api.post(`/games/${gameId}/trades/${tradeId}/cancel`);
    return response.data;
  },
};

// WebSocket URL builder
export function buildWebSocketUrl(gameId: number): string {
  const token = localStorage.getItem('authToken');

  // Determine base: use the configured API base or derive from window.location
  let wsBase: string;

  if (API_BASE_URL.startsWith('http://') || API_BASE_URL.startsWith('https://')) {
    // Absolute URL configured — convert http(s) to ws(s)
    wsBase = API_BASE_URL.replace(/^http/, 'ws');
  } else {
    // Relative path (e.g. "/api") — derive from current page origin
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    wsBase = `${protocol}//${window.location.host}`;
  }

  // Remove trailing slash
  wsBase = wsBase.replace(/\/$/, '');

  // The WS endpoint is at /ws/{game_id}, not under /api
  // Strip the /api suffix if present so we hit the root-level /ws route
  wsBase = wsBase.replace(/\/api$/, '');

  let url = `${wsBase}/ws/${gameId}`;
  if (token) {
    url += `?token=${encodeURIComponent(token)}`;
  }
  return url;
}

export default api;