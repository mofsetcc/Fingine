/**
 * Hot stocks section component showing gainers, losers, and most traded stocks.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { HotStock } from '../types';

interface HotStocksSectionProps {
  hotStocks: HotStock[];
  isLoading: boolean;
}

type HotStockCategory = 'gainer' | 'loser' | 'most_traded';

const HotStocksSection: React.FC<HotStocksSectionProps> = ({ 
  hotStocks, 
  isLoading 
}) => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<HotStockCategory>('gainer');

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'JPY',
      minimumFractionDigits: 0,
    }).format(price);
  };

  const formatVolume = (volume: number) => {
    return new Intl.NumberFormat('ja-JP', {
      notation: 'compact',
      compactDisplay: 'short'
    }).format(volume);
  };

  const formatChange = (change: number, changePercent: number) => {
    const isPositive = change >= 0;
    const colorClass = isPositive ? 'text-success-600' : 'text-danger-600';
    const sign = isPositive ? '+' : '';
    
    return (
      <span className={`font-medium ${colorClass}`}>
        {sign}{change.toFixed(2)} ({sign}{changePercent.toFixed(2)}%)
      </span>
    );
  };

  const getTabIcon = (category: HotStockCategory) => {
    switch (category) {
      case 'gainer':
        return '📈';
      case 'loser':
        return '📉';
      case 'most_traded':
        return '🔥';
      default:
        return '📊';
    }
  };

  const getTabLabel = (category: HotStockCategory) => {
    switch (category) {
      case 'gainer':
        return 'Top Gainers';
      case 'loser':
        return 'Top Losers';
      case 'most_traded':
        return 'Most Traded';
      default:
        return 'Stocks';
    }
  };

  const getStocksByCategory = (category: HotStockCategory) => {
    return hotStocks
      .filter(stock => stock.category === category)
      .slice(0, 10); // Show top 10
  };

  const handleStockClick = (ticker: string) => {
    navigate(`/stocks/${ticker}`);
  };

  const tabs: HotStockCategory[] = ['gainer', 'loser', 'most_traded'];

  if (isLoading) {
    return (
      <div className="space-y-4">
        {/* Tab skeleton */}
        <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex-1 h-10 bg-gray-200 rounded animate-pulse"></div>
          ))}
        </div>
        
        {/* Content skeleton */}
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg animate-pulse">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-gray-200 rounded"></div>
                <div className="space-y-1">
                  <div className="h-4 bg-gray-200 rounded w-16"></div>
                  <div className="h-3 bg-gray-200 rounded w-24"></div>
                </div>
              </div>
              <div className="text-right space-y-1">
                <div className="h-4 bg-gray-200 rounded w-20"></div>
                <div className="h-3 bg-gray-200 rounded w-16"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 flex items-center justify-center space-x-2 py-2 px-3 rounded-md text-sm font-medium transition-colors duration-200 ${
              activeTab === tab
                ? 'bg-white text-primary-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <span>{getTabIcon(tab)}</span>
            <span>{getTabLabel(tab)}</span>
          </button>
        ))}
      </div>

      {/* Stock List */}
      <div className="space-y-2">
        {getStocksByCategory(activeTab).length === 0 ? (
          <div className="text-center py-8">
            <div className="text-4xl mb-2">{getTabIcon(activeTab)}</div>
            <p className="text-gray-500">No {getTabLabel(activeTab).toLowerCase()} data available</p>
            <p className="text-sm text-gray-400 mt-1">Data will be updated during market hours</p>
          </div>
        ) : (
          getStocksByCategory(activeTab).map((stock, index) => (
            <div
              key={stock.ticker}
              onClick={() => handleStockClick(stock.ticker)}
              className="flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100 rounded-lg cursor-pointer transition-colors duration-200 group"
            >
              {/* Left side - Rank and Stock Info */}
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                    index < 3 
                      ? 'bg-primary-100 text-primary-600' 
                      : 'bg-gray-200 text-gray-600'
                  }`}>
                    {index + 1}
                  </div>
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-sm font-semibold text-primary-600 group-hover:text-primary-700">
                      {stock.ticker}
                    </span>
                    {index < 3 && (
                      <span className="text-xs">
                        {index === 0 ? '🥇' : index === 1 ? '🥈' : '🥉'}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-600 truncate max-w-48">
                    {stock.company_name}
                  </p>
                </div>
              </div>

              {/* Right side - Price and Change */}
              <div className="text-right">
                <div className="text-sm font-medium text-gray-900">
                  {formatPrice(stock.price)}
                </div>
                <div className="text-xs">
                  {formatChange(stock.change, stock.change_percent)}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Vol: {formatVolume(stock.volume)}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer with update time */}
      {getStocksByCategory(activeTab).length > 0 && (
        <div className="text-center pt-4 border-t border-gray-200">
          <p className="text-xs text-gray-500">
            Data updates every 5 minutes during market hours (9:00-15:00 JST)
          </p>
        </div>
      )}
    </div>
  );
};

export default HotStocksSection;