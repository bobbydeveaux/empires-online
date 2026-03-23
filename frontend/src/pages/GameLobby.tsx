import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Game, Country, WsServerMessage } from '../types';
import { gamesAPI, playersAPI } from '../services/api';
import { useGameWebSocket } from '../hooks/useGameWebSocket';

const GameLobby: React.FC = () => {
  const [games, setGames] = useState<Game[]>([]);
  const [countries, setCountries] = useState<Country[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const navigate = useNavigate();

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [gamesData, countriesData] = await Promise.all([
        gamesAPI.listGames(),
        playersAPI.getCountries()
      ]);
      setGames(gamesData);
      setCountries(countriesData);
    } catch (err: any) {
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Refresh game list when window regains focus
  useEffect(() => {
    const handleFocus = () => { loadData(); };
    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, [loadData]);

  const joinGame = async (gameId: number, countryId: number) => {
    try {
      await gamesAPI.joinGame(gameId, countryId);
      navigate(`/game/${gameId}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to join game');
    }
  };

  if (loading && games.length === 0) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <div>
      <div className="page-header">
        <h1>Game Lobby</h1>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button
            className="btn btn-secondary"
            onClick={loadData}
            title="Refresh game list"
          >
            Refresh
          </button>
          <button
            className="btn"
            onClick={() => setShowCreateForm(!showCreateForm)}
          >
            {showCreateForm ? 'Cancel' : 'Create New Game'}
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {showCreateForm && (
        <CreateGameForm
          countries={countries}
          onGameCreated={(gameId) => {
            setShowCreateForm(false);
            navigate(`/game/${gameId}`);
          }}
          onCancel={() => setShowCreateForm(false)}
        />
      )}

      <div className="card">
        <h2>Available Games</h2>
        {games.length === 0 ? (
          <p>No games available. Create a new game to get started!</p>
        ) : (
          <div className="grid">
            {games.map(game => (
              <GameCardWithWs
                key={game.id}
                game={game}
                countries={countries}
                onJoin={joinGame}
                onGameUpdated={loadData}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

interface CreateGameFormProps {
  countries: Country[];
  onGameCreated: (gameId: number) => void;
  onCancel: () => void;
}

const CreateGameForm: React.FC<CreateGameFormProps> = ({ countries, onGameCreated, onCancel }) => {
  const [rounds, setRounds] = useState(5);
  const [selectedCountries, setSelectedCountries] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (selectedCountries.length < 2) {
      alert('Please select at least 2 countries');
      return;
    }

    setLoading(true);
    try {
      const game = await gamesAPI.createGame(rounds, selectedCountries);
      onGameCreated(game.id);
    } catch (err) {
      console.error('Failed to create game:', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleCountry = (countryName: string) => {
    setSelectedCountries(prev =>
      prev.includes(countryName)
        ? prev.filter(c => c !== countryName)
        : [...prev, countryName]
    );
  };

  return (
    <div className="card" style={{ marginBottom: '20px' }}>
      <h3>Create New Game</h3>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Number of Rounds:</label>
          <select value={rounds} onChange={(e) => setRounds(Number(e.target.value))}>
            <option value={3}>3 Rounds</option>
            <option value={5}>5 Rounds</option>
            <option value={7}>7 Rounds</option>
          </select>
        </div>

        <div className="form-group">
          <label>Select Countries (min 2):</label>
          <div className="grid grid-3" style={{ marginTop: '10px' }}>
            {countries.map(country => (
              <label key={country.id} style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={selectedCountries.includes(country.name)}
                  onChange={() => toggleCountry(country.name)}
                  style={{ marginRight: '8px' }}
                />
                {country.name}
              </label>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
          <button type="submit" className="btn" disabled={loading}>
            {loading ? 'Creating...' : 'Create Game'}
          </button>
          <button type="button" className="btn btn-secondary" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

interface GameCardWithWsProps {
  game: Game;
  countries: Country[];
  onJoin: (gameId: number, countryId: number) => void;
  onGameUpdated: () => void;
}

/** Game card that subscribes to WebSocket for real-time player join/leave updates. */
const GameCardWithWs: React.FC<GameCardWithWsProps> = ({ game, countries, onJoin, onGameUpdated }) => {
  const [selectedCountryId, setSelectedCountryId] = useState<number>(countries[0]?.id || 0);
  const [spectateLoading, setSpectateLoading] = useState(false);
  const token = localStorage.getItem('authToken');
  const navigate = useNavigate();

  // Only subscribe to WebSocket for games in "waiting" phase
  const shouldConnect = game.phase === 'waiting';

  const handleWsMessage = useCallback((message: WsServerMessage) => {
    if (message.type === 'player_joined' || message.type === 'player_left') {
      onGameUpdated();
    }
  }, [onGameUpdated]);

  const handleSpectate = async () => {
    setSpectateLoading(true);
    try {
      const result = await gamesAPI.spectateGame(game.id);
      localStorage.setItem(`spectatorToken:${game.id}`, result.spectator_token);
      navigate(`/spectate/${game.id}`);
    } catch (err: any) {
      console.error('Failed to spectate game:', err);
    } finally {
      setSpectateLoading(false);
    }
  };

  const { connectionStatus } = useGameWebSocket({
    gameId: shouldConnect ? game.id : null,
    token: shouldConnect ? token : null,
    onMessage: handleWsMessage,
  });

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
        <h3 style={{ margin: 0 }}>Game #{game.id}</h3>
        {shouldConnect && (
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: connectionStatus === 'connected' ? '#2e7d32' : connectionStatus === 'reconnecting' ? '#ff9800' : '#d32f2f',
              display: 'inline-block',
            }}
            title={`Live updates: ${connectionStatus}`}
          />
        )}
      </div>
      <p><strong>Status:</strong> {game.phase}</p>
      <p><strong>Rounds:</strong> {game.rounds_remaining} / {game.rounds} remaining</p>
      <p><strong>Created:</strong> {new Date(game.created_at).toLocaleDateString()}</p>

      {game.phase === 'waiting' && (
        <div style={{ marginTop: '15px' }}>
          <div className="form-group">
            <label>Choose Country:</label>
            <select
              value={selectedCountryId}
              onChange={(e) => setSelectedCountryId(Number(e.target.value))}
            >
              {countries.map(country => (
                <option key={country.id} value={country.id}>
                  {country.name} (Gold: {country.default_gold}, Territories: {country.default_territories})
                </option>
              ))}
            </select>
          </div>
          <button
            className="btn"
            onClick={() => onJoin(game.id, selectedCountryId)}
          >
            Join Game
          </button>
        </div>
      )}

      {game.phase !== 'waiting' && game.phase !== 'completed' && (
        <div style={{ marginTop: '15px', display: 'flex', gap: '10px' }}>
          <button
            className="btn"
            onClick={handleSpectate}
            disabled={spectateLoading}
          >
            {spectateLoading ? 'Loading...' : 'Spectate'}
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => window.location.href = `/game/${game.id}`}
          >
            View Game
          </button>
        </div>
      )}

      {game.phase === 'completed' && (
        <button
          className="btn btn-secondary"
          onClick={() => window.location.href = `/game/${game.id}`}
        >
          View Game
        </button>
      )}
    </div>
  );
};

export default GameLobby;
