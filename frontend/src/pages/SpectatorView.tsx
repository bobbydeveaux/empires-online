import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { GameState, SpawnedCountryWithDetails, WsServerMessage } from '../types';
import { gamesAPI } from '../services/api';
import { useGameWebSocket } from '../hooks/useGameWebSocket';

const SpectatorView: React.FC = () => {
  const { gameId } = useParams<{ gameId: string }>();
  const navigate = useNavigate();
  const numericGameId = gameId ? Number(gameId) : null;

  const spectatorToken = gameId
    ? localStorage.getItem(`spectatorToken:${gameId}`)
    : null;
  const authToken = localStorage.getItem('authToken');
  // Use spectator token for WebSocket if available, fall back to auth token
  const wsToken = spectatorToken || authToken;

  const handleWsMessage = useCallback((message: WsServerMessage) => {
    if (message.type === 'error') {
      console.warn('Spectator WebSocket error:', message.message);
    }
  }, []);

  const { gameState, connectionStatus, reconnect } = useGameWebSocket({
    gameId: numericGameId,
    token: wsToken,
    onMessage: handleWsMessage,
  });

  const loading = gameState === null && connectionStatus !== 'disconnected';

  if (loading) {
    return <div className="loading">Loading game...</div>;
  }

  if (!gameState) {
    return (
      <div className="card">
        <h2>Game not found</h2>
        <button className="btn" onClick={() => navigate('/lobby')}>
          Back to Lobby
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Spectator Banner */}
      <div
        style={{
          backgroundColor: '#e3f2fd',
          color: '#1565c0',
          padding: '8px 16px',
          marginBottom: '16px',
          borderRadius: '4px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderLeft: '4px solid #1565c0',
        }}
      >
        <span>Spectator Mode — You are watching this game (read-only)</span>
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => navigate('/lobby')}
        >
          Back to Lobby
        </button>
      </div>

      {/* Connection Status */}
      {connectionStatus !== 'connected' && (
        <div
          style={{
            backgroundColor: connectionStatus === 'disconnected' ? '#f8d7da' : '#fff3cd',
            color: connectionStatus === 'disconnected' ? '#721c24' : '#856404',
            padding: '8px 16px',
            marginBottom: '16px',
            borderRadius: '4px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
          role="alert"
        >
          <span>
            {connectionStatus === 'disconnected'
              ? 'Disconnected from game server.'
              : 'Connecting to game server...'}
          </span>
          {connectionStatus === 'disconnected' && (
            <button
              onClick={reconnect}
              style={{
                background: 'none',
                border: '1px solid #721c24',
                color: '#721c24',
                padding: '4px 12px',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Reconnect
            </button>
          )}
        </div>
      )}

      {/* Game Info */}
      <div className="game-info-bar">
        <h1 style={{ margin: 0 }}>Game #{gameState.game.id}</h1>
        <div>
          <strong>Round:</strong>{' '}
          {gameState.game.rounds - gameState.game.rounds_remaining + 1} /{' '}
          {gameState.game.rounds} | <strong>Phase:</strong> {gameState.game.phase}
        </div>
      </div>

      {/* All Players */}
      <div className="card">
        <h3>Players</h3>
        <div className="grid grid-2">
          {gameState.players.map((player) => (
            <div key={player.id} className="card">
              <h4>
                {player.player.username} - {player.country.name}
              </h4>
              <SpectatorPlayerStatus player={player} />

              {gameState.game.phase === 'development' && (
                <div style={{ marginTop: '10px', fontSize: '14px' }}>
                  <span
                    style={{
                      color: player.development_completed ? '#2e7d32' : '#ff9800',
                    }}
                  >
                    Development:{' '}
                    {player.development_completed ? 'Completed' : 'Pending'}
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Leaderboard */}
      <div className="card">
        <h3>Current Leaderboard</h3>
        <div className="table-responsive">
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ddd' }}>
                <th style={{ padding: '10px', textAlign: 'left' }}>Rank</th>
                <th style={{ padding: '10px', textAlign: 'left' }}>Player</th>
                <th style={{ padding: '10px', textAlign: 'left' }}>Country</th>
                <th style={{ padding: '10px', textAlign: 'right' }}>Score</th>
              </tr>
            </thead>
            <tbody>
              {gameState.leaderboard.map((entry, index) => (
                <tr
                  key={entry.player_id}
                  style={{ borderBottom: '1px solid #eee' }}
                >
                  <td style={{ padding: '10px' }}>{index + 1}</td>
                  <td style={{ padding: '10px' }}>{entry.player_name}</td>
                  <td style={{ padding: '10px' }}>{entry.country_name}</td>
                  <td style={{ padding: '10px', textAlign: 'right' }}>
                    {entry.score.toFixed(1)}
                    {entry.breakdown.instability_penalty && (
                      <span style={{ color: '#d32f2f', fontSize: '12px' }}>
                        {' '}
                        (Instability Penalty)
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

interface SpectatorPlayerStatusProps {
  player: SpawnedCountryWithDetails;
}

const SpectatorPlayerStatus: React.FC<SpectatorPlayerStatusProps> = ({
  player,
}) => {
  return (
    <div className="grid grid-3" style={{ fontSize: '14px' }}>
      <div>
        <strong>Gold:</strong> {player.gold}
        <br />
        <strong>Bonds:</strong> {player.bonds}
        <br />
        <strong>Banks:</strong> {player.banks}
      </div>
      <div>
        <strong>Territories:</strong> {player.territories}
        <br />
        <strong>Goods:</strong> {player.goods}
        <br />
        <strong>People:</strong> {player.people}
      </div>
      <div>
        <strong>Supporters:</strong> {player.supporters}
        <br />
        <strong>Revolters:</strong> {player.revolters}
        <br />
        <strong>Net Stability:</strong> {player.supporters - player.revolters}
      </div>
    </div>
  );
};

export default SpectatorView;
