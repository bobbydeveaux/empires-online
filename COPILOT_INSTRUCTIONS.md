# Copilot Instructions for Empires Online

## Project Overview
You are building an online version of the classic "Empires" board game - a strategic economic game where players control historical empires and compete through resource management and political stability.

## Core Game Concept
**Empires** is a turn-based strategy game where 2-6 players control historical countries (France, England, Spain, etc.) and compete over multiple rounds to accumulate the most victory points through economic development and political management.

## Game Rules Summary

### Resources Per Country
- **Gold**: Primary currency for actions and scoring
- **Bonds**: Government debt that generates benefits but requires banks
- **Territories**: Land that produces goods and supports population
- **Goods**: Materials for luxury production
- **People**: Population that works in industries or creates luxuries
- **Banks**: Cost gold to maintain but provide stability
- **Supporters**: Citizens supporting the government (positive stability)
- **Revolters**: Citizens in revolt (negative stability)

### Core Game Loop
1. **Development Phase** (automatic): Calculate luxuries, industries, unemployment, banking costs
2. **Action Phase** (optional): Players can buy bonds, build banks, trade resources
3. **Round End**: Update state, check stability, prepare for next round
4. **Game End**: Calculate victory points after all rounds

### Development Algorithm (Critical - Implement Exactly)
```pseudocode
// This is the heart of the game - implement exactly as specified
luxuries = MIN(people, goods)
available_workers = people - luxuries
industries = MIN(territories, available_workers)
unemployed = people - luxuries - industries

if unemployed > 1 then
    revolters = revolters + 1
end if

gold = gold - banks  // Bank maintenance cost
revolters = revolters + (bonds - banks)  // Banking stability effect
supporters = supporters + luxuries
gold = gold + industries  // Industrial income
goods = MIN(territories, people)  // Next round's goods
```

## Technical Architecture

### Backend Requirements
- **RESTful API** with proper game state management
- **WebSocket support** for real-time multiplayer updates
- **Database** for persistent game state and user management
- **Authentication system** for secure player accounts

### Database Schema (Essential Tables)
```sql
countries (id, name, default_gold, default_bonds, default_territories, default_goods, default_people)
players (id, username, password_hash, email, email_verified)
games (id, rounds, rounds_remaining, phase, creator_id, created_at)
spawned_countries (id, country_id, game_id, player_id, gold, bonds, territories, goods, people, banks, supporters, revolters)
game_history (id, game_id, round_number, spawned_country_id, action_type, details, timestamp)
```

### Key API Endpoints
- `POST /api/games` - Create new game
- `POST /api/games/{id}/join` - Join existing game
- `POST /api/games/{id}/countries/{country_id}/develop` - Execute development phase
- `POST /api/games/{id}/countries/{country_id}/actions` - Perform actions
- `GET /api/games/{id}/countries/{country_id}` - Get country state
- `GET /api/games/{id}/leaderboard` - Current standings

### Frontend Requirements
- **Game Lobby**: Create/join games, select countries
- **Game Board**: Real-time view of all player states
- **Turn Interface**: Clear phase indicators and action buttons
- **Resource Display**: Current gold, territories, people, etc.
- **Scoring System**: Live leaderboard with victory point calculations

## Implementation Checklist

### Phase 1: Core Game
- [ ] Set up database schema with all required tables
- [ ] Implement user authentication and registration
- [ ] Create game lobby for creating/joining games
- [ ] Implement core development algorithm exactly as specified
- [ ] Build basic web interface for gameplay
- [ ] Add real-time game state updates
- [ ] Implement victory point calculation

### Phase 2: Enhanced Features
- [ ] Add optional action system (buy bonds, build banks)
- [ ] Implement trading between players
- [ ] Add game history and statistics
- [ ] Create comprehensive API documentation
- [ ] Add input validation and error handling
- [ ] Implement game spectator mode

### Phase 3: Polish
- [ ] Add AI opponents for single-player practice
- [ ] Create tournament system
- [ ] Add game variants (short/long games)
- [ ] Implement advanced rules (diplomacy, events)
- [ ] Mobile-responsive design
- [ ] Performance optimization

## Critical Implementation Notes

### Game State Management
- Games progress through phases: Waiting → Development → Actions → Resolution
- All players must complete development before moving to actions
- Use WebSockets to keep all players synchronized
- Validate all state changes server-side to prevent cheating

### Victory Point Calculation
```
Base Score = gold * 1
Territory Bonus = territories * 2
Stability Bonus = MAX(0, supporters - revolters) * 1
Economic Bonus = bonds * 1
Instability Penalty = If revolters > supporters, multiply total by 0.5
```

### Balancing Considerations
- Luxury production vs industrial development creates strategic tension
- Banks are expensive but necessary for bond-heavy strategies
- Unemployment creates automatic revolt pressure
- Multiple viable strategies should exist

## Testing Strategy
- Unit tests for development algorithm with known inputs/outputs
- Integration tests for all API endpoints
- End-to-end tests for complete game scenarios
- Load testing for concurrent multiplayer games
- Validation of edge cases (zero resources, maximum revolt, etc.)

## Security Requirements
- Authenticate all API calls
- Validate game state before allowing any actions
- Rate limit to prevent API abuse
- Secure WebSocket connections
- Prevent state manipulation through client-side changes

## Performance Targets
- Support 100+ concurrent games
- Real-time updates with <100ms latency
- Handle 1000+ registered users
- Database queries optimized for game state reads

## Development Philosophy
This is a **strategic economic game** - focus on making economic decisions meaningful and creating interesting trade-offs. The development phase should feel automatic and quick, while strategic decisions in the action phase should feel impactful.

The game should be **easy to learn but hard to master** - the basic mechanics are simple (manage resources, avoid unemployment) but the strategic depth comes from balancing competing priorities over multiple rounds.

Remember: This is about **empire management**, not warfare. Players compete through economic efficiency and political stability, not military conflict.