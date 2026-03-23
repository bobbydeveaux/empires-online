import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PlayerStatsData } from '../types';
import { playersAPI } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import GlobalLeaderboard from '../components/GlobalLeaderboard';

const PlayerStats: React.FC = () => {
  const { playerId } = useParams<{ playerId?: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState<PlayerStatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'stats' | 'leaderboard'>('stats');

  const resolvedPlayerId = playerId ? parseInt(playerId, 10) : user?.id;

  useEffect(() => {
    if (!resolvedPlayerId) return;

    const loadStats = async () => {
      try {
        setLoading(true);
        setError('');
        const data = await playersAPI.getPlayerStats(resolvedPlayerId);
        setStats(data);
      } catch (err: any) {
        setError('Failed to load player stats');
      } finally {
        setLoading(false);
      }
    };
    loadStats();
  }, [resolvedPlayerId]);

  if (!resolvedPlayerId) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <div>
      <div className="page-header">
        <h1>Player Stats</h1>
        <button className="btn btn-secondary" onClick={() => navigate('/lobby')}>
          Back to Lobby
        </button>
      </div>

      <div className="stats-tabs">
        <button
          className={`stats-tab ${activeTab === 'stats' ? 'stats-tab-active' : ''}`}
          onClick={() => setActiveTab('stats')}
        >
          My Stats
        </button>
        <button
          className={`stats-tab ${activeTab === 'leaderboard' ? 'stats-tab-active' : ''}`}
          onClick={() => setActiveTab('leaderboard')}
        >
          Leaderboard
        </button>
      </div>

      {activeTab === 'stats' ? (
        <>
          {loading && <div className="loading">Loading stats...</div>}
          {error && <div className="error">{error}</div>}
          {stats && <StatsOverview stats={stats} />}
          {stats && <GameHistory stats={stats} />}
        </>
      ) : (
        <GlobalLeaderboard />
      )}
    </div>
  );
};

const StatsOverview: React.FC<{ stats: PlayerStatsData }> = ({ stats }) => (
  <div className="card">
    <h2>{stats.username}'s Stats</h2>
    <div className="stats-grid">
      <div className="stat-card">
        <div className="stat-value">{stats.games_played}</div>
        <div className="stat-label">Games Played</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{stats.wins}</div>
        <div className="stat-label">Wins</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{stats.losses}</div>
        <div className="stat-label">Losses</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{stats.win_rate}%</div>
        <div className="stat-label">Win Rate</div>
      </div>
    </div>
  </div>
);

const GameHistory: React.FC<{ stats: PlayerStatsData }> = ({ stats }) => (
  <div className="card">
    <h2>Recent Games</h2>
    {stats.history.length === 0 ? (
      <p>No completed games yet.</p>
    ) : (
      <div className="table-responsive">
        <table className="stats-table">
          <thead>
            <tr>
              <th>Game</th>
              <th>Country</th>
              <th>Rounds</th>
              <th>Placement</th>
              <th>Result</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {stats.history.map((entry) => (
              <tr key={entry.game_id}>
                <td>#{entry.game_id}</td>
                <td>{entry.country_name}</td>
                <td>{entry.rounds}</td>
                <td>{entry.placement ?? '—'}</td>
                <td>
                  <span className={entry.won ? 'result-win' : 'result-loss'}>
                    {entry.won ? 'Win' : 'Loss'}
                  </span>
                </td>
                <td>
                  {entry.finished_at
                    ? new Date(entry.finished_at).toLocaleDateString()
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
  </div>
);

export default PlayerStats;
