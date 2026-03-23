// Type definitions for the Empires Online game

export interface Player {
  id: number;
  username: string;
  email: string;
  email_verified: boolean;
  created_at: string;
}

export interface Country {
  id: number;
  name: string;
  default_gold: number;
  default_bonds: number;
  default_territories: number;
  default_goods: number;
  default_people: number;
}

export interface Game {
  id: number;
  rounds: number;
  rounds_remaining: number;
  phase: 'waiting' | 'development' | 'actions' | 'completed';
  creator_id: number;
  created_at: string;
  started_at?: string;
}

export interface SpawnedCountry {
  id: number;
  country_id: number;
  game_id: number;
  player_id: number;
  gold: number;
  bonds: number;
  territories: number;
  goods: number;
  people: number;
  banks: number;
  supporters: number;
  revolters: number;
  development_completed: boolean;
  actions_completed: boolean;
}

export interface SpawnedCountryWithDetails extends SpawnedCountry {
  country: Country;
  player: Player;
}

export interface GameState {
  game: Game;
  players: SpawnedCountryWithDetails[];
  leaderboard: LeaderboardEntry[];
  spectator_count?: number;
}

export interface LeaderboardEntry {
  player_id: number;
  player_name: string;
  country_name: string;
  score: number;
  breakdown: {
    base_score: number;
    territory_bonus: number;
    stability_bonus: number;
    economic_bonus: number;
    instability_penalty: boolean;
    total_before_penalty: number;
  };
}

export interface DevelopmentResult {
  success: boolean;
  new_state: {
    gold: number;
    supporters: number;
    revolters: number;
    goods: number;
  };
  changes: {
    before: any;
    after: any;
    calculations: any;
  };
}

export interface ActionResult {
  success: boolean;
  new_state?: any;
  changes?: any;
  error?: string;
}

export interface GameAction {
  action: string;
  quantity: number;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}

// Player stats and game history types

export interface PlayerStats {
  total_games: number;
  wins: number;
  losses: number;
  win_rate: number;
}

export interface GameHistoryEntry {
  game_id: number;
  placement: number;
  score: number;
  country_name: string;
  duration_rounds: number;
  finished_at: string;
}

export interface GlobalLeaderboardEntry {
  player_id: number;
  username: string;
  total_games: number;
  wins: number;
  win_rate: number;
  avg_placement: number;
}

export interface PlayerHistoryResponse {
  player_id: number;
  username: string;
  stats: PlayerStats;
  history: GameHistoryEntry[];
}

// WebSocket message types

// Shared payload types
export interface WsPlayerInfo {
  id: number;
  username: string;
}

// Client → Server messages
export interface WsPingMessage {
  type: 'ping';
}

export interface WsChatOutMessage {
  type: 'chat';
  message: string;
}

export type WsClientMessage = WsPingMessage | WsChatOutMessage;

// Server → Client messages
export interface WsPlayerJoinedMessage {
  type: 'player_joined';
  game_id: number;
  player: WsPlayerInfo;
}

export interface WsPlayerLeftMessage {
  type: 'player_left';
  game_id: number;
  player: WsPlayerInfo;
}

export interface WsGameStateUpdateMessage {
  type: 'game_state_update';
  game_id: number;
  game_state?: GameState;
}

export interface WsRoundChangedMessage {
  type: 'round_changed';
  game_id: number;
  round: number;
  phase: Game['phase'];
}

export interface WsChatInMessage {
  type: 'chat';
  game_id: number;
  player: WsPlayerInfo;
  message: string;
}

export interface WsPongMessage {
  type: 'pong';
}

export interface WsErrorMessage {
  type: 'error';
  message: string;
}

export type WsServerMessage =
  | WsPlayerJoinedMessage
  | WsPlayerLeftMessage
  | WsGameStateUpdateMessage
  | WsRoundChangedMessage
  | WsChatInMessage
  | WsPongMessage
  | WsErrorMessage;

// WebSocket connection status
export type WsConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';
