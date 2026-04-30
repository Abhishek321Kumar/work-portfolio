import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  ChevronRight,
  MoonStar,
  RefreshCw,
  Search,
  Sparkles,
  SunMedium,
  TriangleAlert,
} from 'lucide-react';
import { useCryptoMarkets } from './hooks/useCryptoMarkets';
import { formatCompactCurrency, formatNumber, formatPercent, formatSupply } from './utils/formatters';
import { cn } from './utils/cn';

const THEMES = {
  dark: 'dark',
  light: 'light',
};

const statCards = [
  {
    key: 'market_cap',
    label: 'Tracked Market Cap',
    icon: Activity,
  },
  {
    key: 'volume',
    label: '24H Volume',
    icon: Sparkles,
  },
  {
    key: 'gainers',
    label: 'Top Movers Up',
    icon: ChevronRight,
  },
];

function ThemeToggle({ theme, onToggle }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-slate-800/80 bg-slate-900/80 text-slate-100 transition hover:border-emerald-400/40 hover:text-emerald-300 dark:border-slate-800/80 dark:bg-slate-900/80 light:border-slate-200 light:bg-white light:text-slate-800"
      aria-label="Toggle color theme"
    >
      {theme === THEMES.dark ? <SunMedium size={18} /> : <MoonStar size={18} />}
    </button>
  );
}

function SearchField({ value, onChange }) {
  return (
    <label className="flex h-12 items-center gap-3 rounded-full border border-slate-800/70 bg-slate-900/75 px-4 shadow-soft transition focus-within:border-sky-400/50 dark:border-slate-800/70 dark:bg-slate-900/75 light:border-slate-200 light:bg-white">
      <Search size={18} className="text-slate-400" />
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Search by asset name or symbol"
        className="w-full bg-transparent text-sm text-slate-100 outline-none placeholder:text-slate-500 light:text-slate-900"
      />
    </label>
  );
}

function StatCard({ label, value, helper, icon: Icon }) {
  return (
    <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-5 shadow-soft backdrop-blur-sm light:border-slate-200 light:bg-white">
      <div className="mb-5 flex items-center justify-between">
        <span className="text-sm text-slate-400 light:text-slate-500">{label}</span>
        <span className="rounded-full border border-emerald-400/20 bg-emerald-500/10 p-2 text-emerald-300 light:border-emerald-200 light:bg-emerald-50 light:text-emerald-600">
          <Icon size={16} />
        </span>
      </div>
      <div className="space-y-1">
        <p className="text-2xl font-semibold tracking-tight text-white light:text-slate-900">{value}</p>
        <p className="text-sm text-slate-400 light:text-slate-500">{helper}</p>
      </div>
    </div>
  );
}

function PriceChangePill({ value }) {
  const positive = value >= 0;

  return (
    <span
      className={cn(
        'inline-flex min-w-20 justify-center rounded-full px-3 py-1 text-xs font-semibold',
        positive
          ? 'bg-emerald-500/15 text-emerald-300 light:bg-emerald-50 light:text-emerald-700'
          : 'bg-rose-500/15 text-rose-300 light:bg-rose-50 light:text-rose-700',
      )}
    >
      {formatPercent(value)}
    </span>
  );
}

function MarketTable({ coins, onSelect }) {
  return (
    <div className="overflow-hidden rounded-3xl border border-white/8 bg-slate-950/70 shadow-soft backdrop-blur-sm light:border-slate-200 light:bg-white">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-white/5 light:divide-slate-200">
          <thead className="bg-white/[0.03] light:bg-slate-50">
            <tr className="text-left text-xs uppercase tracking-[0.18em] text-slate-500">
              <th className="px-5 py-4 font-medium">Asset</th>
              <th className="px-5 py-4 font-medium">Price</th>
              <th className="px-5 py-4 font-medium">24h</th>
              <th className="px-5 py-4 font-medium">Market Cap</th>
              <th className="px-5 py-4 font-medium">Volume</th>
              <th className="px-5 py-4 font-medium">Rank</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 light:divide-slate-200">
            {coins.map((coin) => (
              <tr
                key={coin.id}
                onClick={() => onSelect(coin)}
                className="cursor-pointer transition hover:bg-white/[0.03] light:hover:bg-slate-50"
              >
                <td className="px-5 py-4">
                  <div className="flex items-center gap-3">
                    <img src={coin.image} alt={coin.name} className="h-10 w-10 rounded-full" loading="lazy" />
                    <div>
                      <p className="font-medium text-white light:text-slate-900">{coin.name}</p>
                      <p className="text-sm uppercase text-slate-500">{coin.symbol}</p>
                    </div>
                  </div>
                </td>
                <td className="px-5 py-4 text-sm font-medium text-white light:text-slate-900">
                  {formatCompactCurrency(coin.current_price)}
                </td>
                <td className="px-5 py-4 text-sm">
                  <PriceChangePill value={coin.price_change_percentage_24h ?? 0} />
                </td>
                <td className="px-5 py-4 text-sm text-slate-300 light:text-slate-700">
                  {formatCompactCurrency(coin.market_cap)}
                </td>
                <td className="px-5 py-4 text-sm text-slate-300 light:text-slate-700">
                  {formatCompactCurrency(coin.total_volume)}
                </td>
                <td className="px-5 py-4 text-sm text-slate-400 light:text-slate-500">#{coin.market_cap_rank}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MobileCards({ coins, onSelect }) {
  return (
    <div className="grid gap-4 lg:hidden">
      {coins.map((coin) => (
        <button
          key={coin.id}
          type="button"
          onClick={() => onSelect(coin)}
          className="rounded-2xl border border-white/8 bg-white/[0.03] p-4 text-left shadow-soft transition hover:border-sky-400/30 light:border-slate-200 light:bg-white"
        >
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <img src={coin.image} alt={coin.name} className="h-11 w-11 rounded-full" loading="lazy" />
              <div>
                <p className="font-medium text-white light:text-slate-900">{coin.name}</p>
                <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{coin.symbol}</p>
              </div>
            </div>
            <PriceChangePill value={coin.price_change_percentage_24h ?? 0} />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-slate-500">Price</p>
              <p className="mt-1 font-medium text-white light:text-slate-900">
                {formatCompactCurrency(coin.current_price)}
              </p>
            </div>
            <div>
              <p className="text-slate-500">Market Cap</p>
              <p className="mt-1 font-medium text-white light:text-slate-900">
                {formatCompactCurrency(coin.market_cap)}
              </p>
            </div>
          </div>
        </button>
      ))}
    </div>
  );
}

function LoadingState() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <div
            key={index}
            className="h-36 animate-pulse rounded-2xl border border-white/8 bg-white/[0.03] light:border-slate-200 light:bg-white"
          />
        ))}
      </div>
      <div className="space-y-4 rounded-3xl border border-white/8 bg-white/[0.03] p-5 light:border-slate-200 light:bg-white">
        {Array.from({ length: 8 }).map((_, index) => (
          <div key={index} className="h-14 animate-pulse rounded-2xl bg-white/[0.04] light:bg-slate-100" />
        ))}
      </div>
    </div>
  );
}

function ErrorState({ message, onRetry }) {
  return (
    <div className="rounded-3xl border border-rose-500/20 bg-rose-500/10 p-8 text-center shadow-soft light:border-rose-200 light:bg-rose-50">
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-rose-500/15 text-rose-300 light:bg-rose-100 light:text-rose-600">
        <TriangleAlert size={24} />
      </div>
      <h2 className="text-xl font-semibold text-white light:text-slate-900">Unable to load live prices</h2>
      <p className="mx-auto mt-2 max-w-xl text-sm text-slate-300 light:text-slate-600">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-5 inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-emerald-100 light:bg-slate-900 light:text-white light:hover:bg-slate-700"
      >
        <RefreshCw size={16} />
        Retry
      </button>
    </div>
  );
}

function DetailRow({ label, value }) {
  return (
    <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4 light:border-slate-200 light:bg-slate-50">
      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-2 text-lg font-semibold text-white light:text-slate-900">{value}</p>
    </div>
  );
}

function AssetDrawer({ coin, onClose }) {
  return (
    <div className="fixed inset-0 z-30 flex justify-end bg-slate-950/60 backdrop-blur-sm" onClick={onClose}>
      <aside
        className="h-full w-full max-w-xl overflow-y-auto border-l border-white/8 bg-slate-950/95 p-6 shadow-soft light:border-slate-200 light:bg-white"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <img src={coin.image} alt={coin.name} className="h-14 w-14 rounded-full" />
            <div>
              <h2 className="text-2xl font-semibold text-white light:text-slate-900">{coin.name}</h2>
              <p className="mt-1 text-sm uppercase tracking-[0.18em] text-slate-500">{coin.symbol}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-white/10 px-3 py-2 text-sm text-slate-300 transition hover:border-slate-400 hover:text-white light:border-slate-200 light:text-slate-700"
          >
            Close
          </button>
        </div>

        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          <DetailRow label="Current Price" value={formatCompactCurrency(coin.current_price)} />
          <DetailRow label="24h Change" value={formatPercent(coin.price_change_percentage_24h ?? 0)} />
          <DetailRow label="24h High" value={formatCompactCurrency(coin.high_24h)} />
          <DetailRow label="24h Low" value={formatCompactCurrency(coin.low_24h)} />
          <DetailRow label="Market Cap" value={formatCompactCurrency(coin.market_cap)} />
          <DetailRow label="Total Volume" value={formatCompactCurrency(coin.total_volume)} />
          <DetailRow label="Circulating Supply" value={formatSupply(coin.circulating_supply, coin.symbol)} />
          <DetailRow label="Total Supply" value={formatSupply(coin.total_supply, coin.symbol)} />
          <DetailRow label="Max Supply" value={formatSupply(coin.max_supply, coin.symbol)} />
          <DetailRow label="ATH" value={formatCompactCurrency(coin.ath)} />
          <DetailRow label="ATL" value={formatCompactCurrency(coin.atl)} />
          <DetailRow label="Rank" value={`#${formatNumber(coin.market_cap_rank)}`} />
        </div>
      </aside>
    </div>
  );
}

function EmptyState({ search }) {
  return (
    <div className="rounded-3xl border border-dashed border-white/10 bg-white/[0.02] px-6 py-12 text-center light:border-slate-300 light:bg-white">
      <h2 className="text-xl font-semibold text-white light:text-slate-900">No assets match that search</h2>
      <p className="mt-2 text-sm text-slate-400 light:text-slate-500">
        Try another name or ticker. Nothing in the current market set matches "{search}".
      </p>
    </div>
  );
}

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('pulse-theme') ?? THEMES.dark);
  const [query, setQuery] = useState('');
  const [selectedCoin, setSelectedCoin] = useState(null);
  const { coins, loading, error, refetch, updatedAt } = useCryptoMarkets();

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('dark', theme === THEMES.dark);
    root.classList.toggle('light', theme === THEMES.light);
    localStorage.setItem('pulse-theme', theme);
  }, [theme]);

  useEffect(() => {
    if (!selectedCoin) {
      return;
    }

    const nextSelected = coins.find((coin) => coin.id === selectedCoin.id);
    if (nextSelected) {
      setSelectedCoin(nextSelected);
    }
  }, [coins, selectedCoin]);

  const filteredCoins = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) {
      return coins;
    }

    return coins.filter((coin) => {
      return (
        coin.name.toLowerCase().includes(normalizedQuery) ||
        coin.symbol.toLowerCase().includes(normalizedQuery)
      );
    });
  }, [coins, query]);

  const stats = useMemo(() => {
    const marketCap = coins.reduce((sum, coin) => sum + (coin.market_cap ?? 0), 0);
    const volume = coins.reduce((sum, coin) => sum + (coin.total_volume ?? 0), 0);
    const gainers = coins.filter((coin) => (coin.price_change_percentage_24h ?? 0) > 0).length;

    return {
      market_cap: formatCompactCurrency(marketCap),
      volume: formatCompactCurrency(volume),
      gainers: `${gainers}/${coins.length || 0}`,
    };
  }, [coins]);

  return (
    <div className="min-h-screen">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-4 py-6 sm:px-6 lg:px-8">
        <header className="rounded-[28px] border border-white/8 bg-slate-950/65 px-5 py-6 shadow-soft backdrop-blur-sm light:border-slate-200 light:bg-white/90 sm:px-7">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <p className="text-sm uppercase tracking-[0.22em] text-emerald-300 light:text-emerald-600">
                Real-time market pulse
              </p>
              <h1 className="mt-3 text-4xl font-semibold tracking-tight text-white light:text-slate-900 sm:text-5xl">
                Cryptomania Dashboard
              </h1>
              <p className="mt-4 max-w-xl text-sm leading-6 text-slate-300 light:text-slate-600 sm:text-base">
                A responsive cryptocurrency tracker with live CoinGecko pricing, instant asset search, and a
                deep-dive panel for the metrics traders reach for most.
              </p>
            </div>

            <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
              <SearchField value={query} onChange={setQuery} />
              <button
                type="button"
                onClick={refetch}
                className="inline-flex h-12 items-center justify-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-5 text-sm font-medium text-white transition hover:border-sky-400/40 hover:text-sky-200 light:border-slate-200 light:bg-slate-100 light:text-slate-800"
              >
                <RefreshCw size={16} />
                Refresh
              </button>
              <ThemeToggle
                theme={theme}
                onToggle={() => setTheme((current) => (current === THEMES.dark ? THEMES.light : THEMES.dark))}
              />
            </div>
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-3 text-sm text-slate-400 light:text-slate-500">
            <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 light:border-slate-200 light:bg-slate-100">
              Tracking {coins.length} assets
            </span>
            <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 light:border-slate-200 light:bg-slate-100">
              Search updates instantly
            </span>
            <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 light:border-slate-200 light:bg-slate-100">
              Last refresh {updatedAt ? updatedAt.toLocaleTimeString() : 'pending'}
            </span>
          </div>
        </header>

        <main className="mt-6 flex-1">
          {loading ? (
            <LoadingState />
          ) : error ? (
            <ErrorState message={error} onRetry={refetch} />
          ) : (
            <div className="space-y-6">
              <section className="grid gap-4 md:grid-cols-3">
                {statCards.map(({ key, label, icon }) => (
                  <StatCard
                    key={key}
                    label={label}
                    value={stats[key]}
                    helper={
                      key === 'gainers'
                        ? 'Assets currently printing green in the 24h window'
                        : 'Calculated from the live top-market asset set'
                    }
                    icon={icon}
                  />
                ))}
              </section>

              <section className="hidden lg:block">
                {filteredCoins.length > 0 ? (
                  <MarketTable coins={filteredCoins} onSelect={setSelectedCoin} />
                ) : (
                  <EmptyState search={query} />
                )}
              </section>

              <section className="lg:hidden">
                {filteredCoins.length > 0 ? (
                  <MobileCards coins={filteredCoins} onSelect={setSelectedCoin} />
                ) : (
                  <EmptyState search={query} />
                )}
              </section>
            </div>
          )}
        </main>

        <footer className="mt-8 border-t border-white/8 py-6 text-center text-sm text-slate-400 light:border-slate-200 light:text-slate-500">
          <p className="font-medium text-white light:text-slate-900">Cryptomania</p>
          <p className="mt-1">Live cryptocurrency market tracking dashboard.</p>
        </footer>
      </div>

      {selectedCoin ? <AssetDrawer coin={selectedCoin} onClose={() => setSelectedCoin(null)} /> : null}
    </div>
  );
}
