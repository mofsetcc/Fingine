import React from 'react';
import { WatchlistStockWithPrice } from '../types/watchlist';

interface WatchlistStockCardProps {
  stock: WatchlistStockWithPrice;
  onRemove: () => void;
  onEdit: () => void;
  onViewAnalysis: (ticker: string) => void;
}

const WatchlistStockCard: React.FC<WatchlistStockCardProps> = ({
  stock,
  onRemove,
  onEdit,
  onViewAnalysis,
}) => {
  const formatPrice = (price: number | null | undefined) => {
    if (price === null || price === undefined) return 'N/A';
    return `¥${price.toLocaleString()}`;
  };

  const formatChange = (change: number | null | undefined, percent: number | null | undefined) => {
    if (change === null || change === undefined || percent === null || percent === undefined) {
      return 'N/A';
    }
    
    const sign = change >= 0 ? '+' : '';
    return `${sign}¥${change.toFixed(2)} (${sign}${percent.toFixed(2)}%)`;
  };

  const getChangeClass = (change: number | null | undefined) => {
    if (change === null || change === undefined) return '';
    return change >= 0 ? 'positive' : 'negative';
  };

  const formatVolume = (volume: number | null | undefined) => {
    if (volume === null || volume === undefined) return 'N/A';
    
    if (volume >= 1000000) {
      return `${(volume / 1000000).toFixed(1)}M`;
    } else if (volume >= 1000) {
      return `${(volume / 1000).toFixed(1)}K`;
    }
    return volume.toLocaleString();
  };

  const formatDate = (date: string | null | undefined) => {
    if (!date) return 'N/A';
    return new Date(date).toLocaleDateString();
  };

  return (
    <div className="watchlist-stock-card">
      <div className="stock-header">
        <div className="stock-info">
          <h3 className="stock-ticker">{stock.ticker}</h3>
          <p className="stock-name">
            {stock.stock?.company_name_jp || stock.stock?.company_name_en || 'Unknown Company'}
          </p>
        </div>
        
        <div className="stock-actions">
          <button
            className="btn btn-sm btn-secondary"
            onClick={onEdit}
            title="Edit notes"
          >
            ✏️
          </button>
          <button
            className="btn btn-sm btn-danger"
            onClick={onRemove}
            title="Remove from watchlist"
          >
            🗑️
          </button>
        </div>
      </div>

      <div className="stock-price-info">
        <div className="current-price">
          <span className="price-label">Current Price:</span>
          <span className="price-value">{formatPrice(stock.current_price)}</span>
        </div>
        
        <div className={`price-change ${getChangeClass(stock.price_change)}`}>
          <span className="change-value">
            {formatChange(stock.price_change, stock.price_change_percent)}
          </span>
        </div>
      </div>

      <div className="stock-details">
        <div className="detail-row">
          <span className="detail-label">Volume:</span>
          <span className="detail-value">{formatVolume(stock.volume_today)}</span>
        </div>
        
        <div className="detail-row">
          <span className="detail-label">Last Updated:</span>
          <span className="detail-value">{formatDate(stock.last_updated)}</span>
        </div>
        
        {stock.stock?.sector_jp && (
          <div className="detail-row">
            <span className="detail-label">Sector:</span>
            <span className="detail-value">{stock.stock.sector_jp}</span>
          </div>
        )}
      </div>

      {stock.notes && (
        <div className="stock-notes">
          <span className="notes-label">Notes:</span>
          <p className="notes-content">{stock.notes}</p>
        </div>
      )}

      <div className="stock-card-actions">
        <button
          className="btn btn-primary btn-sm"
          onClick={() => onViewAnalysis(stock.ticker)}
        >
          View Analysis
        </button>
        
        <div className="added-date">
          Added: {formatDate(stock.created_at)}
        </div>
      </div>

      {/* Alert indicators */}
      {(stock.price_alert_triggered || stock.volume_alert_triggered) && (
        <div className="alert-indicators">
          {stock.price_alert_triggered && (
            <span className="alert-badge price-alert">Price Alert</span>
          )}
          {stock.volume_alert_triggered && (
            <span className="alert-badge volume-alert">Volume Alert</span>
          )}
        </div>
      )}
    </div>
  );
};

export default WatchlistStockCard;