import React, { useEffect, useState } from 'react';
import { useAppSelector } from '../store';

interface AddStockModalProps {
  onAdd: (ticker: string, notes?: string) => void;
  onClose: () => void;
}

const AddStockModal: React.FC<AddStockModalProps> = ({ onAdd, onClose }) => {
  const [ticker, setTicker] = useState('');
  const [notes, setNotes] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState('');

  const { isLoading } = useAppSelector((state) => state.watchlist);

  // Search for stocks as user types
  useEffect(() => {
    const searchStocks = async () => {
      if (ticker.length < 2) {
        setSearchResults([]);
        return;
      }

      setIsSearching(true);
      setSearchError('');

      try {
        const response = await fetch(`/api/v1/stocks/search?q=${encodeURIComponent(ticker)}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
        });

        if (!response.ok) {
          throw new Error('Failed to search stocks');
        }

        const results = await response.json();
        setSearchResults(results.slice(0, 10)); // Limit to 10 results
      } catch (error) {
        setSearchError('Failed to search stocks');
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    };

    const debounceTimer = setTimeout(searchStocks, 300);
    return () => clearTimeout(debounceTimer);
  }, [ticker]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!ticker.trim()) {
      return;
    }

    onAdd(ticker.trim().toUpperCase(), notes.trim() || undefined);
  };

  const handleSelectStock = (selectedStock: any) => {
    setTicker(selectedStock.ticker);
    setSearchResults([]);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content add-stock-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Add Stock to Watchlist</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="ticker">Stock Ticker or Company Name:</label>
            <div className="search-input-container">
              <input
                id="ticker"
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                placeholder="e.g., 7203 or Toyota"
                required
                autoComplete="off"
              />
              
              {isSearching && (
                <div className="search-loading">Searching...</div>
              )}
              
              {searchResults.length > 0 && (
                <div className="search-results">
                  {searchResults.map((stock) => (
                    <div
                      key={stock.ticker}
                      className="search-result-item"
                      onClick={() => handleSelectStock(stock)}
                    >
                      <div className="result-ticker">{stock.ticker}</div>
                      <div className="result-name">
                        {stock.company_name_jp || stock.company_name_en}
                      </div>
                      {stock.sector_jp && (
                        <div className="result-sector">{stock.sector_jp}</div>
                      )}
                    </div>
                  ))}
                </div>
              )}
              
              {searchError && (
                <div className="search-error">{searchError}</div>
              )}
            </div>
          </div>
          
          <div className="form-group">
            <label htmlFor="notes">Notes (optional):</label>
            <textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add your notes about this stock..."
              rows={3}
              maxLength={1000}
            />
            <div className="character-count">
              {notes.length}/1000 characters
            </div>
          </div>
          
          <div className="modal-actions">
            <button 
              type="button" 
              className="btn btn-secondary" 
              onClick={onClose}
              disabled={isLoading}
            >
              Cancel
            </button>
            <button 
              type="submit" 
              className="btn btn-primary"
              disabled={isLoading || !ticker.trim()}
            >
              {isLoading ? 'Adding...' : 'Add to Watchlist'}
            </button>
          </div>
        </form>
        
        <div className="modal-help">
          <h4>Tips:</h4>
          <ul>
            <li>Enter a Japanese stock ticker (e.g., 7203 for Toyota)</li>
            <li>Or search by company name in Japanese or English</li>
            <li>Click on search results to select a stock</li>
            <li>Add notes to remember why you're watching this stock</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default AddStockModal;