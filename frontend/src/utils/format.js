/**
 * src/utils/format.js - Financial Formatting Utilities
 * ====================================================
 * Robust formatting for INR currency, signed percentages, and timezone-safe dates.
 */

const MONTH_NAMES = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

/**
 * Formats a number as Indian currency (INR), e.g. ₹5,00,000.00.
 * Handles invalid, missing, and non-finite numbers gracefully.
 *
 * @param {number|string|null|undefined} amount
 * @returns {string} Formatted INR currency string
 */
export function formatINR(amount) {
  if (amount === null || amount === undefined || amount === '') {
    return '—';
  }
  const num = typeof amount === 'number' ? amount : Number(amount);
  if (!Number.isFinite(num)) {
    return '—';
  }

  try {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);
  } catch (err) {
    // Fallback in case of environment locale issues
    const sign = num < 0 ? '-' : '';
    const absVal = Math.abs(num).toFixed(2);
    return `${sign}₹${absVal}`;
  }
}

/**
 * Formats a number as a signed percentage, e.g. +12.34% or -1.20%.
 *
 * @param {number|string|null|undefined} value
 * @param {number} [decimals=2]
 * @returns {string} Formatted signed percentage
 */
export function formatPercent(value, decimals = 2) {
  if (value === null || value === undefined || value === '') {
    return '—';
  }
  const num = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(num)) {
    return '—';
  }

  const fixed = Math.abs(num).toFixed(decimals);
  if (num > 0.000001) {
    return `+${num.toFixed(decimals)}%`;
  } else if (num < -0.000001) {
    return `-${fixed}%`;
  }
  return `0.${'0'.repeat(decimals)}%`;
}

/**
 * Formats a date string as DD-MMM-YYYY (e.g. 31-Oct-2022).
 * Strictly avoids timezone shift bugs by directly extracting date-only tokens.
 *
 * @param {string|Date|null|undefined} dateStr
 * @returns {string} Formatted date string
 */
export function formatDate(dateStr) {
  if (!dateStr) return '—';

  // If already a Date object
  if (dateStr instanceof Date) {
    if (isNaN(dateStr.getTime())) return '—';
    const day = String(dateStr.getUTCDate()).padStart(2, '0');
    const month = MONTH_NAMES[dateStr.getUTCMonth()];
    const year = dateStr.getUTCFullYear();
    return `${day}-${month}-${year}`;
  }

  if (typeof dateStr !== 'string') return '—';

  // Match YYYY-MM-DD or YYYY-MM-DDTHH:mm:ss
  const match = dateStr.trim().match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (match) {
    const [, y, m, d] = match;
    const monthIndex = parseInt(m, 10) - 1;
    const day = String(parseInt(d, 10)).padStart(2, '0');
    if (monthIndex >= 0 && monthIndex < 12) {
      return `${day}-${MONTH_NAMES[monthIndex]}-${y}`;
    }
  }

  // Fallback for standard parseable date strings
  const parsed = new Date(dateStr);
  if (isNaN(parsed.getTime())) return String(dateStr);
  const day = String(parsed.getDate()).padStart(2, '0');
  const month = MONTH_NAMES[parsed.getMonth()];
  const year = parsed.getFullYear();
  return `${day}-${month}-${year}`;
}

/**
 * Formats a ratio or float to a specified number of decimal places (e.g. 0.79 or 1.06).
 * Returns '—' for null, undefined, or non-finite inputs.
 *
 * @param {number|string|null|undefined} value
 * @param {number} [decimals=2]
 * @returns {string}
 */
export function formatRatio(value, decimals = 2) {
  if (value === null || value === undefined || value === '') {
    return '—';
  }
  const num = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(num)) {
    return '—';
  }
  return num.toFixed(decimals);
}

/**
 * Formats an unsigned percentage (e.g. 21.73% or 17.60%).
 * Returns '—' for null, undefined, or non-finite inputs.
 *
 * @param {number|string|null|undefined} value
 * @param {number} [decimals=2]
 * @returns {string}
 */
export function formatUnsignedPercent(value, decimals = 2) {
  if (value === null || value === undefined || value === '') {
    return '—';
  }
  const num = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(num)) {
    return '—';
  }
  return `${num.toFixed(decimals)}%`;
}

/**
 * Compact currency formatter for chart Y-axes (e.g. ₹5.0L, ₹11.4L, ₹2.5Cr).
 *
 * @param {number|string|null|undefined} num
 * @returns {string}
 */
export function formatCompactINR(num) {
  if (num === null || num === undefined || !Number.isFinite(Number(num))) {
    return '—';
  }
  const val = Number(num);
  const sign = val < 0 ? '-' : '';
  const abs = Math.abs(val);
  if (abs >= 10000000) {
    return `${sign}₹${(abs / 10000000).toFixed(1)}Cr`;
  }
  if (abs >= 100000) {
    return `${sign}₹${(abs / 100000).toFixed(1)}L`;
  }
  if (abs >= 1000) {
    return `${sign}₹${(abs / 1000).toFixed(0)}k`;
  }
  return `${sign}₹${abs.toFixed(0)}`;
}

/**
 * Formats a YYYY-MM-DD date string into compact month-year (e.g. "Nov '22").
 *
 * @param {string} dateStr
 * @returns {string}
 */
export function formatMonthYear(dateStr) {
  if (!dateStr || typeof dateStr !== 'string') return '';
  const match = dateStr.trim().match(/^(\d{4})-(\d{2})/);
  if (!match) return dateStr;
  const [, y, m] = match;
  const monthIndex = parseInt(m, 10) - 1;
  const shortYear = y.slice(2);
  if (monthIndex >= 0 && monthIndex < 12) {
    return `${MONTH_NAMES[monthIndex]} '${shortYear}`;
  }
  return dateStr;
}


