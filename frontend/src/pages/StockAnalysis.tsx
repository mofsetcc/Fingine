/**
 * Individual stock analysis page component.
 */

import React from 'react';
import { useParams } from 'react-router-dom';

const StockAnalysis: React.FC = () => {
  const { ticker } = useParams<{ ticker: string }>();

  return (
    <div className="space-y-6">
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Stock Analysis: {ticker}
        </h2>
        <p className="text-gray-600">
          AI-powered analysis components will be implemented in later tasks.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            AI Analysis
          </h3>
          <p className="text-gray-600">Short, mid, and long-term insights</p>
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Price Chart
          </h3>
          <p className="text-gray-600">Interactive TradingView charts</p>
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Financial Data
          </h3>
          <p className="text-gray-600">Income statement, balance sheet</p>
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            News & Sentiment
          </h3>
          <p className="text-gray-600">Related news with sentiment analysis</p>
        </div>
      </div>
    </div>
  );
};

export default StockAnalysis;