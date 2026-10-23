import React from 'react';

function StatusBanner({ connected, lastUpdate, error }) {
  return (
    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div className="flex items-center gap-3">
        <span className={`h-3 w-3 rounded-full ${connected ? 'bg-bullish animate-pulse' : 'bg-bearish'}`} />
        <span className="text-sm text-gray-300">{connected ? 'Live stream' : 'Polling fallback'}</span>
      </div>
      <div className="text-sm text-gray-400">
        {lastUpdate ? `Last update: ${lastUpdate.toLocaleTimeString()}` : 'Waiting for data'}
      </div>
      {error && <div className="text-sm text-red-400">{error}</div>}
    </div>
  );
}

export default StatusBanner;
