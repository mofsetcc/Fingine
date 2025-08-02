import { createAsyncThunk, createSlice, PayloadAction } from '@reduxjs/toolkit';
import { WatchlistStockWithPrice } from '../../types/watchlist';

// API base URL
const API_BASE = '/api/v1/watchlist';

// Async thunks for API calls
export const fetchWatchlist = createAsyncThunk(
  'watchlist/fetchWatchlist',
  async (_, { rejectWithValue }) => {
    try {
      const response = await fetch(API_BASE, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch watchlist');
      }
      
      return await response.json();
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Unknown error');
    }
  }
);

export const addStockToWatchlist = createAsyncThunk(
  'watchlist/addStock',
  async (stockData: { ticker: string; notes?: string }, { rejectWithValue }) => {
    try {
      const response = await fetch(API_BASE, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(stockData),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to add stock to watchlist');
      }
      
      return await response.json();
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Unknown error');
    }
  }
);

export const updateWatchlistStock = createAsyncThunk(
  'watchlist/updateStock',
  async ({ ticker, data }: { ticker: string; data: SimpleWatchlistStockUpdate }, { rejectWithValue }) => {
    try {
      const response = await fetch(`${API_BASE}/${ticker}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update watchlist stock');
      }
      
      return await response.json();
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Unknown error');
    }
  }
);

export const removeStockFromWatchlist = createAsyncThunk(
  'watchlist/removeStock',
  async (ticker: string, { rejectWithValue }) => {
    try {
      const response = await fetch(`${API_BASE}/${ticker}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to remove stock from watchlist');
      }
      
      return ticker;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Unknown error');
    }
  }
);

export const bulkAddStocksToWatchlist = createAsyncThunk(
  'watchlist/bulkAddStocks',
  async (tickers: string[], { rejectWithValue }) => {
    try {
      const response = await fetch(`${API_BASE}/bulk-add`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(tickers),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to bulk add stocks to watchlist');
      }
      
      return await response.json();
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Unknown error');
    }
  }
);

// Watchlist state interface
interface WatchlistState {
  stocks: WatchlistStockWithPrice[];
  isLoading: boolean;
  error: string | null;
  lastUpdated: string | null;
}

// Initial state
const initialState: WatchlistState = {
  stocks: [],
  isLoading: false,
  error: null,
  lastUpdated: null,
};

// Watchlist slice
const watchlistSlice = createSlice({
  name: 'watchlist',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    updateStockPrice: (state, action: PayloadAction<{ ticker: string; priceData: any }>) => {
      const { ticker, priceData } = action.payload;
      const stock = state.stocks.find(s => s.ticker === ticker);
      if (stock) {
        stock.current_price = priceData.current_price;
        stock.price_change = priceData.price_change;
        stock.price_change_percent = priceData.price_change_percent;
        stock.volume_today = priceData.volume_today;
        stock.last_updated = priceData.last_updated;
      }
    },
  },
  extraReducers: (builder) => {
    // Fetch watchlist
    builder
      .addCase(fetchWatchlist.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchWatchlist.fulfilled, (state, action) => {
        state.isLoading = false;
        state.stocks = action.payload;
        state.lastUpdated = new Date().toISOString();
      })
      .addCase(fetchWatchlist.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Add stock to watchlist
    builder
      .addCase(addStockToWatchlist.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(addStockToWatchlist.fulfilled, (state, action) => {
        state.isLoading = false;
        state.stocks.unshift(action.payload);
      })
      .addCase(addStockToWatchlist.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Update watchlist stock
    builder
      .addCase(updateWatchlistStock.pending, (state) => {
        state.error = null;
      })
      .addCase(updateWatchlistStock.fulfilled, (state, action) => {
        const index = state.stocks.findIndex(s => s.ticker === action.payload.ticker);
        if (index !== -1) {
          state.stocks[index] = action.payload;
        }
      })
      .addCase(updateWatchlistStock.rejected, (state, action) => {
        state.error = action.payload as string;
      });

    // Remove stock from watchlist
    builder
      .addCase(removeStockFromWatchlist.pending, (state) => {
        state.error = null;
      })
      .addCase(removeStockFromWatchlist.fulfilled, (state, action) => {
        state.stocks = state.stocks.filter(s => s.ticker !== action.payload);
      })
      .addCase(removeStockFromWatchlist.rejected, (state, action) => {
        state.error = action.payload as string;
      });

    // Bulk add stocks
    builder
      .addCase(bulkAddStocksToWatchlist.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(bulkAddStocksToWatchlist.fulfilled, (state, action) => {
        state.isLoading = false;
        // Refresh watchlist after bulk operation
      })
      .addCase(bulkAddStocksToWatchlist.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Real-time price updates
    builder
      .addCase(fetchRealTimePrices.fulfilled, (state, action) => {
        const priceUpdates = action.payload;
        state.stocks.forEach(stock => {
          const priceUpdate = priceUpdates[stock.ticker];
          if (priceUpdate) {
            stock.current_price = priceUpdate.current_price;
            stock.price_change = priceUpdate.price_change;
            stock.price_change_percent = priceUpdate.price_change_percent;
            stock.volume_today = priceUpdate.volume_today;
            stock.last_updated = priceUpdate.last_updated;
          }
        });
        state.lastUpdated = new Date().toISOString();
      });
  },
});

// Real-time price updates
export const fetchRealTimePrices = createAsyncThunk(
  'watchlist/fetchRealTimePrices',
  async (tickers: string[], { rejectWithValue }) => {
    try {
      const response = await fetch('/api/v1/stocks/prices/batch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ tickers }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch real-time prices');
      }
      
      return await response.json();
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Unknown error');
    }
  }
);

export const { clearError, updateStockPrice } = watchlistSlice.actions;
export default watchlistSlice.reducer;