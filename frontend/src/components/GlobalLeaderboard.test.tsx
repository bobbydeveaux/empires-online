import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import GlobalLeaderboard from './GlobalLeaderboard';

// Mock the API module
jest.mock('../services/api', () => ({
  playersAPI: {
    getGlobalLeaderboard: jest.fn(),
  },
}));

import { playersAPI } from '../services/api';
const mockGetLeaderboard = playersAPI.getGlobalLeaderboard as jest.Mock;

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe('GlobalLeaderboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows loading state initially', () => {
    mockGetLeaderboard.mockReturnValue(new Promise(() => {})); // never resolves
    renderWithRouter(<GlobalLeaderboard />);
    expect(screen.getByText('Loading leaderboard...')).toBeInTheDocument();
  });

  it('shows empty state when no games completed', async () => {
    mockGetLeaderboard.mockResolvedValue([]);
    renderWithRouter(<GlobalLeaderboard />);
    await waitFor(() => {
      expect(screen.getByText('No Games Completed Yet')).toBeInTheDocument();
    });
  });

  it('renders leaderboard entries', async () => {
    mockGetLeaderboard.mockResolvedValue([
      {
        player_id: 1,
        player_name: 'alice',
        games_played: 5,
        wins: 3,
        average_score: 24.5,
        best_score: 30,
      },
      {
        player_id: 2,
        player_name: 'bob',
        games_played: 4,
        wins: 1,
        average_score: 18.0,
        best_score: 22,
      },
    ]);

    renderWithRouter(<GlobalLeaderboard />);

    await waitFor(() => {
      expect(screen.getByText('alice')).toBeInTheDocument();
      expect(screen.getByText('bob')).toBeInTheDocument();
      expect(screen.getByText('60%')).toBeInTheDocument(); // alice win rate
      expect(screen.getByText('24.5')).toBeInTheDocument(); // alice avg
    });
  });

  it('shows error when API fails', async () => {
    mockGetLeaderboard.mockRejectedValue(new Error('Network error'));
    renderWithRouter(<GlobalLeaderboard />);
    await waitFor(() => {
      expect(screen.getByText('Failed to load leaderboard')).toBeInTheDocument();
    });
  });
});
