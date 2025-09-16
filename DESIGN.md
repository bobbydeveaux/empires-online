# Design Document for Empires Online

## Game Overview

Empires is a strategic economic board game where players control historical empires, managing resources, developing territories, and competing for dominance. Each player starts with a country having specific resources and must make strategic decisions each round to grow their empire while managing internal stability.

## Game Rules and Mechanics

### Objective
The goal is to accumulate the most victory points through economic development, territorial expansion, and maintaining political stability over a fixed number of rounds.

### Game Components per Country
- **Gold**: Primary currency for transactions and development
- **Bonds**: Government debt instruments that generate income
- **Territories**: Land areas that can produce goods and support population
- **Goods**: Raw materials and manufactured products
- **People**: Population that can work in industries or create luxuries
- **Banks**: Financial institutions that cost gold to maintain but reduce revolt risk
- **Supporters**: Citizens who support the government (positive stability)
- **Revolters**: Citizens in revolt (negative stability)

### Game Phases

#### 1. Development Phase
Each round, players simultaneously make development decisions:

**Luxury Production**: 
- Luxuries = MIN(people, goods)
- Each luxury increases supporters by 1

**Industrial Production**:
- Industries = MIN(territories, people - luxuries)
- Each industry produces 1 gold

**Unemployment Check**:
- Unemployed = people - luxuries - industries
- If unemployed > 1, revolt increases by 1

**Banking Operations**:
- Players pay 1 gold per bank they maintain
- Revolt increases by (bonds - banks)
- Gold decreases by number of banks

**Resource Updates**:
- Supporters increase by luxuries produced
- Goods = MIN(territories, people) for next round

#### 2. Action Phase
Players can take additional actions (if implemented):
- Buy/Sell bonds
- Build banks (costs gold)
- Recruit people (costs gold)
- Acquire territories (costs gold)
- Trade with other players

#### 3. Stability Check
- If revolters > supporters, the country may collapse
- Countries with high revolt may lose resources

### Victory Conditions
After the final round, victory points are calculated based on:
- Total gold accumulated
- Number of territories controlled
- Number of supporters vs revolters ratio
- Bonus points for economic stability

### Game Flow
1. Game starts with predetermined number of rounds
2. Each round consists of Development Phase → Action Phase → Stability Check
3. Players make simultaneous decisions during Development Phase
4. Game ends after all rounds completed
5. Victory points calculated and winner determined

## Technical Implementation

### Entities

* Country
  * id
  * default_gold
  * default_bonds
  * default_territories
  * default_goods
  * default_people

* Player
  * id
  * username
  * password
  * email
  * email_verification_code
  * spawned_country_id

* Spawned_Country
  * id
  * country_id
  * game_id
  * gold
  * bonds
  * territories
  * goods
  * people
  * banks 

* Game
  * id
  * rounds
  * rounds_remaining
  * phase
  * creator_id
  * creation_date

Examples:

Country

|id|name|default_gold|default_bonds|default_territories|default_goods|default_people|
|---|-------|--------|-----|-----------------------|------------------|---|
| 4 | France | 5  | 1 | 4   | 2   | 3



Player

|id|username|password|email|email_verification|spawned-country-id|
|---|-------|--------|-----|-----------------------|------------------|
| 1 | Roger | 12345  | roger@gmail.com | abcdefg   | 111              |

Spawned Country

| id  | country_id  | game_id  | gold | bonds  | terrirtories | goods  | people  | banks  | supporters | revolters |
|---|---|---|---|---|---|---|---|---|---|---|
| 111  | 4  | 1  |  5 | 1  |  4 | 2  | 3  | 0  | 0 | 0

Game

|id|rounds|rounds_remaining|phase|creator_id|creation_date
|---|-------|--------|-----|-----------------------|------------------|
| 1 | 5 | 5  |  1 | 1 | 2019-12-30 22:17:10




## Development Phase Algorithm

### Core Development Logic
```pseudocode
// Phase 1: Calculate luxury production
luxuries = MIN(people, goods)

// Phase 2: Calculate industrial production  
available_workers = people - luxuries
industries = MIN(territories, available_workers)
gold_from_industries = industries

// Phase 3: Check for unemployment
unemployed = people - luxuries - industries
if unemployed > 1 then
    revolters = revolters + 1
end if

// Phase 4: Banking operations
gold = gold - banks  // Pay bank maintenance costs
banking_stability = bonds - banks
revolters = revolters + banking_stability

// Phase 5: Update supporters and resources
supporters = supporters + luxuries
gold = gold + gold_from_industries

// Phase 6: Prepare for next round
goods = MIN(territories, people)  // Goods production for next round
```

### Example Calculation
Starting state:
```
Country: France
Gold: 4
Bonds: 1
Banks: 1
Goods: 2
Territories: 4
People: 3
Supporters: 0
Revolters: 0
```

Step-by-step calculation:
```
Step 1: luxuries = MIN(3, 2) = 2
Step 2: available_workers = 3 - 2 = 1
        industries = MIN(4, 1) = 1
        gold_from_industries = 1
Step 3: unemployed = 3 - 2 - 1 = 0 (no revolt from unemployment)
Step 4: gold = 4 - 1 = 3 (bank maintenance)
        banking_stability = 1 - 1 = 0 (no revolt from banking)
Step 5: supporters = 0 + 2 = 2
        gold = 3 + 1 = 4 (add industrial income)
Step 6: goods = MIN(4, 3) = 3 (for next round)
```

Final state:
```
Gold: 4
Bonds: 1
Banks: 1
Goods: 3
Territories: 4
People: 3
Supporters: 2
Revolters: 0
```


## API Endpoints

### Game Management
```
POST /api/games
Description: Create a new game
Body: { "rounds": 5, "countries": ["France", "England", "Spain"] }
Response: { "game_id": 1, "status": "created" }

GET /api/games/{game_id}
Description: Get game state
Response: { "id": 1, "rounds": 5, "rounds_remaining": 5, "phase": "development", "players": [...] }

POST /api/games/{game_id}/start
Description: Start the game (all players must be joined)
Response: { "status": "started", "current_phase": "development" }
```

### Player Actions
```
POST /api/games/{game_id}/join
Description: Join a game
Body: { "player_id": 1, "country_id": 4 }
Response: { "spawned_country_id": 111 }

POST /api/games/{game_id}/countries/{spawned_country_id}/develop
Description: Execute development phase for a country
Body: { } (automatic calculation based on current resources)
Response: { "new_state": {...}, "changes": {...} }

POST /api/games/{game_id}/countries/{spawned_country_id}/actions
Description: Perform optional actions (buy bonds, build banks, etc.)
Body: { "action": "buy_bond", "quantity": 1 }
Response: { "success": true, "new_state": {...} }
```

### Game State Queries
```
GET /api/games/{game_id}/countries/{spawned_country_id}
Description: Get specific country state
Response: { 
  "id": 111, 
  "country_name": "France",
  "gold": 4, 
  "bonds": 1, 
  "territories": 4, 
  "goods": 3, 
  "people": 3, 
  "banks": 1, 
  "supporters": 2, 
  "revolters": 0 
}

GET /api/games/{game_id}/leaderboard
Description: Get current standings
Response: [
  { "player": "Roger", "country": "France", "score": 15, "gold": 4, "territories": 4 },
  ...
]
```

## Game State Management

### Game Phases
1. **Waiting**: Game created, waiting for players
2. **Development**: Players make development decisions
3. **Actions**: Optional action phase
4. **Resolution**: Calculate results and update game state
5. **Completed**: Game finished, show final scores

### State Transitions
```
Waiting → Development (when all players joined and game started)
Development → Actions (when all players completed development)
Actions → Resolution (after action timeout or all players done)
Resolution → Development (if rounds remaining > 0)
Resolution → Completed (if rounds remaining = 0)
```

### Validation Rules
- Players can only act on their own countries
- Development phase must complete before actions
- Actions must be valid (sufficient resources)
- Game must be in correct phase for operations

## Victory Point Calculation

### End Game Scoring
```pseudocode
base_score = gold * 1
territory_bonus = territories * 2
stability_bonus = MAX(0, (supporters - revolters)) * 1
economic_bonus = bonds * 1

total_score = base_score + territory_bonus + stability_bonus + economic_bonus

// Penalties
if revolters > supporters then
    total_score = total_score * 0.5  // Unstable government penalty
end if
```

## Copilot Instructions for Implementation

### Architecture Requirements
1. **Backend**: RESTful API with proper game state management
2. **Database**: Store games, players, countries, and game history
3. **Real-time**: WebSocket connections for live game updates
4. **Frontend**: React/Vue SPA with real-time game board
5. **Authentication**: User registration and session management

### Key Implementation Steps

#### 1. Database Schema
```sql
-- Core tables matching the entities above
CREATE TABLE countries (id, name, default_gold, default_bonds, default_territories, default_goods, default_people);
CREATE TABLE players (id, username, password_hash, email, email_verified);
CREATE TABLE games (id, rounds, rounds_remaining, phase, creator_id, created_at, started_at);
CREATE TABLE spawned_countries (id, country_id, game_id, player_id, gold, bonds, territories, goods, people, banks, supporters, revolters);
CREATE TABLE game_history (id, game_id, round_number, spawned_country_id, action_type, details, timestamp);
```

#### 2. Core Game Logic
- Implement development phase calculation exactly as specified
- Add validation for all game state transitions
- Create game master service to coordinate multiplayer games
- Implement action queue system for simultaneous play

#### 3. API Development
- Implement all endpoints listed above
- Add proper error handling and validation
- Use WebSockets for real-time game state updates
- Add rate limiting and security measures

#### 4. Frontend Requirements
- Game lobby for creating/joining games
- Live game board showing all player states
- Turn-based interface with clear phase indicators
- Resource management interface
- Leaderboard and scoring display

#### 5. Game Flow Implementation
```pseudocode
1. Create game lobby
2. Players join and select countries
3. Game starts in Development phase
4. All players submit development (automatic calculation)
5. Move to Actions phase (optional)
6. Process all actions and update state
7. Show round results
8. Repeat for remaining rounds
9. Calculate final scores and declare winner
```

### Testing Strategy
- Unit tests for all game logic calculations
- Integration tests for API endpoints
- End-to-end tests for complete game scenarios
- Load testing for concurrent games
- Validation tests for all edge cases

### Security Considerations
- Authenticate all API calls
- Validate game state before allowing actions
- Prevent cheating through state manipulation
- Rate limit API calls to prevent abuse
- Secure WebSocket connections

## Advanced Game Variants

### Extended Rules (Optional Implementation)

#### Trade System
- Players can trade resources between countries
- Trade routes require mutual agreement
- Trading costs may apply based on distance/relationships

#### Diplomatic Relations
- Alliance system affecting trade and warfare
- Diplomatic points for negotiation
- Treaties and agreements

#### Random Events
- Economic booms/busts affecting all players
- Natural disasters affecting specific countries
- Political events changing game rules temporarily

#### Technology Tree
- Research system for improving efficiency
- Technologies affect production formulas
- Military technologies for conflict resolution

### Game Variants

#### Short Game (3 rounds)
- Faster gameplay for casual sessions
- Reduced starting resources
- Higher scoring multipliers

#### Epic Game (10+ rounds)
- Extended gameplay with more strategic depth
- Additional action phases per round
- More complex scoring system

#### Team Play
- Players form alliances
- Shared victory conditions
- Collaborative resource management

## Balancing Considerations

### Resource Scaling
- Ensure no single strategy dominates
- Balance luxury vs industrial production
- Make banks worthwhile but not overpowered
- Keep unemployment mechanics relevant

### Victory Point Balance
```
Gold: 1 point per gold (liquid wealth)
Territories: 2 points per territory (strategic value)
Stability: 1 point per net supporter (political success)
Bonds: 1 point per bond (economic infrastructure)
```

### Game Length Optimization
- 5 rounds provides good balance of strategy vs time
- Development phase should be quick (automatic)
- Action phase should have reasonable time limits
- Real-time updates keep all players engaged

## Implementation Priorities

### Phase 1: Core Game
1. Basic multiplayer lobby
2. Core development algorithm
3. Simple scoring system
4. Web interface for game play

### Phase 2: Enhanced Features
1. Advanced actions (bonds, banks, trading)
2. Real-time updates via WebSockets
3. Game history and statistics
4. Mobile-responsive design

### Phase 3: Advanced Features
1. Tournament system
2. AI opponents
3. Game variants and custom rules
4. Social features and player profiles

## Performance Requirements

### Scalability Targets
- Support 100+ concurrent games
- Handle 1000+ registered users
- Real-time updates with <100ms latency
- Game state persistence with backup

### Database Optimization
- Index game queries for performance
- Archive completed games
- Optimize for read-heavy game state queries
- Consider caching for active games





