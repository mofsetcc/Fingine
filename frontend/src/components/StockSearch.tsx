/**
 * Stock search component with autocomplete functionality.
 */

import React, { useEffect, useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { RootState } from '../store';
import {
    clearSearchResults,
    setLoading,
    setSearchResults
} from '../store/slices/stocksSlice';
import { StockSearchResult } from '../types';

const StockSearch: React.FC = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { searchResults, isLoading } = useSelector((state: RootState) => state.stocks);
  
  const [query, setQuery] = useState('');
  const [showResults, setShowResults] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const searchRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<NodeJS.Timeout>();

  // Handle search with debouncing
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    if (query.trim().length >= 2) {
      debounceRef.current = setTimeout(() => {
        performSearch(query.trim());
      }, 300);
    } else {
      dispatch(clearSearchResults());
      setShowResults(false);
    }

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [query]);

  // Handle clicks outside to close results
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowResults(false);
        setSelectedIndex(-1);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const performSearch = async (searchQuery: string) => {
    try {
      dispatch(setLoading(true));
      
      const response = await fetch(
        `/api/v1/stocks/search?query=${encodeURIComponent(searchQuery)}&limit=10`
      );
      
      if (response.ok) {
        const data = await response.json();
        dispatch(setSearchResults(data.results || []));
        setShowResults(true);
        setSelectedIndex(-1);
      } else {
        console.error('Search failed:', response.statusText);
        dispatch(clearSearchResults());
      }
    } catch (error) {
      console.error('Search error:', error);
      dispatch(clearSearchResults());
    } finally {
      dispatch(setLoading(false));
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showResults || searchResults.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < searchResults.length - 1 ? prev + 1 : 0
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev > 0 ? prev - 1 : searchResults.length - 1
        );
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < searchResults.length) {
          selectStock(searchResults[selectedIndex]);
        }
        break;
      case 'Escape':
        setShowResults(false);
        setSelectedIndex(-1);
        inputRef.current?.blur();
        break;
    }
  };

  const selectStock = (stock: StockSearchResult) => {
    setQuery(`${stock.ticker} - ${stock.company_name_jp}`);
    setShowResults(false);
    setSelectedIndex(-1);
    navigate(`/stocks/${stock.ticker}`);
  };

  const formatPrice = (price?: number) => {
    if (price === undefined) return 'N/A';
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'JPY',
      minimumFractionDigits: 0,
    }).format(price);
  };

  const formatPriceChange = (change?: number, changePercent?: number) => {
    if (change === undefined || changePercent === undefined) return null;
    
    const isPositive = change >= 0;
    const colorClass = isPositive ? 'text-success-600' : 'text-danger-600';
    const sign = isPositive ? '+' : '';
    
    return (
      <span className={`text-sm ${colorClass}`}>
        {sign}{change.toFixed(2)} ({sign}{changePercent.toFixed(2)}%)
      </span>
    );
  };

  return (
    <div ref={searchRef} className="relative">
      {/* Search Input */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <svg 
            className="h-5 w-5 text-gray-400" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" 
            />
          </svg>
        </div>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => query.length >= 2 && setShowResults(true)}
          placeholder="Search stocks by ticker or company name (e.g., 7203, Toyota)"
          className="input-field pl-10 pr-4 py-3 text-lg"
          autoComplete="off"
        />
        {isLoading && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
            <div className="loading-spinner h-5 w-5"></div>
          </div>
        )}
      </div>

      {/* Search Results Dropdown */}
      {showResults && searchResults.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-96 overflow-y-auto">
          {searchResults.map((stock, index) => (
            <div
              key={stock.ticker}
              onClick={() => selectStock(stock)}
              className={`px-4 py-3 cursor-pointer border-b border-gray-100 last:border-b-0 hover:bg-gray-50 ${
                index === selectedIndex ? 'bg-primary-50' : ''
              }`}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-sm font-semibold text-primary-600">
                      {stock.ticker}
                    </span>
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                      Match: {(stock.match_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="mt-1">
                    <p className="text-sm font-medium text-gray-900">
                      {stock.company_name_jp}
                    </p>
                    {stock.company_name_en && (
                      <p className="text-xs text-gray-500">
                        {stock.company_name_en}
                      </p>
                    )}
                  </div>
                  {stock.sector_jp && (
                    <p className="text-xs text-gray-500 mt-1">
                      {stock.sector_jp}
                      {stock.industry_jp && ` • ${stock.industry_jp}`}
                    </p>
                  )}
                </div>
                <div className="text-right ml-4">
                  {stock.current_price && (
                    <div className="text-sm font-medium text-gray-900">
                      {formatPrice(stock.current_price)}
                    </div>
                  )}
                  {formatPriceChange(stock.price_change, stock.price_change_percent)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* No Results Message */}
      {showResults && searchResults.length === 0 && !isLoading && query.length >= 2 && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-4">
          <div className="text-center text-gray-500">
            <svg className="mx-auto h-12 w-12 text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6-4h6m2 5.291A7.962 7.962 0 0112 15c-2.34 0-4.47-.881-6.08-2.33" />
            </svg>
            <p className="text-sm">No stocks found for "{query}"</p>
            <p className="text-xs text-gray-400 mt-1">
              Try searching with a ticker symbol (e.g., 7203) or company name
            </p>
          </div>
        </div>
      )}

      {/* Search Tips */}
      {!showResults && query.length === 0 && (
        <div className="mt-2 text-xs text-gray-500">
          <p>💡 Search tips:</p>
          <ul className="ml-4 mt-1 space-y-1">
            <li>• Use 4-digit ticker symbols (e.g., 7203 for Toyota)</li>
            <li>• Search by company name in Japanese or English</li>
            <li>• Use keyboard arrows to navigate results</li>
          </ul>
        </div>
      )}
    </div>
  );
};

export default StockSearch;