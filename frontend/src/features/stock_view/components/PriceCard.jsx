import React from 'react';
import { Link } from 'react-router-dom';

function PriceCard({ row }) {
  const close = Number(row.close ?? 0);
  const open = Number(row.open ?? close);
  const change = close - open;
  const changeClass = change >= 0 ? 'text-bullish' : 'text-bearish';

  return (
    <Link to={`/stocks/${row.symbol}`} className="block">
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 hover:border-bullish/50">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-400">{row.symbol}</p>
            <p className="text-xl font-semibold text-white">{close.toFixed(2)}</p>
          </div>
          <div className={`text-right ${changeClass}`}>
            <p className="text-sm">{change >= 0 ? '+' : ''}{change.toFixed(2)}</p>
          </div>
        </div>
        <div className="mt-3 text-xs text-gray-500">Volume: {row.volume}</div>
      </div>
    </Link>
  );
}

export default PriceCard;
