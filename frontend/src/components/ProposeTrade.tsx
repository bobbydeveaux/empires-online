import React, { useState } from 'react';
import { SpawnedCountryWithDetails } from '../types';
import { gamesAPI } from '../services/api';

interface ProposeTradeProps {
  gameId: number;
  currentPlayer: SpawnedCountryWithDetails;
  players: SpawnedCountryWithDetails[];
  onClose: () => void;
  onTradeProposed: () => void;
  onToast: (message: string, type: 'success' | 'error') => void;
}

const ProposeTrade: React.FC<ProposeTradeProps> = ({
  gameId,
  currentPlayer,
  players,
  onClose,
  onTradeProposed,
  onToast,
}) => {
  const otherPlayers = players.filter(p => p.id !== currentPlayer.id);

  const [receiverId, setReceiverId] = useState<number>(
    otherPlayers.length > 0 ? otherPlayers[0].id : 0
  );
  const [offerGold, setOfferGold] = useState(0);
  const [offerPeople, setOfferPeople] = useState(0);
  const [offerTerritory, setOfferTerritory] = useState(0);
  const [requestGold, setRequestGold] = useState(0);
  const [requestPeople, setRequestPeople] = useState(0);
  const [requestTerritory, setRequestTerritory] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  const hasOffer = offerGold > 0 || offerPeople > 0 || offerTerritory > 0;
  const hasRequest = requestGold > 0 || requestPeople > 0 || requestTerritory > 0;
  const canSubmit = receiverId > 0 && (hasOffer || hasRequest) && !submitting;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      await gamesAPI.proposeTrade(gameId, {
        receiver_country_id: receiverId,
        offer_gold: offerGold,
        offer_people: offerPeople,
        offer_territory: offerTerritory,
        request_gold: requestGold,
        request_people: requestPeople,
        request_territory: requestTerritory,
      });
      onToast('Trade proposed!', 'success');
      onTradeProposed();
      onClose();
    } catch (err: any) {
      onToast(err.response?.data?.detail || 'Failed to propose trade', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const renderSlider = (
    label: string,
    value: number,
    max: number,
    onChange: (val: number) => void,
  ) => (
    <div style={{ marginBottom: '12px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px', marginBottom: '4px' }}>
        <span>{label}</span>
        <span style={{ fontWeight: 'bold' }}>{value}</span>
      </div>
      <input
        type="range"
        min={0}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ width: '100%' }}
      />
    </div>
  );

  return (
    <div className="trade-modal-overlay" onClick={onClose}>
      <div className="trade-modal" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h3 style={{ margin: 0 }}>Propose Trade</h3>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer', color: '#666' }}
          >
            X
          </button>
        </div>

        <div className="form-group">
          <label>Trade with:</label>
          <select
            value={receiverId}
            onChange={(e) => setReceiverId(Number(e.target.value))}
          >
            {otherPlayers.map(p => (
              <option key={p.id} value={p.id}>
                {p.player.username} ({p.country.name})
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-2" style={{ gap: '20px', marginTop: '15px' }}>
          <div>
            <h4 style={{ marginBottom: '10px', color: '#d32f2f' }}>You Offer</h4>
            <div className="trade-slider-section">
              {renderSlider('Gold', offerGold, currentPlayer.gold, setOfferGold)}
              {renderSlider('People', offerPeople, currentPlayer.people, setOfferPeople)}
              {renderSlider('Territory', offerTerritory, currentPlayer.territories, setOfferTerritory)}
            </div>
          </div>

          <div>
            <h4 style={{ marginBottom: '10px', color: '#2e7d32' }}>You Request</h4>
            <div className="trade-slider-section">
              {renderSlider('Gold', requestGold, 999, setRequestGold)}
              {renderSlider('People', requestPeople, 999, setRequestPeople)}
              {renderSlider('Territory', requestTerritory, 999, setRequestTerritory)}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px', marginTop: '20px', justifyContent: 'flex-end' }}>
          <button className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn"
            onClick={handleSubmit}
            disabled={!canSubmit}
          >
            {submitting ? 'Sending...' : 'Send Proposal'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProposeTrade;
