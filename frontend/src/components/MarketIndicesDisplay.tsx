/**
 * Market indices display component showing Nikkei 225, TOPIX, etc.
 */

import React from 'react';
import { MarketIndex } from '../types';

interface MarketIndicesDisplayProps {
  indices: MarketIndex[];
  isLoading: boolean;
}

const MarketIndicesDisplay: React.FC<MarketIndicesDisplayProps> = ({ 
  indices, 
  isLoading 
}) => {
  const formatValue = (value: number) => {
    return new Intl.NumberFormat('ja-JP', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatChange = (change: number, changePercent: number) => {
    const isPositive = change >= 0;
    const colorClass = isPositive ? 'text-success-600' : 'text-danger-600';
    const bgColorClass = isPositive ? 'bg-success-50' : 'bg-danger-50';
    const sign = isPositive ? '+' : '';
    
    return (
      <div className={`inline-flex items-center px-2 py-1 rounded-full text-sm font-medium ${colorClass} ${bgColorClass}`}>
        <svg 
          className={`w-4 h-4 mr-1 ${isPositive ? 'rotate-0' : 'rotate-180'}`} 
          fill="currentColor" 
          viewBox="0 0 20 20"
        >
          <path 
            fillRule="evenodd" 
            d="M5.293 7.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L10 4.414 6.707 7.707a1 1 0 01-1.414 0z" 
            clipRule="evenodd" 
          />
        </svg>
        {sign}{formatValue(Math.abs(change))} ({sign}{changePercent.toFixed(2)}%)
      </div>
    );
  };

  const getIndexIcon = (symbol: string) => {
    switch (symbol.toUpperCase()) {
      case 'N225':
      case 'NIKKEI':
        return '📈';
      case 'TOPIX':
        return '📊';
      case 'MOTHERS':
        return '🚀';
      case 'JASDAQ':
        return '💼';
      default:
        return '📋';
    }
  };

  const getIndexDescription = (name: string, symbol: string) => {
    switch (symbol.toUpperCase()) {
      case 'N225':
      case 'NIKKEI':
        return 'Japan\'s premier stock index of 225 companies';
      case 'TOPIX':
        return 'Tokyo Stock Price Index of all TSE companies';
      case 'MOTHERS':
        return 'Market for emerging and growth companies';
      case 'JASDAQ':
        return 'Over-the-counter market for smaller companies';
      default:
        return 'Japanese market index';
    }
  };

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="animate-pulse">
            <div className="bg-gray-100 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="h-6 bg-gray-200 rounded w-20"></div>
                <div className="h-8 bg-gray-200 rounded w-16"></div>
              </div>
              <div className="h-8 bg-gray-200 rounded w-24 mb-2"></div>
              <div className="h-4 bg-gray-200 rounded w-32"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (indices.length === 0) {
    return (
      <div className="text-center py-8">
        <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <p className="text-gray-500">Market indices data unavailable</p>
        <p className="text-sm text-gray-400 mt-1">Please try refreshing the page</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {indices.map((index) => (
        <div 
          key={index.symbol} 
          className="bg-gradient-to-br from-white to-gray-50 border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow duration-200"
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <span className="text-2xl">{getIndexIcon(index.symbol)}</span>
              <div>
                <h3 className="font-semibold text-gray-900">{index.name}</h3>
                <p className="text-xs text-gray-500 font-mono">{index.symbol}</p>
              </div>
            </div>
            {index.volume && (
              <div className="text-right">
                <p className="text-xs text-gray-500">Volume</p>
                <p className="text-sm font-medium">
                  {new Intl.NumberFormat('ja-JP', { 
                    notation: 'compact',
                    compactDisplay: 'short'
                  }).format(index.volume)}
                </p>
              </div>
            )}
          </div>

          {/* Value */}
          <div className="mb-3">
            <p className="text-2xl font-bold text-gray-900">
              {formatValue(index.value)}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {getIndexDescription(index.name, index.symbol)}
            </p>
          </div>

          {/* Change */}
          <div className="flex items-center justify-between">
            {formatChange(index.change, index.change_percent)}
            <div className="text-right">
              <p className="text-xs text-gray-500">
                Updated: {new Date(index.updated_at).toLocaleTimeString('ja-JP', {
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default MarketIndicesDisplay;