import React, { useState } from 'react';
import { SpawnedCountryWithDetails, TradePropose } from '../types';

interface ProposeTradeProps {
  currentPlayer: SpawnedCountryWithDetails;
  otherPlayers: SpawnedCountryWithDetails[];
  onPropose: (trade: TradePropose) => void;
  onClose: () => void;
  loading: boolean;
}

const ProposeTrade: React.FC<ProposeTradeProps> = ({
  currentPlayer,
  otherPlayers,
  onPropose,
  onClose,
  loading,
}) => {
  const [receiverId, setReceiverId] = useState<number>(otherPlayers[0]?.id ?? 0);
  const [offerGold, setOfferGold] = useState(0);
  const [offerPeople, setOfferPeople] = useState(0);
  const [offerTerritory, setOfferTerritory] = useState(0);
  const [requestGold, setRequestGold] = useState(0);
  const [requestPeople, setRequestPeople] = useState(0);
  const [requestTerritory, setRequestTerritory] = useState(0);

  const hasOffer = offerGold > 0 || offerPeople > 0 || offerTerritory > 0;
  const hasRequest = requestGold > 0 || requestPeople > 0 || requestTerritory > 0;
  const canAfford =
    offerGold <= currentPlayer.gold &&
    offerPeople <= currentPlayer.people &&
    offerTerritory <= currentPlayer.territories;
  const isValid = receiverId > 0 && hasOffer && hasRequest && canAfford;

  const handleSubmit = () => {
    if (!isValid) return;
    onPropose({
      receiver_country_id: receiverId,
      offer_gold: offerGold,
      offer_people: offerPeople,
      offer_territory: offerTerritory,
      request_gold: requestGold,
      request_people: requestPeople,
      request_territory: requestTerritory,
    });
  };

  const sliderRow = (
    label: string,
    value: number,
    max: number,
    onChange: (v: number) => void
  ) => (
    <div style={{ marginBottom: '10px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '4px' }}>
        <span>{label}</span>
        <span>{value} / {max}</span>
      </div>
      <input
        type="range"
        min={0}
        max={max}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        style={{ width: '100%' }}
        disabled={loading}
      />
    </div>
  );

  return (
    <div className="trade-modal-overlay" onClick={onClose}>
      <div className="trade-modal" onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h3 style={{ margin: 0 }}>Propose Trade</h3>
          <button className="btn-secondary btn-sm" onClick={onClose}>Close</button>
        </div>

        <div className="form-group">
          <label>Trade with:</label>
          <select
            value={receiverId}
            onChange={e => setReceiverId(Number(e.target.value))}
            disabled={loading}
          >
            {otherPlayers.map(p => (
              <option key={p.id} value={p.id}>
                {p.player.username} ({p.country.name})
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-2" style={{ gap: '15px', marginTop: '15px' }}>
          <div>
            <h4 style={{ marginTop: 0, color: '#d32f2f' }}>You Offer</h4>
            {sliderRow('Gold', offerGold, currentPlayer.gold, setOfferGold)}
            {sliderRow('People', offerPeople, currentPlayer.people, setOfferPeople)}
            {sliderRow('Territory', offerTerritory, currentPlayer.territories, setOfferTerritory)}
          </div>
          <div>
            <h4 style={{ marginTop: 0, color: '#2e7d32' }}>You Request</h4>
            {sliderRow('Gold', requestGold, 99, setRequestGold)}
            {sliderRow('People', requestPeople, 99, setRequestPeople)}
            {sliderRow('Territory', requestTerritory, 99, setRequestTerritory)}
          </div>
        </div>

        {!canAfford && (
          <div className="error" style={{ marginTop: '10px' }}>
            You don't have enough resources to offer this trade.
          </div>
        )}

        <div style={{ marginTop: '15px', display: 'flex', gap: '10px' }}>
          <button
            className="btn"
            onClick={handleSubmit}
            disabled={loading || !isValid}
          >
            {loading ? 'Proposing...' : 'Propose Trade'}
          </button>
          <button className="btn-secondary" onClick={onClose} disabled={loading}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProposeTrade;
