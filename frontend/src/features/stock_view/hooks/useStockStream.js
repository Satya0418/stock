import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { getLatestStocks } from '../api/stockApi';
import { getAccessToken } from '../../../shared/auth/tokenStore';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || '';
const WS_BASE_URL = import.meta.env.VITE_WS_URL || '';

function normalizeBaseUrl(value) {
  if (!value) {
    return '';
  }
  return value.replace(/\/+$/, '');
}

function buildWebSocketBaseUrl() {
  const wsBase = normalizeBaseUrl(WS_BASE_URL);
  if (wsBase) {
    return wsBase;
  }
  const apiBase = normalizeBaseUrl(API_BASE_URL);
  if (apiBase) {
    return apiBase.replace(/^http/i, 'ws');
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}`;
}

function getWebSocketUrl() {
  const token = getAccessToken();
  const baseUrl = `${buildWebSocketBaseUrl()}/stocks/stream/`;
  if (!token) {
    return baseUrl;
  }
  return `${baseUrl}?token=${encodeURIComponent(token)}`;
}

function normalizeRows(rows) {
  if (!Array.isArray(rows)) {
    return [];
  }
  return rows.map((row) => ({
    ...row,
    symbol: row.symbol?.toUpperCase(),
  }));
}

export default function useStockStream({ pollInterval = 60000 } = {}) {
  const [data, setData] = useState([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState('');
  const [lastUpdate, setLastUpdate] = useState(null);
  const wsRef = useRef(null);
  const pollRef = useRef(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback(async () => {
    stopPolling();
    try {
      const latest = await getLatestStocks();
      setData(normalizeRows(latest));
      setLastUpdate(new Date());
      setError('');
    } catch (err) {
      setError(err.message || 'Polling failed');
    }
    pollRef.current = setInterval(async () => {
      try {
        const latest = await getLatestStocks();
        setData(normalizeRows(latest));
        setLastUpdate(new Date());
        setError('');
      } catch (err) {
        setError(err.message || 'Polling failed');
      }
    }, pollInterval);
  }, [pollInterval, stopPolling]);

  const connectWebSocket = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(getWebSocketUrl());

    ws.onopen = () => {
      setConnected(true);
      setError('');
      stopPolling();
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'stock_stream') {
          setData(normalizeRows(payload.data));
          setLastUpdate(new Date(payload.timestamp || Date.now()));
          setError('');
        }
      } catch (err) {
        setError('Invalid stream data');
      }
    };

    ws.onclose = () => {
      setConnected(false);
      startPolling();
    };

    ws.onerror = () => {
      setConnected(false);
      setError('WebSocket error');
      startPolling();
    };

    wsRef.current = ws;
  }, [startPolling, stopPolling]);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      stopPolling();
    };
  }, [connectWebSocket, stopPolling]);

  const dataBySymbol = useMemo(() => {
    return data.reduce((acc, row) => {
      if (row.symbol) {
        acc[row.symbol] = row;
      }
      return acc;
    }, {});
  }, [data]);

  return { data, dataBySymbol, connected, error, lastUpdate, reconnect: connectWebSocket };
}
