/**
 * src/utils/metrics.js - Performance Metrics & Analytics Helpers
 * ==============================================================
 * Shared calculations for KPI extraction, best-value determination,
 * observations generation, and robust numeric sorting.
 */

/**
 * Safely extracts a numeric value from a row, returning null if invalid or missing.
 *
 * @param {Object} row
 * @param {string} key
 * @returns {number|null}
 */
export function getMetricNumber(row, key) {
  if (!row || row[key] === null || row[key] === undefined || row[key] === '') {
    return null;
  }
  const val = Number(row[key]);
  return Number.isFinite(val) ? val : null;
}

/**
 * Identifies the best metric value across performance rows.
 *
 * @param {Array<Object>} rows
 * @param {string} key
 * @param {'max'|'min'|'absMin'} direction
 * @returns {number|null}
 */
export function findBestMetricValue(rows, key, direction = 'max') {
  if (!Array.isArray(rows) || rows.length === 0) return null;

  let best = null;

  for (const row of rows) {
    const val = getMetricNumber(row, key);
    if (val === null) continue;

    if (best === null) {
      best = val;
      continue;
    }

    if (direction === 'max' && val > best) {
      best = val;
    } else if (direction === 'min' && val < best) {
      best = val;
    } else if (direction === 'absMin' && Math.abs(val) < Math.abs(best)) {
      best = val;
    }
  }

  return best;
}

/**
 * Checks if a specific value is equal to the best observed value (within floating point precision).
 *
 * @param {number|null} val
 * @param {number|null} bestVal
 * @param {'max'|'min'|'absMin'} direction
 * @returns {boolean}
 */
export function isBestValue(val, bestVal, direction = 'max') {
  if (val === null || bestVal === null) return false;
  if (!Number.isFinite(val) || !Number.isFinite(bestVal)) return false;

  if (direction === 'absMin') {
    return Math.abs(Math.abs(val) - Math.abs(bestVal)) < 1e-4;
  }
  return Math.abs(val - bestVal) < 1e-4;
}

/**
 * Finds the winning strategy record for a given metric.
 *
 * @param {Array<Object>} rows
 * @param {string} key
 * @param {'max'|'min'|'absMin'} direction
 * @returns {{ strategy: string, value: number, row: Object }|null}
 */
export function findWinningStrategy(rows, key, direction = 'max') {
  const bestVal = findBestMetricValue(rows, key, direction);
  if (bestVal === null) return null;

  for (const row of rows) {
    const val = getMetricNumber(row, key);
    if (val !== null && isBestValue(val, bestVal, direction)) {
      return {
        strategy: row.Strategy || 'Unknown Strategy',
        value: val,
        row,
      };
    }
  }
  return null;
}

/**
 * Generates neutral, evidence-based academic observations from real performance data.
 *
 * @param {Array<Object>} rows
 * @returns {Array<string>} List of dynamically derived observations
 */
export function generateKeyObservations(rows) {
  if (!Array.isArray(rows) || rows.length === 0) return [];

  const observations = [];

  // 1. Sortino Ratio Winner (Downside risk-adjusted performance)
  const sortinoWinner = findWinningStrategy(rows, 'Sortino_Ratio', 'max');
  if (sortinoWinner && sortinoWinner.value > 0) {
    observations.push(
      `In this backtest, ${sortinoWinner.strategy} recorded the highest Sortino ratio (${sortinoWinner.value.toFixed(2)}), reflecting superior returns per unit of downside volatility.`
    );
  }

  // 2. Maximum Drawdown Winner (Capital preservation)
  const ddWinner = findWinningStrategy(rows, 'Max_Drawdown_%', 'absMin');
  if (ddWinner) {
    const ddStr = `${ddWinner.value.toFixed(2)}%`;
    observations.push(
      `${ddWinner.strategy} demonstrated the strongest capital preservation with the lowest maximum drawdown (${ddStr}) over the 4-year historical simulation.`
    );
  }

  // 3. Name Turnover Winner (Portfolio stability)
  const turnoverWinner = findWinningStrategy(rows, 'Avg_Name_Turnover_%', 'min');
  if (turnoverWinner) {
    const toStr = `${turnoverWinner.value.toFixed(2)}%`;
    observations.push(
      `${turnoverWinner.strategy} achieved the lowest monthly portfolio constituent turnover (${toStr}), minimizing churn and associated market impact.`
    );
  }

  // 4. Return vs. Transaction Cost Trade-off
  const cagrWinner = findWinningStrategy(rows, 'CAGR_%', 'max');
  const costWinner = findWinningStrategy(rows, 'Total_Transaction_Costs_INR', 'min');
  if (cagrWinner && costWinner && cagrWinner.strategy !== costWinner.strategy) {
    observations.push(
      `While ${costWinner.strategy} incurred the lowest cumulative transaction costs, ${cagrWinner.strategy} generated the highest compound annual growth rate (${cagrWinner.value.toFixed(2)}% CAGR), highlighting the trade-off between active rebalancing friction and momentum alpha capture.`
    );
  }

  return observations;
}

/**
 * Sorts performance records numerically or alphabetically without mutating the original array.
 * Missing/null values are deterministically positioned at the bottom.
 *
 * @param {Array<Object>} rows
 * @param {string} sortKey
 * @param {'asc'|'desc'} sortDirection
 * @returns {Array<Object>}
 */
export function sortPerformanceRows(rows, sortKey, sortDirection = 'desc') {
  if (!Array.isArray(rows)) return [];
  const copied = [...rows];
  if (!sortKey) return copied;

  copied.sort((a, b) => {
    // String sorting for Strategy column
    if (sortKey === 'Strategy') {
      const valA = String(a.Strategy || '').toLowerCase();
      const valB = String(b.Strategy || '').toLowerCase();
      if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
      if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    }

    // Numeric sorting for all other metric columns
    const numA = getMetricNumber(a, sortKey);
    const numB = getMetricNumber(b, sortKey);

    // Keep missing values at the end regardless of sort direction
    if (numA === null && numB === null) return 0;
    if (numA === null) return 1;
    if (numB === null) return -1;

    if (numA < numB) return sortDirection === 'asc' ? -1 : 1;
    if (numA > numB) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  return copied;
}

/**
 * Computes chronological running maximum and daily drawdown series for all strategies.
 * Drawdown is always non-positive (% decline from peak, e.g. 0% to -35%).
 *
 * @param {Array<Object>} dailyEquityRows
 * @returns {Array<Object>} Array with date, s1_dd, s2_dd, s3_dd, s4_dd, etc.
 */
export function computeDailyDrawdowns(dailyEquityRows) {
  if (!Array.isArray(dailyEquityRows) || dailyEquityRows.length === 0) return [];

  // Sort chronological copy
  const rows = [...dailyEquityRows].sort((a, b) => (String(a.date) > String(b.date) ? 1 : -1));
  const runningMax = { s1: 0, s2: 0, s3: 0, s4: 0 };

  return rows.map((row) => {
    const item = { date: row.date };
    for (const s of ['s1', 's2', 's3', 's4']) {
      const eq = getMetricNumber(row, `${s}_equity`);
      if (eq !== null && eq > 0) {
        if (eq > runningMax[s]) {
          runningMax[s] = eq;
        }
        const dd = ((eq - runningMax[s]) / runningMax[s]) * 100;
        item[`${s}_dd`] = Number(dd.toFixed(2));
        item[`${s}_equity`] = eq;
      } else {
        item[`${s}_dd`] = 0;
      }
    }
    return item;
  });
}

/**
 * Derives completed monthly profit and loss (in INR) for Strategy 3 from ending equity balances.
 *
 * @param {Array<Object>} monthlyRows
 * @returns {Array<{ date: string, pnl: number, returnPct: number, endingEquity: number }>}
 */
export function computeStrategy3MonthlyPnL(monthlyRows) {
  if (!Array.isArray(monthlyRows) || monthlyRows.length < 2) return [];

  const rows = [...monthlyRows].sort((a, b) => (String(a.date) > String(b.date) ? 1 : -1));
  const result = [];

  for (let i = 1; i < rows.length; i++) {
    const curr = rows[i];
    const prev = rows[i - 1];
    const currVal = getMetricNumber(curr, 's3_value');
    const prevVal = getMetricNumber(prev, 's3_value');

    if (currVal !== null && prevVal !== null) {
      const pnl = Number((currVal - prevVal).toFixed(2));
      const ret = getMetricNumber(curr, 's3_ret') ?? (prevVal > 0 ? ((currVal - prevVal) / prevVal) * 100 : 0);
      result.push({
        date: curr.date,
        pnl,
        returnPct: Number(ret.toFixed(2)),
        endingEquity: currVal,
      });
    }
  }

  return result;
}

