/**
 * src/api/client.js - Backend API Client
 * ======================================
 * Interfaces with FastAPI endpoints (/api/strategies, /api/run) via native fetch.
 */

async function handleResponse(response) {
  if (!response.ok) {
    let errorMessage = `Server error (${response.status})`;
    try {
      const errorData = await response.json();
      if (errorData) {
        if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          // Pydantic validation errors
          errorMessage = errorData.detail
            .map((err) => `${err.loc ? err.loc.slice(-1).join('') + ': ' : ''}${err.msg}`)
            .join('; ');
        } else if (errorData.message) {
          errorMessage = errorData.message;
        }
      }
    } catch {
      // response body was not JSON
    }
    throw new Error(errorMessage);
  }
  return response.json();
}

/**
 * Fetches dynamic metadata and descriptions for all 4 momentum strategies.
 *
 * @returns {Promise<Array<{id: number, name: string, description: string}>>}
 */
export async function getStrategies() {
  try {
    const response = await fetch('/api/strategies', {
      headers: {
        Accept: 'application/json',
      },
    });
    return await handleResponse(response);
  } catch (err) {
    if (err.name === 'TypeError' || (err.message && err.message.includes('fetch'))) {
      throw new Error(
        'Unable to connect to the backend server. Please verify the FastAPI backend is running on http://localhost:8000.'
      );
    }
    throw err;
  }
}

/**
 * Executes the quantitative backtest simulation with dynamic capital and top-X parameter.
 *
 * @param {number} capital - Total capital in INR (min 10,000, max 100,000,000)
 * @param {number} x - Top X momentum stocks to hold (min 5, max 50)
 * @returns {Promise<Object>} Complete simulation result dictionary
 */
export async function runBacktest(capital, x) {
  try {
    const response = await fetch('/api/run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        capital: Number(capital),
        x: parseInt(x, 10),
      }),
    });
    return await handleResponse(response);
  } catch (err) {
    if (err.name === 'TypeError' || (err.message && err.message.includes('fetch'))) {
      throw new Error(
        'Unable to connect to the backend server. Please verify the FastAPI backend is running on http://localhost:8000.'
      );
    }
    throw err;
  }
}

/**
 * Service health check endpoint.
 */
export async function checkHealth() {
  try {
    const response = await fetch('/api/health');
    return await handleResponse(response);
  } catch {
    return { status: 'offline' };
  }
}
