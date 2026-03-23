import React from 'react';
import { TradeOffer, SpawnedCountryWithDetails } from '../types';

interface TradePanelProps {
  trades: TradeOffer[];
  currentPlayer: SpawnedCountryWithDetails;
  onAccept: (tradeId: number) => void;
  onReject: (tradeId: number) => void;
  onCancel: (tradeId: number) => void;
  onOpenPropose: () => void;
  loading: boolean;
}

const resourceSummary = (gold: number, people: number, territory: number): string => {
  const parts: string[] = [];
  if (gold > 0) parts.push(`${gold} gold`);
  if (people > 0) parts.push(`${people} people`);
  if (territory > 0) parts.push(`${territory} territory`);
  return parts.length > 0 ? parts.join(', ') : 'nothing';
};

const TradePanel: React.FC<TradePanelProps> = ({
  trades,
  currentPlayer,
  onAccept,
  onReject,
  onCancel,
  onOpenPropose,
  loading,
}) => {
  const incoming = trades.filter(t => t.receiver_country_id === currentPlayer.id);
  const outgoing = trades.filter(t => t.proposer_country_id === currentPlayer.id);

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>Trade Offers</h3>
        <button className="btn btn-sm" onClick={onOpenPropose} disabled={loading}>
          Propose Trade
        </button>
      </div>

      {trades.length === 0 && (
        <p style={{ fontSize: '14px', color: '#666', marginTop: '10px' }}>
          No active trades. Propose a trade to another player!
        </p>
      )}

      {incoming.length > 0 && (
        <div style={{ marginTop: '15px' }}>
          <h4 style={{ marginBottom: '8px' }}>Incoming Offers</h4>
          {incoming.map(trade => (
            <div key={trade.id} className="trade-card trade-incoming">
              <div className="trade-card-header">
                <strong>{trade.proposer_name || `Country #${trade.proposer_country_id}`}</strong>
                {trade.proposer_country_name && (
                  <span style={{ color: '#666', fontSize: '12px' }}> ({trade.proposer_country_name})</span>
                )}
              </div>
              <div className="trade-card-body">
                <div>
                  <span style={{ color: '#2e7d32', fontWeight: 500 }}>You receive:</span>{' '}
                  {resourceSummary(trade.offer_gold, trade.offer_people, trade.offer_territory)}
                </div>
                <div>
                  <span style={{ color: '#d32f2f', fontWeight: 500 }}>They request:</span>{' '}
                  {resourceSummary(trade.request_gold, trade.request_people, trade.request_territory)}
                </div>
              </div>
              <div className="trade-card-actions">
                <button
                  className="btn btn-sm btn-recruit"
                  onClick={() => onAccept(trade.id)}
                  disabled={loading}
                >
                  Accept
                </button>
                <button
                  className="btn btn-sm btn-danger"
                  onClick={() => onReject(trade.id)}
                  disabled={loading}
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {outgoing.length > 0 && (
        <div style={{ marginTop: '15px' }}>
          <h4 style={{ marginBottom: '8px' }}>Outgoing Offers</h4>
          {outgoing.map(trade => (
            <div key={trade.id} className="trade-card trade-outgoing">
              <div className="trade-card-header">
                <strong>To: {trade.receiver_name || `Country #${trade.receiver_country_id}`}</strong>
                {trade.receiver_country_name && (
                  <span style={{ color: '#666', fontSize: '12px' }}> ({trade.receiver_country_name})</span>
                )}
              </div>
              <div className="trade-card-body">
                <div>
                  <span style={{ color: '#d32f2f', fontWeight: 500 }}>You offer:</span>{' '}
                  {resourceSummary(trade.offer_gold, trade.offer_people, trade.offer_territory)}
                </div>
                <div>
                  <span style={{ color: '#2e7d32', fontWeight: 500 }}>You request:</span>{' '}
                  {resourceSummary(trade.request_gold, trade.request_people, trade.request_territory)}
                </div>
              </div>
              <div className="trade-card-actions">
                <button
                  className="btn btn-sm btn-secondary"
                  onClick={() => onCancel(trade.id)}
                  disabled={loading}
                >
                  Cancel
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TradePanel;
