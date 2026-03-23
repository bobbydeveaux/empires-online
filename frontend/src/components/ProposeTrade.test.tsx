import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ProposeTrade from './ProposeTrade';
import { gamesAPI } from '../services/api';
import { SpawnedCountryWithDetails } from '../types';

jest.mock('../services/api', () => ({
  gamesAPI: {
    proposeTrade: jest.fn(),
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

describe('ProposeTrade', () => {
  const mockOnClose = jest.fn();
  const mockOnTradeProposed = jest.fn();
  const mockOnToast = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders modal with player selector and resource sliders', () => {
    render(
      <ProposeTrade
        gameId={1}
        currentPlayer={currentPlayer}
        players={players}
        onClose={mockOnClose}
        onTradeProposed={mockOnTradeProposed}
        onToast={mockOnToast}
      />
    );

    expect(screen.getByText('Propose Trade')).toBeInTheDocument();
    expect(screen.getByText('You Offer')).toBeInTheDocument();
    expect(screen.getByText('You Request')).toBeInTheDocument();
    expect(screen.getByText('Send Proposal')).toBeInTheDocument();
    expect(screen.getByText('Bob (Britannia)')).toBeInTheDocument();
  });

  it('disables Send Proposal when no resources selected', () => {
    render(
      <ProposeTrade
        gameId={1}
        currentPlayer={currentPlayer}
        players={players}
        onClose={mockOnClose}
        onTradeProposed={mockOnTradeProposed}
        onToast={mockOnToast}
      />
    );

    expect(screen.getByText('Send Proposal')).toBeDisabled();
  });

  it('calls onClose when Cancel is clicked', async () => {
    render(
      <ProposeTrade
        gameId={1}
        currentPlayer={currentPlayer}
        players={players}
        onClose={mockOnClose}
        onTradeProposed={mockOnTradeProposed}
        onToast={mockOnToast}
      />
    );

    await userEvent.click(screen.getByText('Cancel'));

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('calls onClose when overlay is clicked', async () => {
    render(
      <ProposeTrade
        gameId={1}
        currentPlayer={currentPlayer}
        players={players}
        onClose={mockOnClose}
        onTradeProposed={mockOnTradeProposed}
        onToast={mockOnToast}
      />
    );

    // Click on overlay (the outer div)
    const overlay = document.querySelector('.trade-modal-overlay');
    if (overlay) {
      await userEvent.click(overlay);
    }

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('submits trade proposal via API', async () => {
    (gamesAPI.proposeTrade as jest.Mock).mockResolvedValue({});

    render(
      <ProposeTrade
        gameId={1}
        currentPlayer={currentPlayer}
        players={players}
        onClose={mockOnClose}
        onTradeProposed={mockOnTradeProposed}
        onToast={mockOnToast}
      />
    );

    // Change gold offer slider to enable submit
    const sliders = screen.getAllByRole('slider');
    // First slider is offer gold
    fireEvent.change(sliders[0], { target: { value: '10' } });

    await userEvent.click(screen.getByText('Send Proposal'));

    expect(gamesAPI.proposeTrade).toHaveBeenCalledWith(1, {
      receiver_country_id: 2,
      offer_gold: 10,
      offer_people: 0,
      offer_territory: 0,
      request_gold: 0,
      request_people: 0,
      request_territory: 0,
    });
    expect(mockOnToast).toHaveBeenCalledWith('Trade proposed!', 'success');
    expect(mockOnTradeProposed).toHaveBeenCalled();
    expect(mockOnClose).toHaveBeenCalled();
  });

  it('shows error toast on API failure', async () => {
    (gamesAPI.proposeTrade as jest.Mock).mockRejectedValue({
      response: { data: { detail: 'Cannot trade with yourself' } },
    });

    render(
      <ProposeTrade
        gameId={1}
        currentPlayer={currentPlayer}
        players={players}
        onClose={mockOnClose}
        onTradeProposed={mockOnTradeProposed}
        onToast={mockOnToast}
      />
    );

    const sliders = screen.getAllByRole('slider');
    fireEvent.change(sliders[0], { target: { value: '10' } });

    await userEvent.click(screen.getByText('Send Proposal'));

    expect(mockOnToast).toHaveBeenCalledWith('Cannot trade with yourself', 'error');
  });

  it('limits offer slider max to player resources', () => {
    render(
      <ProposeTrade
        gameId={1}
        currentPlayer={currentPlayer}
        players={players}
        onClose={mockOnClose}
        onTradeProposed={mockOnTradeProposed}
        onToast={mockOnToast}
      />
    );

    const sliders = screen.getAllByRole('slider');
    // Offer gold slider (first) should have max = currentPlayer.gold = 100
    expect(sliders[0]).toHaveAttribute('max', '100');
    // Offer people slider (second) should have max = currentPlayer.people = 20
    expect(sliders[1]).toHaveAttribute('max', '20');
    // Offer territory slider (third) should have max = currentPlayer.territories = 10
    expect(sliders[2]).toHaveAttribute('max', '10');
  });
});
