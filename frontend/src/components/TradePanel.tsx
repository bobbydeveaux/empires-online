import React, { useState } from 'react';
import { TradeOffer, SpawnedCountryWithDetails } from '../types';
import { gamesAPI } from '../services/api';

interface TradePanelProps {
  gameId: number;
  trades: TradeOffer[];
  currentPlayer: SpawnedCountryWithDetails;
  players: SpawnedCountryWithDetails[];
  onTradeUpdate: () => void;
  onOpenPropose: () => void;
  onToast: (message: string, type: 'success' | 'error') => void;
}

const TradePanel: React.FC<TradePanelProps> = ({
  gameId,
  trades,
  currentPlayer,
  players,
  onTradeUpdate,
  onOpenPropose,
  onToast,
}) => {
  const [loading, setLoading] = useState<number | null>(null);

  const getCountryName = (countryId: number): string => {
    const player = players.find(p => p.id === countryId);
    return player ? `${player.player.username} (${player.country.name})` : `Country #${countryId}`;
  };

  const incomingTrades = trades.filter(
    t => t.receiver_country_id === currentPlayer.id && t.status === 'pending'
  );

  const outgoingTrades = trades.filter(
    t => t.proposer_country_id === currentPlayer.id && t.status === 'pending'
  );

  const handleAccept = async (tradeId: number) => {
    setLoading(tradeId);
    try {
      await gamesAPI.acceptTrade(gameId, tradeId);
      onToast('Trade accepted!', 'success');
      onTradeUpdate();
    } catch (err: any) {
      onToast(err.response?.data?.detail || 'Failed to accept trade', 'error');
    } finally {
      setLoading(null);
    }
  };

  const handleReject = async (tradeId: number) => {
    setLoading(tradeId);
    try {
      await gamesAPI.rejectTrade(gameId, tradeId);
      onToast('Trade rejected', 'success');
      onTradeUpdate();
    } catch (err: any) {
      onToast(err.response?.data?.detail || 'Failed to reject trade', 'error');
    } finally {
      setLoading(null);
    }
  };

  const handleCancel = async (tradeId: number) => {
    setLoading(tradeId);
    try {
      await gamesAPI.cancelTrade(gameId, tradeId);
      onToast('Trade cancelled', 'success');
      onTradeUpdate();
    } catch (err: any) {
      onToast(err.response?.data?.detail || 'Failed to cancel trade', 'error');
    } finally {
      setLoading(null);
    }
  };

  const renderResources = (label: string, gold: number, people: number, territory: number) => {
    const parts: string[] = [];
    if (gold > 0) parts.push(`${gold} gold`);
    if (people > 0) parts.push(`${people} people`);
    if (territory > 0) parts.push(`${territory} territory`);
    return parts.length > 0 ? `${label}: ${parts.join(', ')}` : `${label}: nothing`;
  };

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
        <h3 style={{ margin: 0 }}>Trade Offers</h3>
        <button className="btn" onClick={onOpenPropose}>
          Propose Trade
        </button>
      </div>

      {incomingTrades.length === 0 && outgoingTrades.length === 0 && (
        <p style={{ color: '#666', fontSize: '14px' }}>
          No pending trades. Use "Propose Trade" to send a trade offer to another player.
        </p>
      )}

      {incomingTrades.length > 0 && (
        <div style={{ marginBottom: '15px' }}>
          <h4 style={{ marginBottom: '10px' }}>Incoming Offers</h4>
          {incomingTrades.map(trade => (
            <div key={trade.id} className="trade-item trade-incoming">
              <div style={{ marginBottom: '8px' }}>
                <strong>From:</strong> {getCountryName(trade.proposer_country_id)}
              </div>
              <div style={{ fontSize: '14px', marginBottom: '4px' }}>
                {renderResources('They offer', trade.offer_gold, trade.offer_people, trade.offer_territory)}
              </div>
              <div style={{ fontSize: '14px', marginBottom: '10px' }}>
                {renderResources('They request', trade.request_gold, trade.request_people, trade.request_territory)}
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  className="btn btn-sm"
                  onClick={() => handleAccept(trade.id)}
                  disabled={loading === trade.id}
                >
                  {loading === trade.id ? 'Processing...' : 'Accept'}
                </button>
                <button
                  className="btn btn-danger btn-sm"
                  onClick={() => handleReject(trade.id)}
                  disabled={loading === trade.id}
                >
                  {loading === trade.id ? 'Processing...' : 'Reject'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {outgoingTrades.length > 0 && (
        <div>
          <h4 style={{ marginBottom: '10px' }}>Outgoing Offers</h4>
          {outgoingTrades.map(trade => (
            <div key={trade.id} className="trade-item trade-outgoing">
              <div style={{ marginBottom: '8px' }}>
                <strong>To:</strong> {getCountryName(trade.receiver_country_id)}
              </div>
              <div style={{ fontSize: '14px', marginBottom: '4px' }}>
                {renderResources('You offer', trade.offer_gold, trade.offer_people, trade.offer_territory)}
              </div>
              <div style={{ fontSize: '14px', marginBottom: '10px' }}>
                {renderResources('You request', trade.request_gold, trade.request_people, trade.request_territory)}
              </div>
              <button
                className="btn-secondary btn-sm"
                onClick={() => handleCancel(trade.id)}
                disabled={loading === trade.id}
              >
                {loading === trade.id ? 'Cancelling...' : 'Cancel'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TradePanel;
