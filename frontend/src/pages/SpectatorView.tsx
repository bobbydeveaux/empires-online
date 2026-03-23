import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { GameState, SpawnedCountryWithDetails, WsServerMessage } from '../types';
import { useGameWebSocket } from '../hooks/useGameWebSocket';

// Round summary delta per player
interface PlayerDelta {
  playerName: string;
  countryName: string;
  goldDelta: number;
  territoriesDelta: number;
  peopleDelta: number;
  supportersDelta: number;
  revoltersDelta: number;
}

const SpectatorView: React.FC = () => {
  const { gameId } = useParams<{ gameId: string }>();
  const navigate = useNavigate();
  const [roundSummary, setRoundSummary] = useState<PlayerDelta[] | null>(null);
  const previousStateRef = useRef<GameState | null>(null);
  const previousRoundRef = useRef<number | null>(null);

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
    isSpectator: true,
  });

  // Track round changes and compute round summary
  useEffect(() => {
    if (!gameState) return;

    const currentRound = gameState.game.rounds - gameState.game.rounds_remaining + 1;

    if (previousRoundRef.current !== null && currentRound > previousRoundRef.current && previousStateRef.current) {
      const deltas: PlayerDelta[] = gameState.players.map(player => {
        const prev = previousStateRef.current?.players.find(p => p.id === player.id);
        return {
          playerName: player.player.username,
          countryName: player.country.name,
          goldDelta: player.gold - (prev?.gold ?? player.gold),
          territoriesDelta: player.territories - (prev?.territories ?? player.territories),
          peopleDelta: player.people - (prev?.people ?? player.people),
          supportersDelta: player.supporters - (prev?.supporters ?? player.supporters),
          revoltersDelta: player.revolters - (prev?.revolters ?? player.revolters),
        };
      });
      setRoundSummary(deltas);
    }

    previousStateRef.current = gameState;
    previousRoundRef.current = currentRound;
  }, [gameState]);

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

  const spectatorCount = gameState.spectator_count ?? 0;

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

      {/* Connection Status Banner */}
      <SpectatorConnectionBanner status={connectionStatus} onReconnect={reconnect} />

      <div className="game-info-bar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <h1 style={{ margin: 0 }}>Game #{gameState.game.id}</h1>
          <span className="spectator-badge" title="Spectator mode">
            Spectating
          </span>
          {spectatorCount > 0 && (
            <span className="spectator-count-badge" title={`${spectatorCount} spectator${spectatorCount !== 1 ? 's' : ''}`}>
              {spectatorCount} {spectatorCount === 1 ? 'spectator' : 'spectators'}
            </span>
          )}
        </div>
        <div>
          <strong>Round:</strong>{' '}
          {gameState.game.rounds - gameState.game.rounds_remaining + 1} /{' '}
          {gameState.game.rounds} | <strong>Phase:</strong> {gameState.game.phase}
        </div>
      </div>

      {/* Round Summary */}
      {roundSummary && (
        <SpectatorRoundSummary
          deltas={roundSummary}
          onDismiss={() => setRoundSummary(null)}
        />
      )}

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

              {gameState.game.phase === 'actions' && (
                <div style={{ marginTop: '10px', fontSize: '14px' }}>
                  <span style={{
                    color: player.actions_completed ? '#2e7d32' : '#ff9800'
                  }}>
                    Actions: {player.actions_completed ? 'Completed' : 'In Progress'}
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
                <th style={{ padding: '10px', textAlign: 'right' }}>Gold</th>
                <th style={{ padding: '10px', textAlign: 'right' }}>Territories</th>
                <th style={{ padding: '10px', textAlign: 'right' }}>Stability</th>
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
                  <td style={{ padding: '10px', textAlign: 'right' }}>{entry.breakdown.base_score}</td>
                  <td style={{ padding: '10px', textAlign: 'right' }}>{entry.breakdown.territory_bonus / 2}</td>
                  <td style={{ padding: '10px', textAlign: 'right' }}>{entry.breakdown.stability_bonus}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

// Connection status banner for spectator
interface SpectatorConnectionBannerProps {
  status: string;
  onReconnect: () => void;
}

const SpectatorConnectionBanner: React.FC<SpectatorConnectionBannerProps> = ({ status, onReconnect }) => {
  if (status === 'connected') return null;

  const bannerStyles: Record<string, React.CSSProperties> = {
    connecting: {
      backgroundColor: '#fff3cd',
      color: '#856404',
      padding: '8px 16px',
      marginBottom: '16px',
      borderRadius: '4px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    },
    reconnecting: {
      backgroundColor: '#fff3cd',
      color: '#856404',
      padding: '8px 16px',
      marginBottom: '16px',
      borderRadius: '4px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    },
    disconnected: {
      backgroundColor: '#f8d7da',
      color: '#721c24',
      padding: '8px 16px',
      marginBottom: '16px',
      borderRadius: '4px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    },
  };

  const messages: Record<string, string> = {
    connecting: 'Connecting to game server...',
    reconnecting: 'Connection lost. Reconnecting...',
    disconnected: 'Disconnected from game server.',
  };

  return (
    <div style={bannerStyles[status] || bannerStyles.disconnected} role="alert">
      <span>{messages[status] || 'Connection issue'}</span>
      {status === 'disconnected' && (
        <button
          onClick={onReconnect}
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

// Round summary display for spectator view
interface SpectatorRoundSummaryProps {
  deltas: PlayerDelta[];
  onDismiss: () => void;
}

const SpectatorRoundSummary: React.FC<SpectatorRoundSummaryProps> = ({ deltas, onDismiss }) => {
  const formatDelta = (value: number): string => {
    if (value > 0) return `+${value}`;
    if (value < 0) return `${value}`;
    return '0';
  };

  const deltaColor = (value: number, invert?: boolean): string => {
    const positive = invert ? value < 0 : value > 0;
    const negative = invert ? value > 0 : value < 0;
    if (positive) return '#2e7d32';
    if (negative) return '#d32f2f';
    return '#666';
  };

  return (
    <div className="card round-summary">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>Round Summary</h3>
        <button className="btn-secondary btn-sm" onClick={onDismiss}>
          Dismiss
        </button>
      </div>
      <p style={{ fontSize: '14px', color: '#666', marginBottom: '10px' }}>
        Changes from last round:
      </p>
      <div style={{ overflowX: 'auto' }}>
        <table className="round-summary-table">
          <thead>
            <tr>
              <th>Player</th>
              <th>Gold</th>
              <th>Territories</th>
              <th>People</th>
              <th>Supporters</th>
              <th>Revolters</th>
            </tr>
          </thead>
          <tbody>
            {deltas.map(delta => (
              <tr key={delta.playerName}>
                <td>
                  <strong>{delta.playerName}</strong>
                  <br />
                  <span style={{ fontSize: '12px', color: '#666' }}>{delta.countryName}</span>
                </td>
                <td style={{ color: deltaColor(delta.goldDelta) }}>
                  {formatDelta(delta.goldDelta)}
                </td>
                <td style={{ color: deltaColor(delta.territoriesDelta) }}>
                  {formatDelta(delta.territoriesDelta)}
                </td>
                <td style={{ color: deltaColor(delta.peopleDelta) }}>
                  {formatDelta(delta.peopleDelta)}
                </td>
                <td style={{ color: deltaColor(delta.supportersDelta) }}>
                  {formatDelta(delta.supportersDelta)}
                </td>
                <td style={{ color: deltaColor(delta.revoltersDelta, true) }}>
                  {formatDelta(delta.revoltersDelta)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default SpectatorView;
