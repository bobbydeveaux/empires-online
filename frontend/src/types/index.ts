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