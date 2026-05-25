const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  notation: 'compact',
  maximumFractionDigits: 2,
});

const numberFormatter = new Intl.NumberFormat('en-US');

export function formatCompactCurrency(value) {
  if (value == null || Number.isNaN(value)) {
    return 'N/A';
  }

  if (value < 1) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 6,
    }).format(value);
  }

  return currencyFormatter.format(value);
}

export function formatPercent(value) {
  if (value == null || Number.isNaN(value)) {
    return 'N/A';
  }

  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

export function formatNumber(value) {
  if (value == null || Number.isNaN(value)) {
    return 'N/A';
  }

  return numberFormatter.format(value);
}

export function formatSupply(value, symbol) {
  if (value == null || Number.isNaN(value)) {
    return 'N/A';
  }

  return `${new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 2,
  }).format(value)} ${symbol.toUpperCase()}`;
}
