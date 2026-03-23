import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PlayerStats as PlayerStatsType } from '../types';
import { playersAPI } from '../services/api';
import GlobalLeaderboard from '../components/GlobalLeaderboard';

const PlayerStats: React.FC = () => {
  const { playerId } = useParams<{ playerId: string }>();
  const navigate = useNavigate();
  const [stats, setStats] = useState<PlayerStatsType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!playerId) return;

    const loadStats = async () => {
      try {
        setLoading(true);
        setError('');
        const data = await playersAPI.getPlayerStats(parseInt(playerId, 10));
        setStats(data);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load player stats');
      } finally {
        setLoading(false);
      }
    };
    loadStats();
  }, [playerId]);

  if (loading) {
    return <div className="loading">Loading player stats...</div>;
  }

  if (error) {
    return (
      <div>
        <div className="error">{error}</div>
        <button className="btn" onClick={() => navigate('/stats')}>
          Back to Leaderboard
        </button>
      </div>
    );
  }

  if (!stats) {
    return <div className="error">Player not found</div>;
  }

  const winRate = stats.games_played > 0
    ? Math.round((stats.wins / stats.games_played) * 100)
    : 0;

  return (
    <div>
      <div className="page-header">
        <h1>{stats.username}</h1>
        <button className="btn btn-secondary" onClick={() => navigate('/stats')}>
          Back to Leaderboard
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-3" style={{ marginBottom: '20px' }}>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#1976d2' }}>
            {stats.games_played}
          </div>
          <div style={{ color: '#666', fontSize: '14px' }}>Games Played</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#2e7d32' }}>
            {stats.wins}
          </div>
          <div style={{ color: '#666', fontSize: '14px' }}>
            Wins ({winRate}%)
          </div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#f57c00' }}>
            {stats.best_score}
          </div>
          <div style={{ color: '#666', fontSize: '14px' }}>Best Score</div>
        </div>
      </div>

      {/* Additional info */}
      <div className="grid grid-2" style={{ marginBottom: '20px' }}>
        <div className="card">
          <h3 style={{ margin: '0 0 10px' }}>Performance</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#666' }}>Average Score</span>
              <strong>{stats.average_score}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#666' }}>Favorite Country</span>
              <strong>{stats.favorite_country || 'N/A'}</strong>
            </div>
            {stats.created_at && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#666' }}>Member Since</span>
                <strong>{new Date(stats.created_at).toLocaleDateString()}</strong>
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <h3 style={{ margin: '0 0 10px' }}>Countries Played</h3>
          {Object.keys(stats.countries_played).length === 0 ? (
            <p style={{ color: '#666', margin: 0 }}>No games completed yet</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {Object.entries(stats.countries_played)
                .sort(([, a], [, b]) => b - a)
                .map(([country, count]) => (
                  <div key={country} style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>{country}</span>
                    <span style={{ color: '#666' }}>
                      {count} {count === 1 ? 'game' : 'games'}
                    </span>
                  </div>
                ))}
            </div>
          )}
        </div>
      </div>

      {/* Game history */}
      <div className="card">
        <h3 style={{ margin: '0 0 15px' }}>Game History</h3>
        {stats.game_history.length === 0 ? (
          <p style={{ color: '#666', margin: 0 }}>No completed games yet</p>
        ) : (
          <div className="table-responsive">
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #ddd' }}>
                  <th style={{ padding: '8px 10px', textAlign: 'left' }}>Game</th>
                  <th style={{ padding: '8px 10px', textAlign: 'left' }}>Country</th>
                  <th style={{ padding: '8px 10px', textAlign: 'right' }}>Placement</th>
                  <th style={{ padding: '8px 10px', textAlign: 'right' }}>Score</th>
                  <th style={{ padding: '8px 10px', textAlign: 'right' }}>Rounds</th>
                  <th style={{ padding: '8px 10px', textAlign: 'right' }}>Date</th>
                </tr>
              </thead>
              <tbody>
                {stats.game_history.map((game) => (
                  <tr key={game.game_id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '8px 10px' }}>#{game.game_id}</td>
                    <td style={{ padding: '8px 10px' }}>{game.country_name}</td>
                    <td style={{ padding: '8px 10px', textAlign: 'right' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        borderRadius: '10px',
                        fontSize: '12px',
                        fontWeight: 600,
                        backgroundColor: game.placement === 1 ? '#fff8e1' : game.placement === 2 ? '#f5f5f5' : game.placement === 3 ? '#fff3e0' : '#fafafa',
                        color: game.placement === 1 ? '#f57c00' : '#666',
                      }}>
                        {game.placement === 1 ? '1st' : game.placement === 2 ? '2nd' : game.placement === 3 ? '3rd' : `${game.placement}th`}
                      </span>
                    </td>
                    <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 500 }}>
                      {game.score}
                    </td>
                    <td style={{ padding: '8px 10px', textAlign: 'right' }}>
                      {game.duration_rounds}
                    </td>
                    <td style={{ padding: '8px 10px', textAlign: 'right', color: '#666' }}>
                      {game.finished_at ? new Date(game.finished_at).toLocaleDateString() : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

const StatsPage: React.FC = () => {
  const { playerId } = useParams<{ playerId: string }>();

  if (playerId) {
    return <PlayerStats />;
  }

  return (
    <div>
      <div className="page-header">
        <h1>Player Stats</h1>
      </div>
      <GlobalLeaderboard />
    </div>
  );
};

export default StatsPage;
