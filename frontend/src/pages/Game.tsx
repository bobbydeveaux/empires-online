import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { GameState, SpawnedCountryWithDetails, GameAction, WsServerMessage } from '../types';
import { gamesAPI } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { useGameWebSocket } from '../hooks/useGameWebSocket';
// Toast notification types
interface Toast {
  id: number;
  message: string;
  type: 'success' | 'error';
}

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

let toastIdCounter = 0;

const Game: React.FC = () => {
  const { gameId } = useParams<{ gameId: string }>();
  const { user } = useAuth();
  const [actionLoading, setActionLoading] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [roundSummary, setRoundSummary] = useState<PlayerDelta[] | null>(null);
  const previousStateRef = useRef<GameState | null>(null);
  const previousRoundRef = useRef<number | null>(null);

  const token = localStorage.getItem('authToken');
  const numericGameId = gameId ? Number(gameId) : null;

  const addToast = useCallback((message: string, type: 'success' | 'error') => {
    const id = ++toastIdCounter;
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  }, []);

  const handleWsMessage = useCallback((message: WsServerMessage) => {
    if (message.type === 'error') {
      console.warn('WebSocket error:', message.message);
    }
  }, []);

  const { gameState, connectionStatus, reconnect, refreshGameState } = useGameWebSocket({
    gameId: numericGameId,
    token,
    onMessage: handleWsMessage,
  });

  // Track round changes and compute round summary
  useEffect(() => {
    if (!gameState) return;

    const currentRound = gameState.game.rounds - gameState.game.rounds_remaining + 1;

    if (previousRoundRef.current !== null && currentRound > previousRoundRef.current && previousStateRef.current) {
      // Round changed — compute deltas
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

  const getCurrentPlayer = (): SpawnedCountryWithDetails | null => {
    if (!gameState || !user) return null;
    return gameState.players.find(p => p.player_id === user.id) || null;
  };

  const startGame = async () => {
    try {
      if (!gameId) return;
      await gamesAPI.startGame(Number(gameId));
      await refreshGameState();
      addToast('Game started!', 'success');
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Failed to start game', 'error');
    }
  };

  const executeDevelopment = async () => {
    const currentPlayer = getCurrentPlayer();
    if (!currentPlayer || !gameId) return;

    setActionLoading(true);
    try {
      await gamesAPI.executeDevelopment(Number(gameId), currentPlayer.id);
      await refreshGameState();
      addToast('Development completed!', 'success');
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Failed to execute development', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const performAction = async (action: string, quantity: number = 1) => {
    const currentPlayer = getCurrentPlayer();
    if (!currentPlayer || !gameId) return;

    setActionLoading(true);
    try {
      const gameAction: GameAction = { action, quantity };
      await gamesAPI.performAction(Number(gameId), currentPlayer.id, gameAction);
      await refreshGameState();
      const actionLabels: Record<string, string> = {
        buy_bond: 'Bonds purchased',
        build_bank: 'Banks built',
        recruit_people: 'People recruited',
        acquire_territory: 'Territory acquired',
      };
      addToast(`${actionLabels[action] || 'Action completed'} (x${quantity})`, 'success');
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Failed to perform action', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const nextRound = async () => {
    try {
      if (!gameId) return;
      await gamesAPI.nextRound(Number(gameId));
      await refreshGameState();
      addToast('Advanced to next round', 'success');
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Failed to advance round', 'error');
    }
  };

  if (loading) {
    return <div className="loading">Loading game...</div>;
  }

  if (!gameState) {
    return <div className="error">Game not found</div>;
  }

  const currentPlayer = getCurrentPlayer();
  const isCreator = user && gameState.game.creator_id === user.id;

  return (
    <div>
      {/* Toast Notifications */}
      <div className="toast-container">
        {toasts.map(toast => (
          <div key={toast.id} className={`toast toast-${toast.type}`}>
            {toast.message}
          </div>
        ))}
      </div>

      {/* Connection Status Banner */}
      <ConnectionStatusBanner status={connectionStatus} onReconnect={reconnect} />

      <div className="game-info-bar">
        <h1 style={{ margin: 0 }}>Game #{gameState.game.id}</h1>
        <div>
          <strong>Round:</strong> {gameState.game.rounds - gameState.game.rounds_remaining + 1} / {gameState.game.rounds} |{' '}
          <strong>Phase:</strong> {gameState.game.phase}
        </div>
      </div>

      {/* Round Summary */}
      {roundSummary && (
        <RoundSummaryDisplay
          deltas={roundSummary}
          onDismiss={() => setRoundSummary(null)}
        />
      )}

      {/* Game Controls */}
      {gameState.game.phase === 'waiting' && isCreator && (
        <div className="card">
          <h3>Game Setup</h3>
          <p>Waiting for players to join. You can start the game when ready.</p>
          <button className="btn" onClick={startGame}>
            Start Game
          </button>
        </div>
      )}

      {/* Current Player Status */}
      {currentPlayer && (
        <div className="card">
          <h3>Your Empire: {currentPlayer.country.name}</h3>
          <PlayerStatus player={currentPlayer} />

          {gameState.game.phase === 'development' && !currentPlayer.development_completed && (
            <div style={{ marginTop: '15px' }}>
              <button
                className="btn"
                onClick={executeDevelopment}
                disabled={actionLoading}
              >
                {actionLoading ? 'Processing...' : 'Execute Development'}
              </button>
              <p style={{ fontSize: '14px', color: '#666', marginTop: '5px' }}>
                This will automatically calculate your luxury production, industries, and stability changes.
              </p>
            </div>
          )}

          {gameState.game.phase === 'development' && currentPlayer.development_completed && (
            <div className="success" style={{ marginTop: '15px' }}>
              Development completed for this round. Waiting for other players...
            </div>
          )}

          {gameState.game.phase === 'actions' && (
            <ActionPanel
              player={currentPlayer}
              onAction={performAction}
              loading={actionLoading}
            />
          )}
        </div>
      )}

      {/* All Players */}
      <div className="card">
        <h3>All Players</h3>
        <div className="grid grid-2">
          {gameState.players.map(player => (
            <div key={player.id} className="card">
              <h4>{player.player.username} - {player.country.name}</h4>
              <PlayerStatus player={player} />

              {gameState.game.phase === 'development' && (
                <div style={{ marginTop: '10px', fontSize: '14px' }}>
                  <span style={{
                    color: player.development_completed ? '#2e7d32' : '#ff9800'
                  }}>
                    Development: {player.development_completed ? 'Completed' : 'Pending'}
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
                  <td style={{ padding: '10px', textAlign: 'right' }}>{entry.breakdown.base_score}</td>
                  <td style={{ padding: '10px', textAlign: 'right' }}>{entry.breakdown.territory_bonus / 2}</td>
                  <td style={{ padding: '10px', textAlign: 'right' }}>{entry.breakdown.stability_bonus}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Admin Controls */}
      {isCreator && gameState.game.phase === 'actions' && (
        <div className="card">
          <h3>Game Master Controls</h3>
          <button className="btn" onClick={nextRound}>
            Advance to Next Round
          </button>
        </div>
      )}
    </div>
  );
};

// Connection status banner component
interface ConnectionStatusBannerProps {
  status: string;
  onReconnect: () => void;
}

const ConnectionStatusBanner: React.FC<ConnectionStatusBannerProps> = ({ status, onReconnect }) => {
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

interface PlayerStatusProps {
  player: SpawnedCountryWithDetails;
}

const PlayerStatus: React.FC<PlayerStatusProps> = ({ player }) => {
  return (
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
  );
};

interface ActionPanelProps {
  player: SpawnedCountryWithDetails;
  onAction: (action: string, quantity: number) => void;
  loading: boolean;
}

const ActionPanel: React.FC<ActionPanelProps> = ({ player, onAction, loading }) => {
  const [bondQuantity, setBondQuantity] = useState(1);
  const [bankQuantity, setBankQuantity] = useState(1);
  const [recruitQuantity, setRecruitQuantity] = useState(1);
  const [territoryQuantity, setTerritoryQuantity] = useState(1);

  const canBuyBonds = player.gold >= (bondQuantity * 2);
  const canBuildBanks = player.gold >= (bankQuantity * 3);
  const canRecruit = player.gold >= (recruitQuantity * 2);
  const canAcquireTerritory = player.gold >= (territoryQuantity * 3);

  return (
    <div style={{ marginTop: '15px' }}>
      <h4>Actions Phase</h4>
      <p style={{ fontSize: '14px', color: '#666', marginBottom: '15px' }}>
        You can perform optional actions with your gold. Actions are processed immediately.
      </p>

      <div className="grid grid-2">
        <div className="action-card">
          <h5>Buy Bonds (2 gold each)</h5>
          <div className="action-input-row">
            <input
              type="number"
              min="1"
              value={bondQuantity}
              onChange={(e) => setBondQuantity(Math.max(1, Number(e.target.value)))}
              className="action-quantity-input"
            />
            <span className="action-cost-label">bonds for {bondQuantity * 2} gold</span>
          </div>
          <button
            className="btn"
            onClick={() => onAction('buy_bond', bondQuantity)}
            disabled={loading || !canBuyBonds}
          >
            Buy Bonds
          </button>
          {!canBuyBonds && <div className="action-insufficient">Insufficient gold</div>}
        </div>

        <div className="action-card">
          <h5>Build Banks (3 gold each)</h5>
          <div className="action-input-row">
            <input
              type="number"
              min="1"
              value={bankQuantity}
              onChange={(e) => setBankQuantity(Math.max(1, Number(e.target.value)))}
              className="action-quantity-input"
            />
            <span className="action-cost-label">banks for {bankQuantity * 3} gold</span>
          </div>
          <button
            className="btn"
            onClick={() => onAction('build_bank', bankQuantity)}
            disabled={loading || !canBuildBanks}
          >
            Build Banks
          </button>
          {!canBuildBanks && <div className="action-insufficient">Insufficient gold</div>}
        </div>

        <div className="action-card">
          <h5>Recruit People (2 gold each)</h5>
          <div className="action-input-row">
            <input
              type="number"
              min="1"
              value={recruitQuantity}
              onChange={(e) => setRecruitQuantity(Math.max(1, Number(e.target.value)))}
              className="action-quantity-input"
            />
            <span className="action-cost-label">people for {recruitQuantity * 2} gold</span>
          </div>
          <button
            className="btn btn-recruit"
            onClick={() => onAction('recruit_people', recruitQuantity)}
            disabled={loading || !canRecruit}
          >
            Recruit People
          </button>
          {!canRecruit && <div className="action-insufficient">Insufficient gold</div>}
          <div className="action-hint">More people = more industries and luxury production.</div>
        </div>

        <div className="action-card">
          <h5>Acquire Territory (3 gold each)</h5>
          <div className="action-input-row">
            <input
              type="number"
              min="1"
              value={territoryQuantity}
              onChange={(e) => setTerritoryQuantity(Math.max(1, Number(e.target.value)))}
              className="action-quantity-input"
            />
            <span className="action-cost-label">territories for {territoryQuantity * 3} gold</span>
          </div>
          <button
            className="btn btn-territory"
            onClick={() => onAction('acquire_territory', territoryQuantity)}
            disabled={loading || !canAcquireTerritory}
          >
            Acquire Territory
          </button>
          {!canAcquireTerritory && <div className="action-insufficient">Insufficient gold</div>}
          <div className="action-hint">More territory = more goods and industrial capacity.</div>
        </div>
      </div>

      <div style={{ marginTop: '15px', fontSize: '12px', color: '#666' }}>
        <strong>Remember:</strong> Banks cost 1 gold per round to maintain, but provide stability.
        Each bond without a corresponding bank increases revolt by 1.
      </div>
    </div>
  );
};

// Round summary display component
interface RoundSummaryDisplayProps {
  deltas: PlayerDelta[];
  onDismiss: () => void;
}

const RoundSummaryDisplay: React.FC<RoundSummaryDisplayProps> = ({ deltas, onDismiss }) => {
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

export default Game;
