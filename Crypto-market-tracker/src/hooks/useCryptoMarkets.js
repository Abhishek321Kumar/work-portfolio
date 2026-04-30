import { useCallback, useEffect, useState } from 'react';

const COINGECKO_MARKETS_URL =
  'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1&sparkline=false&price_change_percentage=24h';

export function useCryptoMarkets() {
  const [coins, setCoins] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [updatedAt, setUpdatedAt] = useState(null);

  const fetchMarkets = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch(COINGECKO_MARKETS_URL, {
        headers: {
          accept: 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`CoinGecko request failed with status ${response.status}.`);
      }

      const data = await response.json();
      setCoins(data);
      setUpdatedAt(new Date());
    } catch (fetchError) {
      setError(
        fetchError instanceof Error
          ? fetchError.message
          : 'Something went wrong while fetching market data.',
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMarkets();
  }, [fetchMarkets]);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      fetchMarkets();
    }, 60000);

    return () => window.clearInterval(intervalId);
  }, [fetchMarkets]);

  return {
    coins,
    loading,
    error,
    updatedAt,
    refetch: fetchMarkets,
  };
}
