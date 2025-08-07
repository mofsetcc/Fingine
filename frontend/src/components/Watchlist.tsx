import React, { useEffect, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../store';
import {
    addStockToWatchlist,
    clearError,
    fetchWatchlist,
    fetchRealTimePrices,
    removeStockFromWatchlist,
    updateWatchlistStock
} from '../store/slices/watchlistSlice';
import { WatchlistStockWithPrice } from '../types/watchlist';
import AddStockModal from './AddStockModal';
import LoadingSpinner from './LoadingSpinner';
import './Watchlist.css';
import WatchlistStockCard from './WatchlistStockCard';

const Watchlist: React.FC = () => {
  const dispatch = useAppDispatch();
  const { stocks, isLoading, error, lastUpdated } = useAppSelector((state) => state.watchlist);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingStock, setEditingStock] = useState<WatchlistStockWithPrice | null>(null);

  useEffect(() => {
    dispatch(fetchWatchlist());
  }, [dispatch]);

  // Set up real-time price updates
  useEffect(() => {
    if (stocks.length === 0) return;

    const updatePrices = () => {
      const tickers = stocks.map(stock => stock.ticker);
      dispatch(fetchRealTimePrices(tickers));
    };

    // Update prices immediately, then every 30 seconds
    updatePrices();
    const priceUpdateInterval = setInterval(updatePrices, 30000);
    
    return () => clearInterval(priceUpdateInterval);
  }, [dispatch, stocks.map(s => s.ticker).join(',')]);

  const handleAddStock = async (ticker: string, notes?: string) => {
    try {
      await dispatch(addStockToWatchlist({ ticker, notes })).unwrap();
      setShowAddModal(false);
    } catch (error) {
      // Error is handled by the slice
    }
  };

  const handleRemoveStock = async (ticker: string) => {
    if (window.confirm(`Are you sure you want to remove ${ticker} from your watchlist?`)) {
      try {
        await dispatch(removeStockFromWatchlist(ticker)).unwrap();
      } catch (error) {
        // Error is handled by the slice
      }
    }
  };

  const handleUpdateStock = async (ticker: string, notes: string) => {
    try {
      await dispatch(updateWatchlistStock({ ticker, data: { notes } })).unwrap();
      setEditingStock(null);
    } catch (error) {
      // Error is handled by the slice
    }
  };

  const handleRefresh = () => {
    dispatch(fetchWatchlist());
  };

  const calculateTotalValue = () => {
    return stocks.reduce((total, stock) => {
      return total + (stock.current_price || 0);
    }, 0);
  };

  const calculateTotalChange = () => {
    const totalChange = stocks.reduce((total, stock) => {
      return total + (stock.price_change || 0);
    }, 0);
    
    const totalValue = calculateTotalValue();
    const previousValue = totalValue - totalChange;
    const changePercent = previousValue > 0 ? (totalChange / previousValue) * 100 : 0;
    
    return { totalChange, changePercent };
  };

  const { totalChange, changePercent } = calculateTotalChange();

  if (isLoading && stocks.length === 0) {
    return <LoadingSpinner />;
  }

  return (
    <div className="watchlist-container">
      <div className="watchlist-header">
        <div className="watchlist-title">
          <h2>My Watchlist</h2>
          <span className="stock-count">({stocks.length} stocks)</span>
        </div>
        
        <div className="watchlist-summary">
          <div className="summary-item">
            <span className="label">Total Value:</span>
            <span className="value">¥{calculateTotalValue().toLocaleString()}</span>
          </div>
          <div className="summary-item">
            <span className="label">Total Change:</span>
            <span className={`value ${totalChange >= 0 ? 'positive' : 'negative'}`}>
              {totalChange >= 0 ? '+' : ''}¥{totalChange.toFixed(2)} ({changePercent.toFixed(2)}%)
            </span>
          </div>
        </div>

        <div className="watchlist-actions">
          <button
            className="btn btn-primary"
            onClick={() => setShowAddModal(true)}
          >
            Add Stock
          </button>
          <button
            className="btn btn-secondary"
            onClick={handleRefresh}
            disabled={isLoading}
          >
            {isLoading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && (
        <div className="error-message">
          <span>{error}</span>
          <button onClick={() => dispatch(clearError())}>×</button>
        </div>
      )}

      {lastUpdated && (
        <div className="last-updated">
          Last updated: {new Date(lastUpdated).toLocaleString()}
        </div>
      )}

      <div className="watchlist-content">
        {stocks.length === 0 ? (
          <div className="empty-watchlist">
            <div className="empty-message">
              <h3>Your watchlist is empty</h3>
              <p>Add stocks to track their performance and get real-time updates.</p>
              <button
                className="btn btn-primary"
                onClick={() => setShowAddModal(true)}
              >
                Add Your First Stock
              </button>
            </div>
          </div>
        ) : (
          <div className="watchlist-grid">
            {stocks.map((stock) => (
              <WatchlistStockCard
                key={stock.ticker}
                stock={stock}
                onRemove={() => handleRemoveStock(stock.ticker)}
                onEdit={() => setEditingStock(stock)}
                onViewAnalysis={(ticker) => {
                  // Navigate to stock analysis page
                  window.location.href = `/stocks/${ticker}`;
                }}
              />
            ))}
          </div>
        )}
      </div>

      {showAddModal && (
        <AddStockModal
          onAdd={handleAddStock}
          onClose={() => setShowAddModal(false)}
        />
      )}

      {editingStock && (
        <EditStockModal
          stock={editingStock}
          onUpdate={(notes) => handleUpdateStock(editingStock.ticker, notes)}
          onClose={() => setEditingStock(null)}
        />
      )}
    </div>
  );
};

// Edit Stock Modal Component
interface EditStockModalProps {
  stock: WatchlistStockWithPrice;
  onUpdate: (notes: string) => void;
  onClose: () => void;
}

const EditStockModal: React.FC<EditStockModalProps> = ({ stock, onUpdate, onClose }) => {
  const [notes, setNotes] = useState(stock.notes || '');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onUpdate(notes);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Edit {stock.ticker}</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="notes">Notes:</label>
            <textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add your notes about this stock..."
              rows={4}
              maxLength={1000}
            />
          </div>
          
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              Update
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Watchlist;