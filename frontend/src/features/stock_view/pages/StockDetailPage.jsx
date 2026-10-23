import React, { useEffect, useMemo, useState } from 'react';
import { useParams, Link } from 'react-router-dom';

import { getStockHistory } from '../api/stockApi';
import PriceHistoryChart from '../../charts/components/PriceHistoryChart.jsx';
import RetryState from '../../../shared/components/RetryState.jsx';

function StockDetailPage() {
  const { symbol } = useParams();
  const [history, setHistory] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const loadHistory = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getStockHistory(symbol.toUpperCase(), { limit: 500 });
      setHistory(data);
    } catch (err) {
      setError(err.message || 'Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, [symbol]);

  const latest = useMemo(() => history[0], [history]);

  return (
    <div className="min-h-screen bg-gray-900 px-6 py-8">
      <div className="max-w-6xl mx-auto">
        <Link to="/" className="text-sm text-gray-400 hover:text-white">Back to dashboard</Link>

        <div className="mt-4 flex flex-col md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-3xl font-semibold text-white">{symbol}</h1>
            <p className="text-gray-400">Historical price view</p>
          </div>
          {latest && (
            <div className="mt-4 md:mt-0 text-right">
              <div className="text-2xl text-white">{Number(latest.close).toFixed(2)}</div>
              <div className="text-sm text-gray-400">{new Date(latest.timestamp).toLocaleString()}</div>
            </div>
          )}
        </div>

        <div className="mt-8 bg-gray-800 border border-gray-700 rounded-2xl p-6">
          {loading && <p className="text-gray-400">Loading history...</p>}
          {!loading && error && <RetryState message={error} onRetry={loadHistory} />}
          {!loading && !error && <PriceHistoryChart rows={history} />}
        </div>
      </div>
    </div>
  );
}

export default StockDetailPage;
