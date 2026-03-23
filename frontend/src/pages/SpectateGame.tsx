import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { GameState, WsServerMessage, WsConnectionStatus } from '../types';
import { gamesAPI } from '../services/api';
import { useGameWebSocket } from '../hooks/useGameWebSocket';

const SpectateGame: React.FC = () => {
  const { gameId } = useParams<{ gameId: string }>();
  const numericGameId = gameId ? Number(gameId) : null;

  const [spectatorToken, setSpectatorToken] = useState<string | null>(null);
  const [tokenError, setTokenError] = useState<string | null>(null);

  // Fetch spectator token on mount
  useEffect(() => {
    if (!numericGameId) return;
    let cancelled = false;

    gamesAPI.spectateGame(numericGameId)
      .then(resp => {
        if (!cancelled) setSpectatorToken(resp.spectator_token);
      })
      .catch(err => {
        if (!cancelled) {
          setTokenError(err.response?.data?.detail || 'Failed to get spectator access');
        }
      });

    return () => { cancelled = true; };
  }, [numericGameId]);

  const handleWsMessage = useCallback((message: WsServerMessage) => {
    if (message.type === 'error') {
      console.warn('Spectator WebSocket error:', message.message);
    }
  }, []);

  const { gameState, connectionStatus, reconnect } = useGameWebSocket({
    gameId: numericGameId,
    token: spectatorToken,
    onMessage: handleWsMessage,
    isSpectator: true,
  });

  if (tokenError) {
    return <div className="error">{tokenError}</div>;
  }

  if (!spectatorToken) {
    return <div className="loading">Joining as spectator...</div>;
  }

  const loading = gameState === null && connectionStatus !== 'disconnected';

  if (loading) {
    return <div className="loading">Loading game...</div>;
  }

  if (!gameState) {
    return <div className="error">Game not found</div>;
  }

  return (
    <div>
      <SpectatorBanner
        connectionStatus={connectionStatus}
        spectatorCount={gameState.spectator_count}
        onReconnect={reconnect}
      />

      <div className="game-info-bar">
        <h1 style={{ margin: 0 }}>Game #{gameState.game.id} (Spectating)</h1>
        <div>
          <strong>Round:</strong> {gameState.game.rounds - gameState.game.rounds_remaining + 1} / {gameState.game.rounds} |{' '}
          <strong>Phase:</strong> {gameState.game.phase}
        </div>
      </div>

      {/* All Players */}
      <div className="card">
        <h3>All Players</h3>
        <div className="grid grid-2">
          {gameState.players.map(player => (
            <div key={player.id} className="card">
              <h4>{player.player.username} - {player.country.name}</h4>
              <div className="grid grid-3" style={{ fontSize: '14px' }}>
                <div>
                  <strong>Gold:</strong> {player.gold}<br />
                  <strong>Bonds:</strong> {player.bonds}<br />
                  <strong>Banks:</strong> {player.banks}
                </div>
                <div>
                  <strong>Territories:</strong> {player.territories}<br />
                  <strong>Goods:</strong> {player.goods}<br />
                  <strong>People:</strong> {player.people}
                </div>
                <div>
                  <strong>Supporters:</strong> {player.supporters}<br />
                  <strong>Revolters:</strong> {player.revolters}<br />
                  <strong>Net Stability:</strong> {player.supporters - player.revolters}
                </div>
              </div>
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
                <tr key={entry.player_id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '10px' }}>{index + 1}</td>
                  <td style={{ padding: '10px' }}>{entry.player_name}</td>
                  <td style={{ padding: '10px' }}>{entry.country_name}</td>
                  <td style={{ padding: '10px', textAlign: 'right' }}>
                    {entry.score.toFixed(1)}
                    {entry.breakdown.instability_penalty && (
                      <span style={{ color: '#d32f2f', fontSize: '12px' }}> (Instability Penalty)</span>
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

interface SpectatorBannerProps {
  connectionStatus: WsConnectionStatus;
  spectatorCount?: number;
  onReconnect: () => void;
}

const SpectatorBanner: React.FC<SpectatorBannerProps> = ({ connectionStatus, spectatorCount, onReconnect }) => {
  const isConnected = connectionStatus === 'connected';
  const style: React.CSSProperties = {
    backgroundColor: isConnected ? '#e3f2fd' : '#fff3cd',
    color: isConnected ? '#1565c0' : '#856404',
    padding: '8px 16px',
    marginBottom: '16px',
    borderRadius: '4px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  };

  return (
    <div style={style} role="status">
      <span>
        Spectator Mode (read-only)
        {spectatorCount != null && ` — ${spectatorCount} spectator${spectatorCount !== 1 ? 's' : ''} watching`}
      </span>
      {connectionStatus === 'disconnected' && (
        <button
          onClick={onReconnect}
          style={{
            background: 'none',
            border: '1px solid #856404',
            color: '#856404',
            padding: '4px 12px',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Reconnect
        </button>
      )}
      {(connectionStatus === 'connecting' || connectionStatus === 'reconnecting') && (
        <span style={{ fontSize: '14px' }}>Connecting...</span>
      )}
    </div>
  );
};

export default SpectateGame;
