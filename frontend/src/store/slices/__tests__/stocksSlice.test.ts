/**
 * Comprehensive unit tests for stocks Redux slice.
 */

import { HotStock, MarketIndex, Stock } from '../../../types/stock';
import stocksReducer, {
    addToWatchlist,
    clearSearchResults,
    removeFromWatchlist,
    setError,
    setHotStocks,
    setLoading,
    setMarketIndices,
    setSearchResults,
    setSelectedStock,
    setWatchlist,
} from '../stocksSlice';

// Sample test data
const mockStock: Stock = {
  ticker: '7203',
  company_name_jp: 'トヨタ自動車株式会社',
  company_name_en: 'Toyota Motor Corporation',
  sector_jp: '輸送用機器',
  industry_jp: '自動車',
  current_price: 2500,
  price_change: 25,
  price_change_percent: 1.0,
  match_score: 0.95,
};

const mockStock2: Stock = {
  ticker: '6758',
  company_name_jp: 'ソニーグループ株式会社',
  company_name_en: 'Sony Group Corporation',
  sector_jp: '電気機器',
  industry_jp: 'エレクトロニクス',
  current_price: 12000,
  price_change: -150,
  price_change_percent: -1.23,
  match_score: 0.87,
};

const mockMarketIndex: MarketIndex = {
  name: 'Nikkei 225',
  value: 33000,
  change: 150,
  change_percent: 0.45,
  last_updated: '2024-01-15T09:00:00Z',
};

const mockHotStock: HotStock = {
  ticker: '7203',
  company_name_jp: 'トヨタ自動車株式会社',
  current_price: 2500,
  price_change: 25,
  price_change_percent: 1.0,
  volume: 15000000,
  category: 'gainers',
};

describe('stocksSlice', () => {
  const initialState = {
    searchResults: [],
    selectedStock: null,
    watchlist: [],
    marketIndices: [],
    hotStocks: [],
    isLoading: false,
    error: null,
  };

  describe('initial state', () => {
    it('should return the initial state', () => {
      expect(stocksReducer(undefined, { type: 'unknown' })).toEqual(initialState);
    });
  });

  describe('setLoading', () => {
    it('should set loading to true', () => {
      const action = setLoading(true);
      const state = stocksReducer(initialState, action);
      
      expect(state.isLoading).toBe(true);
    });

    it('should set loading to false', () => {
      const previousState = { ...initialState, isLoading: true };
      const action = setLoading(false);
      const state = stocksReducer(previousState, action);
      
      expect(state.isLoading).toBe(false);
    });

    it('should not affect other state properties', () => {
      const previousState = {
        ...initialState,
        searchResults: [mockStock],
        error: 'Some error',
      };
      const action = setLoading(true);
      const state = stocksReducer(previousState, action);
      
      expect(state.searchResults).toEqual([mockStock]);
      expect(state.error).toBe('Some error');
      expect(state.isLoading).toBe(true);
    });
  });

  describe('setError', () => {
    it('should set error message', () => {
      const errorMessage = 'Failed to fetch stocks';
      const action = setError(errorMessage);
      const state = stocksReducer(initialState, action);
      
      expect(state.error).toBe(errorMessage);
    });

    it('should clear error message', () => {
      const previousState = { ...initialState, error: 'Some error' };
      const action = setError(null);
      const state = stocksReducer(previousState, action);
      
      expect(state.error).toBeNull();
    });

    it('should handle empty string error', () => {
      const action = setError('');
      const state = stocksReducer(initialState, action);
      
      expect(state.error).toBe('');
    });
  });

  describe('setSearchResults', () => {
    it('should set search results with single stock', () => {
      const action = setSearchResults([mockStock]);
      const state = stocksReducer(initialState, action);
      
      expect(state.searchResults).toEqual([mockStock]);
      expect(state.searchResults).toHaveLength(1);
    });

    it('should set search results with multiple stocks', () => {
      const stocks = [mockStock, mockStock2];
      const action = setSearchResults(stocks);
      const state = stocksReducer(initialState, action);
      
      expect(state.searchResults).toEqual(stocks);
      expect(state.searchResults).toHaveLength(2);
    });

    it('should replace existing search results', () => {
      const previousState = { ...initialState, searchResults: [mockStock] };
      const newResults = [mockStock2];
      const action = setSearchResults(newResults);
      const state = stocksReducer(previousState, action);
      
      expect(state.searchResults).toEqual(newResults);
      expect(state.searchResults).toHaveLength(1);
    });

    it('should handle empty search results', () => {
      const previousState = { ...initialState, searchResults: [mockStock] };
      const action = setSearchResults([]);
      const state = stocksReducer(previousState, action);
      
      expect(state.searchResults).toEqual([]);
      expect(state.searchResults).toHaveLength(0);
    });
  });

  describe('setSelectedStock', () => {
    it('should set selected stock', () => {
      const action = setSelectedStock(mockStock);
      const state = stocksReducer(initialState, action);
      
      expect(state.selectedStock).toEqual(mockStock);
    });

    it('should clear selected stock', () => {
      const previousState = { ...initialState, selectedStock: mockStock };
      const action = setSelectedStock(null);
      const state = stocksReducer(previousState, action);
      
      expect(state.selectedStock).toBeNull();
    });

    it('should replace existing selected stock', () => {
      const previousState = { ...initialState, selectedStock: mockStock };
      const action = setSelectedStock(mockStock2);
      const state = stocksReducer(previousState, action);
      
      expect(state.selectedStock).toEqual(mockStock2);
    });
  });

  describe('setWatchlist', () => {
    it('should set watchlist with single stock', () => {
      const action = setWatchlist([mockStock]);
      const state = stocksReducer(initialState, action);
      
      expect(state.watchlist).toEqual([mockStock]);
      expect(state.watchlist).toHaveLength(1);
    });

    it('should set watchlist with multiple stocks', () => {
      const stocks = [mockStock, mockStock2];
      const action = setWatchlist(stocks);
      const state = stocksReducer(initialState, action);
      
      expect(state.watchlist).toEqual(stocks);
      expect(state.watchlist).toHaveLength(2);
    });

    it('should replace existing watchlist', () => {
      const previousState = { ...initialState, watchlist: [mockStock] };
      const newWatchlist = [mockStock2];
      const action = setWatchlist(newWatchlist);
      const state = stocksReducer(previousState, action);
      
      expect(state.watchlist).toEqual(newWatchlist);
      expect(state.watchlist).toHaveLength(1);
    });

    it('should handle empty watchlist', () => {
      const previousState = { ...initialState, watchlist: [mockStock] };
      const action = setWatchlist([]);
      const state = stocksReducer(previousState, action);
      
      expect(state.watchlist).toEqual([]);
      expect(state.watchlist).toHaveLength(0);
    });
  });

  describe('addToWatchlist', () => {
    it('should add stock to empty watchlist', () => {
      const action = addToWatchlist(mockStock);
      const state = stocksReducer(initialState, action);
      
      expect(state.watchlist).toEqual([mockStock]);
      expect(state.watchlist).toHaveLength(1);
    });

    it('should add stock to existing watchlist', () => {
      const previousState = { ...initialState, watchlist: [mockStock] };
      const action = addToWatchlist(mockStock2);
      const state = stocksReducer(previousState, action);
      
      expect(state.watchlist).toEqual([mockStock, mockStock2]);
      expect(state.watchlist).toHaveLength(2);
    });

    it('should not add duplicate stock to watchlist', () => {
      const previousState = { ...initialState, watchlist: [mockStock] };
      const action = addToWatchlist(mockStock);
      const state = stocksReducer(previousState, action);
      
      expect(state.watchlist).toEqual([mockStock]);
      expect(state.watchlist).toHaveLength(1);
    });

    it('should identify duplicates by ticker', () => {
      const duplicateStock = { ...mockStock, company_name_jp: 'Different Name' };
      const previousState = { ...initialState, watchlist: [mockStock] };
      const action = addToWatchlist(duplicateStock);
      const state = stocksReducer(previousState, action);
      
      expect(state.watchlist).toEqual([mockStock]);
      expect(state.watchlist).toHaveLength(1);
    });
  });

  describe('removeFromWatchlist', () => {
    it('should remove stock from watchlist by ticker', () => {
      const previousState = { ...initialState, watchlist: [mockStock, mockStock2] };
      const action = removeFromWatchlist('7203');
      const state = stocksReducer(previousState, action);
      
      expect(state.watchlist).toEqual([mockStock2]);
      expect(state.watchlist).toHaveLength(1);
    });

    it('should handle removing non-existent stock', () => {
      const previousState = { ...initialState, watchlist: [mockStock] };
      const action = removeFromWatchlist('9999');
      const state = stocksReducer(previousState, action);
      
      expect(state.watchlist).toEqual([mockStock]);
      expect(state.watchlist).toHaveLength(1);
    });

    it('should handle removing from empty watchlist', () => {
      const action = removeFromWatchlist('7203');
      const state = stocksReducer(initialState, action);
      
      expect(state.watchlist).toEqual([]);
      expect(state.watchlist).toHaveLength(0);
    });

    it('should remove all instances of ticker', () => {
      // This shouldn't happen in practice, but test the behavior
      const duplicateStock = { ...mockStock };
      const previousState = { ...initialState, watchlist: [mockStock, duplicateStock, mockStock2] };
      const action = removeFromWatchlist('7203');
      const state = stocksReducer(previousState, action);
      
      expect(state.watchlist).toEqual([mockStock2]);
      expect(state.watchlist).toHaveLength(1);
    });
  });

  describe('setMarketIndices', () => {
    it('should set market indices', () => {
      const indices = [mockMarketIndex];
      const action = setMarketIndices(indices);
      const state = stocksReducer(initialState, action);
      
      expect(state.marketIndices).toEqual(indices);
      expect(state.marketIndices).toHaveLength(1);
    });

    it('should replace existing market indices', () => {
      const previousState = { ...initialState, marketIndices: [mockMarketIndex] };
      const newIndex = { ...mockMarketIndex, name: 'TOPIX', value: 2400 };
      const action = setMarketIndices([newIndex]);
      const state = stocksReducer(previousState, action);
      
      expect(state.marketIndices).toEqual([newIndex]);
      expect(state.marketIndices).toHaveLength(1);
    });

    it('should handle empty market indices', () => {
      const previousState = { ...initialState, marketIndices: [mockMarketIndex] };
      const action = setMarketIndices([]);
      const state = stocksReducer(previousState, action);
      
      expect(state.marketIndices).toEqual([]);
      expect(state.marketIndices).toHaveLength(0);
    });
  });

  describe('setHotStocks', () => {
    it('should set hot stocks', () => {
      const hotStocks = [mockHotStock];
      const action = setHotStocks(hotStocks);
      const state = stocksReducer(initialState, action);
      
      expect(state.hotStocks).toEqual(hotStocks);
      expect(state.hotStocks).toHaveLength(1);
    });

    it('should replace existing hot stocks', () => {
      const previousState = { ...initialState, hotStocks: [mockHotStock] };
      const newHotStock = { ...mockHotStock, ticker: '6758', category: 'losers' as const };
      const action = setHotStocks([newHotStock]);
      const state = stocksReducer(previousState, action);
      
      expect(state.hotStocks).toEqual([newHotStock]);
      expect(state.hotStocks).toHaveLength(1);
    });

    it('should handle empty hot stocks', () => {
      const previousState = { ...initialState, hotStocks: [mockHotStock] };
      const action = setHotStocks([]);
      const state = stocksReducer(previousState, action);
      
      expect(state.hotStocks).toEqual([]);
      expect(state.hotStocks).toHaveLength(0);
    });
  });

  describe('clearSearchResults', () => {
    it('should clear search results', () => {
      const previousState = { ...initialState, searchResults: [mockStock, mockStock2] };
      const action = clearSearchResults();
      const state = stocksReducer(previousState, action);
      
      expect(state.searchResults).toEqual([]);
      expect(state.searchResults).toHaveLength(0);
    });

    it('should not affect other state properties', () => {
      const previousState = {
        ...initialState,
        searchResults: [mockStock],
        selectedStock: mockStock,
        watchlist: [mockStock2],
        isLoading: true,
        error: 'Some error',
      };
      const action = clearSearchResults();
      const state = stocksReducer(previousState, action);
      
      expect(state.searchResults).toEqual([]);
      expect(state.selectedStock).toEqual(mockStock);
      expect(state.watchlist).toEqual([mockStock2]);
      expect(state.isLoading).toBe(true);
      expect(state.error).toBe('Some error');
    });

    it('should handle clearing already empty search results', () => {
      const action = clearSearchResults();
      const state = stocksReducer(initialState, action);
      
      expect(state.searchResults).toEqual([]);
      expect(state.searchResults).toHaveLength(0);
    });
  });

  describe('state immutability', () => {
    it('should not mutate the original state', () => {
      const originalState = { ...initialState };
      const action = setSearchResults([mockStock]);
      
      stocksReducer(originalState, action);
      
      expect(originalState).toEqual(initialState);
    });

    it('should not mutate nested arrays', () => {
      const originalWatchlist = [mockStock];
      const previousState = { ...initialState, watchlist: originalWatchlist };
      const action = addToWatchlist(mockStock2);
      
      stocksReducer(previousState, action);
      
      expect(originalWatchlist).toEqual([mockStock]);
      expect(originalWatchlist).toHaveLength(1);
    });
  });

  describe('action creators', () => {
    it('should create setLoading action', () => {
      const action = setLoading(true);
      expect(action).toEqual({
        type: 'stocks/setLoading',
        payload: true,
      });
    });

    it('should create setError action', () => {
      const errorMessage = 'Test error';
      const action = setError(errorMessage);
      expect(action).toEqual({
        type: 'stocks/setError',
        payload: errorMessage,
      });
    });

    it('should create addToWatchlist action', () => {
      const action = addToWatchlist(mockStock);
      expect(action).toEqual({
        type: 'stocks/addToWatchlist',
        payload: mockStock,
      });
    });

    it('should create removeFromWatchlist action', () => {
      const action = removeFromWatchlist('7203');
      expect(action).toEqual({
        type: 'stocks/removeFromWatchlist',
        payload: '7203',
      });
    });

    it('should create clearSearchResults action', () => {
      const action = clearSearchResults();
      expect(action).toEqual({
        type: 'stocks/clearSearchResults',
      });
    });
  });

  describe('complex state transitions', () => {
    it('should handle multiple actions in sequence', () => {
      let state = stocksReducer(initialState, setLoading(true));
      state = stocksReducer(state, setSearchResults([mockStock, mockStock2]));
      state = stocksReducer(state, setSelectedStock(mockStock));
      state = stocksReducer(state, addToWatchlist(mockStock));
      state = stocksReducer(state, setLoading(false));
      
      expect(state).toEqual({
        searchResults: [mockStock, mockStock2],
        selectedStock: mockStock,
        watchlist: [mockStock],
        marketIndices: [],
        hotStocks: [],
        isLoading: false,
        error: null,
      });
    });

    it('should handle error and recovery flow', () => {
      let state = stocksReducer(initialState, setLoading(true));
      state = stocksReducer(state, setError('Network error'));
      state = stocksReducer(state, setLoading(false));
      state = stocksReducer(state, setError(null));
      state = stocksReducer(state, setSearchResults([mockStock]));
      
      expect(state).toEqual({
        searchResults: [mockStock],
        selectedStock: null,
        watchlist: [],
        marketIndices: [],
        hotStocks: [],
        isLoading: false,
        error: null,
      });
    });
  });
});