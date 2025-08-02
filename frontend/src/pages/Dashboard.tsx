/**
 * Main dashboard page component with market indices, stock search, and hot stocks.
 */

import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import HotStocksSection from '../components/HotStocksSection';
import MarketIndicesDisplay from '../components/MarketIndicesDisplay';
import StockSearch from '../components/StockSearch';
import { RootState } from '../store';
import {
    setError,
    setHotStocks,
    setLoading,
    setMarketIndices
} from '../store/slices/stocksSlice';
import { HotStock, MarketIndex } from '../types';

const Dashboard: React.FC = () => {
  const dispatch = useDispatch();
  const { marketIndices, hotStocks, isLoading, error } = useSelector(
    (state: RootState) => state.stocks
  );

  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null);

  // Fetch market data on component mount
  useEffect(() => {
    fetchMarketData();
    
    // Set up auto-refresh every 5 minutes during market hours
    const interval = setInterval(() => {
      const now = new Date();
      const hour = now.getHours();
      // Refresh during JST market hours (9:00-15:00, which is 0:00-6:00 UTC)
      if (hour >= 0 && hour <= 6) {
        fetchMarketData();
      }
    }, 5 * 60 * 1000); // 5 minutes

    setRefreshInterval(interval);

    return () => {
      if (interval) clearInterval(interval);
    };
  }, []);

  const fetchMarketData = async () => {
    try {
      dispatch(setLoading(true));
      dispatch(setError(null));

      // Fetch market indices
      const indicesResponse = await fetch('/api/v1/stocks/market/indices');
      if (indicesResponse.ok) {
        const indices: MarketIndex[] = await indicesResponse.json();
        dispatch(setMarketIndices(indices));
      }

      // Fetch hot stocks
      const hotStocksResponse = await fetch('/api/v1/stocks/market/hot-stocks');
      if (hotStocksResponse.ok) {
        const hotStocksData = await hotStocksResponse.json();
        const allHotStocks: HotStock[] = [
          ...hotStocksData.gainers.map((stock: any) => ({ ...stock, category: 'gainer' as const })),
          ...hotStocksData.losers.map((stock: any) => ({ ...stock, category: 'loser' as const })),
          ...hotStocksData.most_traded.map((stock: any) => ({ ...stock, category: 'most_traded' as const }))
        ];
        dispatch(setHotStocks(allHotStocks));
      }
    } catch (err) {
      dispatch(setError('Failed to fetch market data'));
      console.error('Error fetching market data:', err);
    } finally {
      dispatch(setLoading(false));
    }
  };

  const handleRefresh = () => {
    fetchMarketData();
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header with refresh button */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Market Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Real-time Japanese stock market insights powered by AI
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isLoading}
          className="btn-secondary flex items-center space-x-2"
        >
          <svg 
            className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" 
            />
          </svg>
          <span>Refresh</span>
        </button>
      </div>

      {/* Error display */}
      {error && (
        <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-lg">
          <div className="flex items-center">
            <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            {error}
          </div>
        </div>
      )}

      {/* Stock Search */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Stock Search</h2>
        <StockSearch />
      </div>

      {/* Market Indices */}
      <div className="card">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Market Indices</h2>
          <span className="text-sm text-gray-500">
            Last updated: {new Date().toLocaleTimeString('ja-JP')}
          </span>
        </div>
        <MarketIndicesDisplay indices={marketIndices} isLoading={isLoading} />
      </div>

      {/* Watchlist Section */}
      <div className="card">
        <Watchlist />
      </div>

      {/* Hot Stocks Section */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Hot Stocks Today</h2>
        <HotStocksSection hotStocks={hotStocks} isLoading={isLoading} />
      </div>
    </div>
  );
};

export default Dashboard;