# Empires Online

An online implementation of the classic Empires board game - a strategic economic game where players control historical empires, manage resources, and compete for dominance.

## Game Overview

Empires is a turn-based strategy game where players:
- Manage economic resources (gold, goods, people, territories)
- Balance luxury production vs industrial development
- Handle political stability through supporters and revolters
- Make strategic banking and bond decisions
- Compete over multiple rounds for the highest score

## Architecture

This implementation consists of:
- **Backend**: FastAPI-based REST API with PostgreSQL database
- **Frontend**: React TypeScript SPA with real-time updates
- **Database**: PostgreSQL with SQLAlchemy ORM and Alembic migrations
- **Real-time**: WebSocket connections with PostgreSQL NOTIFY/LISTEN for cross-process event fanout
- **Deployment**: Docker containers with docker-compose

## Quick Start

### Using Docker (Recommended)

1. **Clone the repository**
```bash
git clone https://github.com/bobbydeveaux/empires-online.git
cd empires-online
```

2. **Start the application**
```bash
docker-compose up -d
```

3. **Access the game**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

4. **Test login**
- Username: `testuser`
- Password: `testpass123`

### Local Development

#### Backend Setup

1. **Install Python dependencies**
```bash
cd backend
pip install -r requirements.txt
```

2. **Set up PostgreSQL database**
```bash
# Start PostgreSQL (e.g., with Docker)
docker run -d --name empires-db -e POSTGRES_DB=empires_db -e POSTGRES_USER=empires -e POSTGRES_PASSWORD=empires -p 5432:5432 postgres:15
```

3. **Initialize database** (runs Alembic migrations and seeds data)
```bash
cd backend
alembic upgrade head
python app/init_db.py
```

4. **Start the backend server**
```bash
uvicorn app.main:app --reload
```

#### Frontend Setup

1. **Install Node.js dependencies**
```bash
cd frontend
npm install
```

2. **Start the development server**
```bash
npm start
```

## Game Rules

### Core Game Loop
1. **Development Phase** (automatic): Calculate luxuries, industries, unemployment, banking costs
2. **Action Phase** (optional): Players can buy bonds, build banks, recruit people, acquire territories
3. **End Actions**: Players mark themselves done; auto-advances when all players complete
4. **Stability Check**: Countries with revolters > supporters lose gold
5. **Round End**: Update state, broadcast round summary, prepare for next round
6. **Game End**: Calculate victory points after all rounds

### Development Algorithm
The heart of the game's economic system:
```
luxuries = MIN(people, goods)
available_workers = people - luxuries
industries = MIN(territories, available_workers)
unemployed = people - luxuries - industries

if unemployed > 1:
    revolters += 1

gold -= banks  // Bank maintenance cost
revolters += (bonds - banks)  // Banking stability effect
supporters += luxuries
gold += industries  // Industrial income
goods = MIN(territories, people)  // Next round's goods
```

### Victory Points
```
Base Score = gold * 1
Territory Bonus = territories * 2
Stability Bonus = MAX(0, supporters - revolters) * 1
Economic Bonus = bonds * 1
Instability Penalty = If revolters > supporters, multiply total by 0.5
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/token` - Login and get access token
- `GET /api/auth/me` - Get current user info

### Games
- `POST /api/games/` - Create new game
- `GET /api/games/` - List available games
- `POST /api/games/{id}/join` - Join game with country
- `POST /api/games/{id}/start` - Start game (creator only)
- `GET /api/games/{id}` - Get game state
- `POST /api/games/{id}/countries/{country_id}/develop` - Execute development
- `POST /api/games/{id}/countries/{country_id}/actions` - Perform actions (buy_bond, build_bank, recruit_people, acquire_territory)
- `POST /api/games/{id}/countries/{country_id}/end-actions` - End actions phase (auto-advances round when all players done)
- `POST /api/games/{id}/next-round` - Manually advance round (creator only)
- `GET /api/games/{id}/round-summary` - Get per-player round summary
- `GET /api/games/{id}/leaderboard` - Get current standings
- `POST /api/games/{id}/spectate` - Get spectator token for watching an in-progress game

### Trading
- `POST /api/games/{id}/trades` - Propose a trade (offer/request resources)
- `POST /api/games/{id}/trades/{trade_id}/accept` - Accept a pending trade (receiver only)
- `POST /api/games/{id}/trades/{trade_id}/reject` - Reject a pending trade (receiver only)
- `POST /api/games/{id}/trades/{trade_id}/cancel` - Cancel a trade
- `GET /api/games/{id}/trades` - List pending trades for a game

### Players
- `GET /api/players/countries` - List available countries
- `GET /api/players/me` - Get current player info

### WebSocket
- `WS /ws/{game_id}?token=<jwt>` - Real-time game updates (JWT required via query param or Authorization header)
- Game state changes (join, start, development, actions, round advance, game completion) are broadcast to all connected clients in real-time
- See [docs/websocket-api.md](docs/websocket-api.md) for full message type reference

## Testing

### Backend Tests
```bash
cd backend
python -m pytest app/tests/ -v
```

### Backend Tests with Coverage
```bash
cd backend
python -m pytest --cov=app --cov-report=term-missing app/tests/ -v
```

Coverage target: **≥ 80%**

### Frontend Tests
```bash
cd frontend
npm test
```

### Full CI/CD Testing
```bash
docker-compose build
docker-compose up -d
# Application should be available at http://localhost:3000
docker-compose down
```

## Development Features

### Phase 1 - Core Game (✅ Complete)
- [x] Set up database schema with all required tables
- [x] Implement user authentication and registration
- [x] Create game lobby for creating/joining games
- [x] Implement core development algorithm exactly as specified
- [x] Build basic web interface for gameplay
- [x] Add real-time game state updates
- [x] Implement victory point calculation
- [x] Full CI/CD pipeline with GitHub Actions
- [x] Docker containers and docker-compose setup
- [x] Comprehensive unit tests for game logic
- [x] Integration tests with coverage target (≥80%)

### Phase 2 - Enhanced Features (🔄 In Progress)
- [x] Add WebSocket support for real-time updates (backend + frontend hook with reconnection)
- [x] Toast notification system for action confirmations and errors
- [x] End-actions endpoint with automatic phase transitions
- [x] Stability check at round end (revolters > supporters → gold loss)
- [x] Round summary endpoint with per-player action history
- [x] New actions: recruit_people (2 gold), acquire_territory (3 gold)
- [x] Implement trading between players (propose/accept/reject with atomic resource transfer)
- [x] Auto-record game results on completion (GameResult with winner, rankings, duration)
- [ ] Add game history and statistics
- [ ] Create comprehensive API documentation
- [x] Implement game spectator mode (backend: spectator WebSocket connections, POST /spectate endpoint, spectator_count in game listings; frontend: spectate button in lobby, read-only spectator view with live updates)

### Phase 3 - Polish (📋 Future)
- [ ] Add AI opponents for single-player practice
- [ ] Create tournament system
- [ ] Add game variants (short/long games)
- [ ] Implement advanced rules (diplomacy, events)
- [x] Mobile-responsive design
- [ ] Performance optimization

## Technology Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, Alembic, PostgreSQL
- **Frontend**: React 18, TypeScript, Axios
- **Database**: PostgreSQL 15
- **Testing**: Pytest + pytest-cov (backend), Jest (frontend)
- **Deployment**: Docker, Docker Compose
- **CI/CD**: GitHub Actions

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests to ensure everything works
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Performance Targets

- Support 100+ concurrent games
- Real-time updates with <100ms latency
- Handle 1000+ registered users
- Database queries optimized for game state reads

## Security Features

- JWT-based authentication
- Password hashing with bcrypt
- SQL injection prevention with SQLAlchemy ORM
- CORS protection
- Input validation with Pydantic

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Documentation

- See [DESIGN.md](DESIGN.md) for complete game rules, API specifications, and implementation details
- See [COPILOT_INSTRUCTIONS.md](COPILOT_INSTRUCTIONS.md) for development guidelines and architecture decisions
- See [docs/websocket-api.md](docs/websocket-api.md) for WebSocket API and frontend hook documentation
