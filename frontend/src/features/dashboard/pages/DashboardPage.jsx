import React from 'react';

import useStockStream from '../../stock_view/hooks/useStockStream.js';
import PriceCard from '../../stock_view/components/PriceCard.jsx';
import StatusBanner from '../../stock_view/components/StatusBanner.jsx';
import RetryState from '../../../shared/components/RetryState.jsx';
import LoadingScreen from '../../../shared/components/LoadingScreen.jsx';

function DashboardPage() {
  const { data, connected, error, lastUpdate, reconnect } = useStockStream({
    pollInterval: 60000,
  });

  if (data.length === 0 && !error) {
    return <LoadingScreen message="Connecting to live data..." />;
  }

  return (
    <div className="min-h-screen bg-gray-900 px-6 py-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold text-white">Live Stock Dashboard</h1>
            <p className="text-gray-400">NSE/BSE live data with resilient streaming.</p>
          </div>
        </div>

        <div className="mt-6">
          <StatusBanner connected={connected} lastUpdate={lastUpdate} error={error} />
        </div>

        {error && data.length === 0 ? (
          <div className="mt-8">
            <RetryState message={error} onRetry={reconnect} />
          </div>
        ) : (
          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-fade-in">
            {data.map((row) => (
              <PriceCard key={row.symbol} row={row} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default DashboardPage;
