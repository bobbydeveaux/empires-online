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
  AuthToken
} from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

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
  }
};

export default api;