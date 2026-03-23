import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TradePanel from './TradePanel';
import { gamesAPI } from '../services/api';
import { TradeOffer, SpawnedCountryWithDetails } from '../types';

jest.mock('../services/api', () => ({
  gamesAPI: {
    acceptTrade: jest.fn(),
    rejectTrade: jest.fn(),
    cancelTrade: jest.fn(),
  },
}));

const mockPlayer = (id: number, playerId: number, username: string, countryName: string): SpawnedCountryWithDetails => ({
  id,
  country_id: id,
  game_id: 1,
  player_id: playerId,
  gold: 100,
  bonds: 5,
  territories: 10,
  goods: 8,
  people: 20,
  banks: 2,
  supporters: 5,
  revolters: 2,
  development_completed: false,
  actions_completed: false,
  country: { id, name: countryName, default_gold: 10, default_bonds: 2, default_territories: 5, default_goods: 3, default_people: 10 },
  player: { id: playerId, username, email: `${username}@test.com`, email_verified: true, created_at: '2024-01-01' },
});

const currentPlayer = mockPlayer(1, 10, 'Alice', 'Arcadia');
const otherPlayer = mockPlayer(2, 20, 'Bob', 'Britannia');
const players = [currentPlayer, otherPlayer];

const makeTrade = (overrides: Partial<TradeOffer> = {}): TradeOffer => ({
  id: 1,
  game_id: 1,
  proposer_country_id: 2,
  receiver_country_id: 1,
  offer_gold: 10,
  offer_people: 5,
  offer_territory: 0,
  request_gold: 0,
  request_people: 0,
  request_territory: 3,
  status: 'pending',
  created_at: '2024-01-01T00:00:00Z',
  ...overrides,
});

describe('TradePanel', () => {
  const mockOnTradeUpdate = jest.fn();
  const mockOnOpenPropose = jest.fn();
  const mockOnToast = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders empty state when no trades', () => {
    render(
      <TradePanel
        gameId={1}
        trades={[]}
        currentPlayer={currentPlayer}
        players={players}
        onTradeUpdate={mockOnTradeUpdate}
        onOpenPropose={mockOnOpenPropose}
        onToast={mockOnToast}
      />
    );

    expect(screen.getByText(/No pending trades/)).toBeInTheDocument();
    expect(screen.getByText('Propose Trade')).toBeInTheDocument();
  });

  it('displays incoming trades with Accept and Reject buttons', () => {
    const incomingTrade = makeTrade();

    render(
      <TradePanel
        gameId={1}
        trades={[incomingTrade]}
        currentPlayer={currentPlayer}
        players={players}
        onTradeUpdate={mockOnTradeUpdate}
        onOpenPropose={mockOnOpenPropose}
        onToast={mockOnToast}
      />
    );

    expect(screen.getByText('Incoming Offers')).toBeInTheDocument();
    expect(screen.getByText(/Bob \(Britannia\)/)).toBeInTheDocument();
    expect(screen.getByText('Accept')).toBeInTheDocument();
    expect(screen.getByText('Reject')).toBeInTheDocument();
  });

  it('displays outgoing trades with Cancel button', () => {
    const outgoingTrade = makeTrade({
      proposer_country_id: 1,
      receiver_country_id: 2,
    });

    render(
      <TradePanel
        gameId={1}
        trades={[outgoingTrade]}
        currentPlayer={currentPlayer}
        players={players}
        onTradeUpdate={mockOnTradeUpdate}
        onOpenPropose={mockOnOpenPropose}
        onToast={mockOnToast}
      />
    );

    expect(screen.getByText('Outgoing Offers')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('calls acceptTrade API and callbacks on Accept click', async () => {
    (gamesAPI.acceptTrade as jest.Mock).mockResolvedValue({});
    const incomingTrade = makeTrade();

    render(
      <TradePanel
        gameId={1}
        trades={[incomingTrade]}
        currentPlayer={currentPlayer}
        players={players}
        onTradeUpdate={mockOnTradeUpdate}
        onOpenPropose={mockOnOpenPropose}
        onToast={mockOnToast}
      />
    );

    await userEvent.click(screen.getByText('Accept'));

    expect(gamesAPI.acceptTrade).toHaveBeenCalledWith(1, 1);
    expect(mockOnToast).toHaveBeenCalledWith('Trade accepted!', 'success');
    expect(mockOnTradeUpdate).toHaveBeenCalled();
  });

  it('calls rejectTrade API on Reject click', async () => {
    (gamesAPI.rejectTrade as jest.Mock).mockResolvedValue({});
    const incomingTrade = makeTrade();

    render(
      <TradePanel
        gameId={1}
        trades={[incomingTrade]}
        currentPlayer={currentPlayer}
        players={players}
        onTradeUpdate={mockOnTradeUpdate}
        onOpenPropose={mockOnOpenPropose}
        onToast={mockOnToast}
      />
    );

    await userEvent.click(screen.getByText('Reject'));

    expect(gamesAPI.rejectTrade).toHaveBeenCalledWith(1, 1);
    expect(mockOnToast).toHaveBeenCalledWith('Trade rejected', 'success');
  });

  it('calls cancelTrade API on Cancel click', async () => {
    (gamesAPI.cancelTrade as jest.Mock).mockResolvedValue({});
    const outgoingTrade = makeTrade({
      proposer_country_id: 1,
      receiver_country_id: 2,
    });

    render(
      <TradePanel
        gameId={1}
        trades={[outgoingTrade]}
        currentPlayer={currentPlayer}
        players={players}
        onTradeUpdate={mockOnTradeUpdate}
        onOpenPropose={mockOnOpenPropose}
        onToast={mockOnToast}
      />
    );

    await userEvent.click(screen.getByText('Cancel'));

    expect(gamesAPI.cancelTrade).toHaveBeenCalledWith(1, 1);
  });

  it('calls onOpenPropose when Propose Trade button is clicked', async () => {
    render(
      <TradePanel
        gameId={1}
        trades={[]}
        currentPlayer={currentPlayer}
        players={players}
        onTradeUpdate={mockOnTradeUpdate}
        onOpenPropose={mockOnOpenPropose}
        onToast={mockOnToast}
      />
    );

    await userEvent.click(screen.getByText('Propose Trade'));

    expect(mockOnOpenPropose).toHaveBeenCalled();
  });

  it('shows error toast on API failure', async () => {
    (gamesAPI.acceptTrade as jest.Mock).mockRejectedValue({
      response: { data: { detail: 'Insufficient resources' } },
    });
    const incomingTrade = makeTrade();

    render(
      <TradePanel
        gameId={1}
        trades={[incomingTrade]}
        currentPlayer={currentPlayer}
        players={players}
        onTradeUpdate={mockOnTradeUpdate}
        onOpenPropose={mockOnOpenPropose}
        onToast={mockOnToast}
      />
    );

    await userEvent.click(screen.getByText('Accept'));

    expect(mockOnToast).toHaveBeenCalledWith('Insufficient resources', 'error');
  });
});
