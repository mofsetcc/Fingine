/**
 * Stock Header Component
 * Displays key stock information at the top of the analysis page
 */

import React from 'react';
import { StockDetail } from '../types/stock';

interface StockHeaderProps {
  stock: StockDetail;
  onAddToWatchlist: () => void;
}

const StockHeader: React.FC<StockHeaderProps> = ({ stock, onAddToWatchlist }) => {
  const formatPrice = (price: number | undefined) => {
    if (!price) return 'N/A';
    return `¥${price.toLocaleString()}`;
  };

  const formatChange = (change: number | undefined, changePercent: number | undefined) => {
    if (change === undefined || changePercent === undefined) return 'N/A';
    const sign = change >= 0 ? '+' : '';
    return `${sign}¥${change.toFixed(2)} (${sign}${changePercent.toFixed(2)}%)`;
  };

  const getChangeColor = (change: number | undefined) => {
    if (change === undefined) return 'text-gray-600';
    return change >= 0 ? 'text-success-600' : 'text-danger-600';
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-4">
          {/* Company Logo */}
          {stock.logo_url && (
            <img
              src={stock.logo_url}
              alt={`${stock.company_name_jp} logo`}
              className="w-16 h-16 rounded-lg object-contain bg-gray-50 p-2"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          )}
          
          {/* Company Info */}
          <div>
            <div className="flex items-center space-x-3 mb-2">
              <h1 className="text-3xl font-bold text-gray-900">{stock.ticker}</h1>
              <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full">
                TSE
              </span>
            </div>
            <h2 className="text-xl text-gray-700 mb-1">{stock.company_name_jp}</h2>
            {stock.company_name_en && (
              <p className="text-gray-600">{stock.company_name_en}</p>
            )}
            {stock.sector_jp && (
              <div className="flex items-center space-x-2 mt-2">
                <span className="text-sm text-gray-500">Sector:</span>
                <span className="text-sm font-medium text-gray-700">{stock.sector_jp}</span>
                {stock.industry_jp && (
                  <>
                    <span className="text-gray-400">•</span>
                    <span className="text-sm text-gray-600">{stock.industry_jp}</span>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-3">
          <button
            onClick={onAddToWatchlist}
            className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
            </svg>
            <span>Add to Watchlist</span>
          </button>
          
          <button className="flex items-center space-x-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z" />
            </svg>
            <span>Share</span>
          </button>
        </div>
      </div>

      {/* Price Information */}
      <div className="mt-6 pt-6 border-t border-gray-200">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-6">
          <div>
            <div className="text-sm text-gray-500 mb-1">Current Price</div>
            <div className="text-2xl font-bold text-gray-900">
              {formatPrice(stock.current_price)}
            </div>
          </div>

          <div>
            <div className="text-sm text-gray-500 mb-1">Change</div>
            <div className={`text-lg font-semibold ${getChangeColor(stock.price_change)}`}>
              {formatChange(stock.price_change, stock.price_change_percent)}
            </div>
          </div>

          <div>
            <div className="text-sm text-gray-500 mb-1">Volume</div>
            <div className="text-lg font-semibold text-gray-900">
              {stock.volume_today?.toLocaleString() || 'N/A'}
            </div>
          </div>

          <div>
            <div className="text-sm text-gray-500 mb-1">Market Cap</div>
            <div className="text-lg font-semibold text-gray-900">
              {stock.market_cap ? `¥${(stock.market_cap / 1000000000).toFixed(1)}B` : 'N/A'}
            </div>
          </div>

          <div>
            <div className="text-sm text-gray-500 mb-1">P/E Ratio</div>
            <div className="text-lg font-semibold text-gray-900">
              {stock.pe_ratio?.toFixed(2) || 'N/A'}
            </div>
          </div>

          <div>
            <div className="text-sm text-gray-500 mb-1">Dividend Yield</div>
            <div className="text-lg font-semibold text-gray-900">
              {stock.dividend_yield ? `${(stock.dividend_yield * 100).toFixed(2)}%` : 'N/A'}
            </div>
          </div>
        </div>

        {/* Additional Metrics */}
        <div className="mt-4 pt-4 border-t border-gray-100">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">52W High:</span>
              <span className="font-medium text-gray-900">
                {formatPrice(stock.week_52_high)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">52W Low:</span>
              <span className="font-medium text-gray-900">
                {formatPrice(stock.week_52_low)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Avg Volume:</span>
              <span className="font-medium text-gray-900">
                {stock.avg_volume_30d?.toLocaleString() || 'N/A'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Beta:</span>
              <span className="font-medium text-gray-900">
                {stock.beta?.toFixed(2) || 'N/A'}
              </span>
            </div>
          </div>
        </div>

        {/* Last Updated */}
        {stock.last_updated && (
          <div className="mt-4 text-xs text-gray-500 text-right">
            Last updated: {new Date(stock.last_updated).toLocaleString('ja-JP', {
              timeZone: 'Asia/Tokyo',
              year: 'numeric',
              month: '2-digit',
              day: '2-digit',
              hour: '2-digit',
              minute: '2-digit'
            })} JST
          </div>
        )}
      </div>
    </div>
  );
};

export default StockHeader;