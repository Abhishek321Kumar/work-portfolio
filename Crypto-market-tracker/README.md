# Pulse Crypto Dashboard

A high-performance, responsive React dashboard for tracking live cryptocurrency market data with the CoinGecko Public API.

## Tech Stack

- React + Vite
- Tailwind CSS
- CoinGecko Public API
- Lucide React icons

## Features

- Live market data for the top 20 cryptocurrencies by market capitalization
- Instant client-side search by asset name or symbol
- Color-coded 24h price performance
- Responsive desktop table and mobile card layouts
- Asset details drawer with deeper market metrics
- Loading skeletons and error recovery states
- Dark and light themes persisted in `localStorage`
- Automatic background refresh every 60 seconds

## Getting Started

1. Install dependencies:

```bash
npm install
```

2. Start the development server:

```bash
npm run dev
```

3. Build for production:

```bash
npm run build
```

## Project Structure

```text
src/
  App.jsx
  hooks/
    useCryptoMarkets.js
  utils/
    cn.js
    formatters.js
```

## Technical Notes

- `useCryptoMarkets` centralizes async fetching, loading state, retry handling, and timed refreshes.
- Search results are memoized with `useMemo` to keep filtering smooth as the dataset updates.
- The UI swaps between a dense market table on desktop and touch-friendly cards on smaller screens.
- Tailwind is configured for class-based theming so the interface can persist user preferences cleanly.

## API Reference

- CoinGecko markets endpoint:
  `https://api.coingecko.com/api/v3/coins/markets`
