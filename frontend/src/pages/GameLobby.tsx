import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Game, Country } from '../types';
import { gamesAPI, playersAPI } from '../services/api';

const GameLobby: React.FC = () => {
  const [games, setGames] = useState<Game[]>([]);
  const [countries, setCountries] = useState<Country[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
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
  };

  const joinGame = async (gameId: number, countryId: number) => {
    try {
      await gamesAPI.joinGame(gameId, countryId);
      navigate(`/game/${gameId}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to join game');
    }
  };

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>Game Lobby</h1>
        <button 
          className="btn" 
          onClick={() => setShowCreateForm(!showCreateForm)}
        >
          {showCreateForm ? 'Cancel' : 'Create New Game'}
        </button>
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
              <GameCard 
                key={game.id} 
                game={game} 
                countries={countries}
                onJoin={joinGame}
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

interface GameCardProps {
  game: Game;
  countries: Country[];
  onJoin: (gameId: number, countryId: number) => void;
}

const GameCard: React.FC<GameCardProps> = ({ game, countries, onJoin }) => {
  const [selectedCountryId, setSelectedCountryId] = useState<number>(countries[0]?.id || 0);

  return (
    <div className="card">
      <h3>Game #{game.id}</h3>
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
      
      {game.phase !== 'waiting' && (
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