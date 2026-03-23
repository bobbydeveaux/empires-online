import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import GlobalLeaderboard from './GlobalLeaderboard';

const mockGetGlobalLeaderboard = jest.fn();

jest.mock('../services/api', () => ({
  playersAPI: {
    getGlobalLeaderboard: (...args: any[]) => mockGetGlobalLeaderboard(...args),
  },
}));

const renderWithRouter = () => {
  return render(
    <MemoryRouter>
      <GlobalLeaderboard />
    </MemoryRouter>
  );
};

describe('GlobalLeaderboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders leaderboard entries', async () => {
    mockGetGlobalLeaderboard.mockResolvedValue([
      { player_id: 1, username: 'alice', games_played: 10, wins: 7, losses: 3, win_rate: 70.0 },
      { player_id: 2, username: 'bob', games_played: 8, wins: 4, losses: 4, win_rate: 50.0 },
    ]);

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText('alice')).toBeInTheDocument();
    });

    expect(screen.getByText('bob')).toBeInTheDocument();
    expect(screen.getByText('70%')).toBeInTheDocument();
    expect(screen.getByText('50%')).toBeInTheDocument();
  });

  it('shows empty state when no entries', async () => {
    mockGetGlobalLeaderboard.mockResolvedValue([]);
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText(/No completed games yet/)).toBeInTheDocument();
    });
  });

  it('shows error on API failure', async () => {
    mockGetGlobalLeaderboard.mockRejectedValue(new Error('Network error'));
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Failed to load leaderboard')).toBeInTheDocument();
    });
  });

  it('shows loading state initially', () => {
    mockGetGlobalLeaderboard.mockReturnValue(new Promise(() => {})); // never resolves
    renderWithRouter();

    expect(screen.getByText('Loading leaderboard...')).toBeInTheDocument();
  });
});
