import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { GlobalLeaderboardEntry } from '../types';
import { playersAPI } from '../services/api';

const GlobalLeaderboard: React.FC = () => {
  const [entries, setEntries] = useState<GlobalLeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const loadLeaderboard = async () => {
      try {
        setLoading(true);
        const data = await playersAPI.getGlobalLeaderboard();
        setEntries(data);
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

  return (
    <div className="card">
      <h2>Global Leaderboard</h2>
      {entries.length === 0 ? (
        <p>No completed games yet. Play some games to see the leaderboard!</p>
      ) : (
        <div className="table-responsive">
          <table className="stats-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Player</th>
                <th>Wins</th>
                <th>Losses</th>
                <th>Games</th>
                <th>Win Rate</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry, index) => (
                <tr
                  key={entry.player_id}
                  className="stats-table-row-clickable"
                  onClick={() => navigate(`/stats/${entry.player_id}`)}
                >
                  <td>{index + 1}</td>
                  <td>{entry.username}</td>
                  <td>{entry.wins}</td>
                  <td>{entry.losses}</td>
                  <td>{entry.games_played}</td>
                  <td>{entry.win_rate}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default GlobalLeaderboard;
