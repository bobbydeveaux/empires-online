import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { GlobalLeaderboardEntry } from '../types';
import { playersAPI } from '../services/api';

const GlobalLeaderboard: React.FC = () => {
  const [leaderboard, setLeaderboard] = useState<GlobalLeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const loadLeaderboard = async () => {
      try {
        setLoading(true);
        const data = await playersAPI.getGlobalLeaderboard();
        setLeaderboard(data);
      } catch (err: any) {
        setError('Failed to load leaderboard');
      } finally {
        setLoading(false);
      }
    };
    loadLeaderboard();
  }, []);

  if (loading) {
    return <div className="loading">Loading leaderboard...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (leaderboard.length === 0) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '40px 20px' }}>
        <h3 style={{ margin: '0 0 10px' }}>No Games Completed Yet</h3>
        <p style={{ color: '#666', margin: 0 }}>
          Complete a game to appear on the leaderboard!
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <h3 style={{ margin: '0 0 15px' }}>Global Leaderboard</h3>
      <div className="table-responsive">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #ddd' }}>
              <th style={{ padding: '8px 10px', textAlign: 'left' }}>Rank</th>
              <th style={{ padding: '8px 10px', textAlign: 'left' }}>Player</th>
              <th style={{ padding: '8px 10px', textAlign: 'right' }}>Wins</th>
              <th style={{ padding: '8px 10px', textAlign: 'right' }}>Games</th>
              <th style={{ padding: '8px 10px', textAlign: 'right' }}>Win Rate</th>
              <th style={{ padding: '8px 10px', textAlign: 'right' }}>Avg Score</th>
              <th style={{ padding: '8px 10px', textAlign: 'right' }}>Best</th>
            </tr>
          </thead>
          <tbody>
            {leaderboard.map((entry, index) => {
              const winRate = entry.games_played > 0
                ? Math.round((entry.wins / entry.games_played) * 100)
                : 0;
              return (
                <tr
                  key={entry.player_id}
                  style={{
                    borderBottom: '1px solid #eee',
                    cursor: 'pointer',
                    backgroundColor: index < 3 ? ['#fff8e1', '#f5f5f5', '#fff3e0'][index] : undefined,
                  }}
                  onClick={() => navigate(`/stats/${entry.player_id}`)}
                  title="View player stats"
                >
                  <td style={{ padding: '8px 10px', fontWeight: 600 }}>
                    {index === 0 ? '1st' : index === 1 ? '2nd' : index === 2 ? '3rd' : `${index + 1}th`}
                  </td>
                  <td style={{ padding: '8px 10px', fontWeight: 500 }}>
                    {entry.player_name}
                  </td>
                  <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 600 }}>
                    {entry.wins}
                  </td>
                  <td style={{ padding: '8px 10px', textAlign: 'right' }}>
                    {entry.games_played}
                  </td>
                  <td style={{ padding: '8px 10px', textAlign: 'right' }}>
                    {winRate}%
                  </td>
                  <td style={{ padding: '8px 10px', textAlign: 'right' }}>
                    {entry.average_score}
                  </td>
                  <td style={{ padding: '8px 10px', textAlign: 'right' }}>
                    {entry.best_score}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default GlobalLeaderboard;
