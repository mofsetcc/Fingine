/**
 * Main dashboard page component.
 */

import React from 'react';

const Dashboard: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Market Overview
        </h2>
        <p className="text-gray-600">
          Dashboard components will be implemented in later tasks.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Market Indices
          </h3>
          <p className="text-gray-600">Nikkei 225, TOPIX data</p>
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Hot Stocks Today
          </h3>
          <p className="text-gray-600">Gainers, losers, most traded</p>
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Your Watchlist
          </h3>
          <p className="text-gray-600">Personalized stock tracking</p>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;