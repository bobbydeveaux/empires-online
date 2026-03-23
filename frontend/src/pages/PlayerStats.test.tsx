import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import PlayerStats from './PlayerStats';

const mockGetPlayerStats = jest.fn();
const mockGetGlobalLeaderboard = jest.fn();

jest.mock('../services/api', () => ({
  playersAPI: {
    getPlayerStats: (...args: any[]) => mockGetPlayerStats(...args),
    getGlobalLeaderboard: (...args: any[]) => mockGetGlobalLeaderboard(...args),
  },
}));

jest.mock('../hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: 1, username: 'testuser', email: 'test@test.com', email_verified: true, created_at: '2024-01-01' },
    loading: false,
  }),
}));

const renderWithRouter = (initialPath = '/stats') => {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/stats" element={<PlayerStats />} />
        <Route path="/stats/:playerId" element={<PlayerStats />} />
        <Route path="/lobby" element={<div>Lobby Page</div>} />
      </Routes>
    </MemoryRouter>
  );
};

const sampleStats = {
  player_id: 1,
  username: 'testuser',
  games_played: 5,
  wins: 3,
  losses: 2,
  win_rate: 60.0,
  history: [
    {
      game_id: 10,
      country_name: 'England',
      rounds: 5,
      placement: 1,
      won: true,
      finished_at: '2024-06-15T12:00:00',
    },
    {
      game_id: 8,
      country_name: 'France',
      rounds: 3,
      placement: 2,
      won: false,
      finished_at: '2024-06-10T12:00:00',
    },
  ],
};

describe('PlayerStats', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetPlayerStats.mockResolvedValue(sampleStats);
    mockGetGlobalLeaderboard.mockResolvedValue([]);
  });

  it('renders player stats overview', async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText("testuser's Stats")).toBeInTheDocument();
    });

    // Check stat values within stat-card elements
    const statCards = document.querySelectorAll('.stat-card');
    const statValues = Array.from(statCards).map(
      card => card.querySelector('.stat-value')?.textContent
    );
    expect(statValues).toEqual(['5', '3', '2', '60%']);
  });

  it('renders game history table', async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText('#10')).toBeInTheDocument();
    });

    expect(screen.getByText('England')).toBeInTheDocument();
    expect(screen.getByText('France')).toBeInTheDocument();
    expect(screen.getByText('Win')).toBeInTheDocument();
    expect(screen.getByText('Loss')).toBeInTheDocument();
  });

  it('shows error when stats fail to load', async () => {
    mockGetPlayerStats.mockRejectedValue(new Error('Network error'));
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Failed to load player stats')).toBeInTheDocument();
    });
  });

  it('switches to leaderboard tab', async () => {
    mockGetGlobalLeaderboard.mockResolvedValue([]);
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText("testuser's Stats")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText('Leaderboard'));

    await waitFor(() => {
      expect(screen.getByText('Global Leaderboard')).toBeInTheDocument();
    });
  });

  it('calls getPlayerStats with current user id by default', async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(mockGetPlayerStats).toHaveBeenCalledWith(1);
    });
  });

  it('calls getPlayerStats with URL param player id', async () => {
    renderWithRouter('/stats/42');

    await waitFor(() => {
      expect(mockGetPlayerStats).toHaveBeenCalledWith(42);
    });
  });

  it('has a back to lobby button', async () => {
    renderWithRouter();

    expect(screen.getByText('Back to Lobby')).toBeInTheDocument();
  });
});
