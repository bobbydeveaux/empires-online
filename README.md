# Empires Online

An online implementation of the classic Empires board game - a strategic economic game where players control historical empires, manage resources, and compete for dominance.

## Game Overview

Empires is a turn-based strategy game where players:
- Manage economic resources (gold, goods, people, territories)
- Balance luxury production vs industrial development
- Handle political stability through supporters and revolters
- Make strategic banking and bond decisions
- Compete over multiple rounds for the highest score

## Key Features

- **Multiplayer Support**: Real-time games with multiple players
- **Strategic Depth**: Complex economic decisions with trade-offs
- **Political Management**: Balance stability vs growth
- **Historical Themes**: Play as classic empires like France, England, Spain
- **Score-based Victory**: Multiple paths to victory through different strategies

## Quick Start

1. **Create Account**: Register and verify email
2. **Join/Create Game**: Enter game lobby and select your empire
3. **Play Rounds**: Make development decisions each round
4. **Strategic Actions**: Optionally buy bonds, build banks, trade resources
5. **Win**: Accumulate the most victory points after all rounds

## Game Mechanics

Each round consists of:
- **Development Phase**: Automatic calculation of luxuries, industries, and stability
- **Action Phase**: Optional strategic actions (buying bonds, building infrastructure)
- **Resolution**: State updates and preparation for next round

Victory is determined by:
- Gold accumulated
- Territories controlled  
- Political stability (supporters vs revolters)
- Economic infrastructure (bonds, banks)

## Technical Stack

- **Backend**: RESTful API with WebSocket support
- **Database**: Relational database for game state persistence
- **Frontend**: Modern SPA with real-time updates
- **Authentication**: Secure user management system

## Documentation

- See [DESIGN.md](DESIGN.md) for complete game rules, API specifications, and implementation details
- Includes full copilot instructions for building the online version

## Development Status

This project is in development. The design document contains comprehensive specifications for implementing the complete online game.
