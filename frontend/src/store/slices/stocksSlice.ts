/**
 * Stocks data state management slice.
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { Stock, MarketIndex, HotStock } from '../../types';

interface StocksState {
  searchResults: Stock[];
  selectedStock: Stock | null;
  watchlist: Stock[];
  marketIndices: MarketIndex[];
  hotStocks: HotStock[];
  isLoading: boolean;
  error: string | null;
}

const initialState: StocksState = {
  searchResults: [],
  selectedStock: null,
  watchlist: [],
  marketIndices: [],
  hotStocks: [],
  isLoading: false,
  error: null,
};

const stocksSlice = createSlice({
  name: 'stocks',
  initialState,
  reducers: {
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    setSearchResults: (state, action: PayloadAction<Stock[]>) => {
      state.searchResults = action.payload;
    },
    setSelectedStock: (state, action: PayloadAction<Stock | null>) => {
      state.selectedStock = action.payload;
    },
    setWatchlist: (state, action: PayloadAction<Stock[]>) => {
      state.watchlist = action.payload;
    },
    addToWatchlist: (state, action: PayloadAction<Stock>) => {
      const exists = state.watchlist.find(stock => stock.ticker === action.payload.ticker);
      if (!exists) {
        state.watchlist.push(action.payload);
      }
    },
    removeFromWatchlist: (state, action: PayloadAction<string>) => {
      state.watchlist = state.watchlist.filter(stock => stock.ticker !== action.payload);
    },
    setMarketIndices: (state, action: PayloadAction<MarketIndex[]>) => {
      state.marketIndices = action.payload;
    },
    setHotStocks: (state, action: PayloadAction<HotStock[]>) => {
      state.hotStocks = action.payload;
    },
    clearSearchResults: (state) => {
      state.searchResults = [];
    },
  },
});

export const {
  setLoading,
  setError,
  setSearchResults,
  setSelectedStock,
  setWatchlist,
  addToWatchlist,
  removeFromWatchlist,
  setMarketIndices,
  setHotStocks,
  clearSearchResults,
} = stocksSlice.actions;

export default stocksSlice.reducer;