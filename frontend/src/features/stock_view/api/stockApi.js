import { fetchJson } from '../../../shared/api/httpClient';

export async function getLatestStocks(symbols = []) {
  const params = symbols.length ? `?symbols=${encodeURIComponent(symbols.join(','))}` : '';
  return fetchJson(`/stocks/latest/${params}`);
}

export async function getStockHistory(symbol, params = {}) {
  const query = new URLSearchParams({ symbol, ...params });
  return fetchJson(`/stocks/history/?${query.toString()}`);
}
