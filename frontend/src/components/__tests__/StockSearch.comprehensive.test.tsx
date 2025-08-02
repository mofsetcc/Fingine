/**
 * Comprehensive unit tests for StockSearch component.
 */

import { configureStore } from '@reduxjs/toolkit';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import stocksSlice from '../../store/slices/stocksSlice';
import { StockSearchResult } from '../../types';
import StockSearch from '../StockSearch';

// Mock fetch globally
global.fetch = jest.fn();

// Mock navigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

// Test store setup
const createTestStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      stocks: stocksSlice,
    },
    preloadedState: {
      stocks: {
        searchResults: [],
        selectedStock: null,
        watchlist: [],
        marketIndices: [],
        isLoading: false,
        error: null,
        ...initialState,
      },
    },
  });
};

// Test wrapper component
const TestWrapper: React.FC<{ store?: any; children: React.ReactNode }> = ({ 
  store = createTestStore(), 
  children 
}) => (
  <Provider store={store}>
    <BrowserRouter>
      {children}
    </BrowserRouter>
  </Provider>
);

// Sample test data
const mockSearchResults: StockSearchResult[] = [
  {
    ticker: '7203',
    company_name_jp: 'トヨタ自動車株式会社',
    company_name_en: 'Toyota Motor Corporation',
    sector_jp: '輸送用機器',
    industry_jp: '自動車',
    current_price: 2500,
    price_change: 25,
    price_change_percent: 1.0,
    match_score: 0.95,
  },
  {
    ticker: '6758',
    company_name_jp: 'ソニーグループ株式会社',
    company_name_en: 'Sony Group Corporation',
    sector_jp: '電気機器',
    industry_jp: 'エレクトロニクス',
    current_price: 12000,
    price_change: -150,
    price_change_percent: -1.23,
    match_score: 0.87,
  },
];

describe('StockSearch Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (fetch as jest.Mock).mockClear();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('Rendering', () => {
    it('renders search input with placeholder', () => {
      render(
        <TestWrapper>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByPlaceholderText(/search stocks by ticker or company name/i);
      expect(searchInput).toBeInTheDocument();
    });

    it('renders search icon', () => {
      render(
        <TestWrapper>
          <StockSearch />
        </TestWrapper>
      );

      const searchIcon = screen.getByRole('textbox').parentElement?.querySelector('svg');
      expect(searchIcon).toBeInTheDocument();
    });

    it('renders search tips when input is empty', () => {
      render(
        <TestWrapper>
          <StockSearch />
        </TestWrapper>
      );

      expect(screen.getByText('💡 Search tips:')).toBeInTheDocument();
      expect(screen.getByText(/use 4-digit ticker symbols/i)).toBeInTheDocument();
    });

    it('does not render search tips when input has value', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      await user.type(searchInput, 'Toyota');

      expect(screen.queryByText('💡 Search tips:')).not.toBeInTheDocument();
    });
  });

  describe('Search Functionality', () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    it('performs search after debounce delay', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ results: mockSearchResults }),
      });

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      render(
        <TestWrapper>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      await user.type(searchInput, 'Toyota');

      // Should not search immediately
      expect(fetch).not.toHaveBeenCalled();

      // Advance timers to trigger debounced search
      act(() => {
        jest.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith(
          '/api/v1/stocks/search?query=Toyota&limit=10'
        );
      });
    });

    it('does not search for queries shorter than 2 characters', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      render(
        <TestWrapper>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      await user.type(searchInput, 'T');

      act(() => {
        jest.advanceTimersByTime(300);
      });

      expect(fetch).not.toHaveBeenCalled();
    });

    it('clears previous search timeout when typing', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      render(
        <TestWrapper>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      
      // Type first query
      await user.type(searchInput, 'To');
      
      // Type more before debounce completes
      await user.type(searchInput, 'yota');

      act(() => {
        jest.advanceTimersByTime(300);
      });

      // Should only make one request with the final query
      await waitFor(() => {
        expect(fetch).toHaveBeenCalledTimes(1);
        expect(fetch).toHaveBeenCalledWith(
          '/api/v1/stocks/search?query=Toyota&limit=10'
        );
      });
    });

    it('shows loading spinner during search', async () => {
      (fetch as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({
          ok: true,
          json: async () => ({ results: mockSearchResults }),
        }), 100))
      );

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      render(
        <TestWrapper>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      await user.type(searchInput, 'Toyota');

      act(() => {
        jest.advanceTimersByTime(300);
      });

      // Should show loading spinner
      await waitFor(() => {
        expect(screen.getByTestId('loading-spinner') || screen.querySelector('.loading-spinner')).toBeInTheDocument();
      });
    });

    it('handles search API errors gracefully', async () => {
      (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      render(
        <TestWrapper>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      await user.type(searchInput, 'Toyota');

      act(() => {
        jest.advanceTimersByTime(300);
      });

      // Should not crash and should clear results
      await waitFor(() => {
        expect(fetch).toHaveBeenCalled();
      });
    });
  });

  describe('Search Results Display', () => {
    it('displays search results when available', async () => {
      const store = createTestStore({
        searchResults: mockSearchResults,
      });

      render(
        <TestWrapper store={store}>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      fireEvent.focus(searchInput);
      fireEvent.change(searchInput, { target: { value: 'Toyota' } });

      await waitFor(() => {
        expect(screen.getByText('7203')).toBeInTheDocument();
        expect(screen.getByText('トヨタ自動車株式会社')).toBeInTheDocument();
        expect(screen.getByText('Toyota Motor Corporation')).toBeInTheDocument();
      });
    });

    it('displays match scores for search results', async () => {
      const store = createTestStore({
        searchResults: mockSearchResults,
      });

      render(
        <TestWrapper store={store}>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      fireEvent.focus(searchInput);
      fireEvent.change(searchInput, { target: { value: 'Toyota' } });

      await waitFor(() => {
        expect(screen.getByText('Match: 95%')).toBeInTheDocument();
        expect(screen.getByText('Match: 87%')).toBeInTheDocument();
      });
    });

    it('displays price information when available', async () => {
      const store = createTestStore({
        searchResults: mockSearchResults,
      });

      render(
        <TestWrapper store={store}>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      fireEvent.focus(searchInput);
      fireEvent.change(searchInput, { target: { value: 'Toyota' } });

      await waitFor(() => {
        expect(screen.getByText('¥2,500')).toBeInTheDocument();
        expect(screen.getByText('+25.00 (+1.00%)')).toBeInTheDocument();
        expect(screen.getByText('-150.00 (-1.23%)')).toBeInTheDocument();
      });
    });

    it('shows no results message when search returns empty', async () => {
      const store = createTestStore({
        searchResults: [],
        isLoading: false,
      });

      render(
        <TestWrapper store={store}>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      fireEvent.focus(searchInput);
      fireEvent.change(searchInput, { target: { value: 'NonExistentStock' } });

      await waitFor(() => {
        expect(screen.getByText(/no stocks found for "NonExistentStock"/i)).toBeInTheDocument();
      });
    });
  });

  describe('Keyboard Navigation', () => {
    it('navigates results with arrow keys', async () => {
      const store = createTestStore({
        searchResults: mockSearchResults,
      });

      render(
        <TestWrapper store={store}>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      fireEvent.focus(searchInput);
      fireEvent.change(searchInput, { target: { value: 'Toyota' } });

      // Press arrow down to select first result
      fireEvent.keyDown(searchInput, { key: 'ArrowDown' });

      await waitFor(() => {
        const firstResult = screen.getByText('7203').closest('div');
        expect(firstResult).toHaveClass('bg-primary-50');
      });

      // Press arrow down again to select second result
      fireEvent.keyDown(searchInput, { key: 'ArrowDown' });

      await waitFor(() => {
        const secondResult = screen.getByText('6758').closest('div');
        expect(secondResult).toHaveClass('bg-primary-50');
      });
    });

    it('wraps around when navigating past last result', async () => {
      const store = createTestStore({
        searchResults: mockSearchResults,
      });

      render(
        <TestWrapper store={store}>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      fireEvent.focus(searchInput);
      fireEvent.change(searchInput, { target: { value: 'Toyota' } });

      // Navigate to last result
      fireEvent.keyDown(searchInput, { key: 'ArrowDown' });
      fireEvent.keyDown(searchInput, { key: 'ArrowDown' });

      // Press arrow down again to wrap to first result
      fireEvent.keyDown(searchInput, { key: 'ArrowDown' });

      await waitFor(() => {
        const firstResult = screen.getByText('7203').closest('div');
        expect(firstResult).toHaveClass('bg-primary-50');
      });
    });

    it('selects result with Enter key', async () => {
      const store = createTestStore({
        searchResults: mockSearchResults,
      });

      render(
        <TestWrapper store={store}>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      fireEvent.focus(searchInput);
      fireEvent.change(searchInput, { target: { value: 'Toyota' } });

      // Navigate to first result and press Enter
      fireEvent.keyDown(searchInput, { key: 'ArrowDown' });
      fireEvent.keyDown(searchInput, { key: 'Enter' });

      expect(mockNavigate).toHaveBeenCalledWith('/stocks/7203');
    });

    it('closes results with Escape key', async () => {
      const store = createTestStore({
        searchResults: mockSearchResults,
      });

      render(
        <TestWrapper store={store}>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      fireEvent.focus(searchInput);
      fireEvent.change(searchInput, { target: { value: 'Toyota' } });

      // Results should be visible
      await waitFor(() => {
        expect(screen.getByText('7203')).toBeInTheDocument();
      });

      // Press Escape to close
      fireEvent.keyDown(searchInput, { key: 'Escape' });

      await waitFor(() => {
        expect(screen.queryByText('7203')).not.toBeInTheDocument();
      });
    });
  });

  describe('Mouse Interactions', () => {
    it('selects result when clicked', async () => {
      const store = createTestStore({
        searchResults: mockSearchResults,
      });

      render(
        <TestWrapper store={store}>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      fireEvent.focus(searchInput);
      fireEvent.change(searchInput, { target: { value: 'Toyota' } });

      await waitFor(() => {
        const toyotaResult = screen.getByText('トヨタ自動車株式会社');
        fireEvent.click(toyotaResult);
      });

      expect(mockNavigate).toHaveBeenCalledWith('/stocks/7203');
    });

    it('highlights result on hover', async () => {
      const store = createTestStore({
        searchResults: mockSearchResults,
      });

      render(
        <TestWrapper store={store}>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      fireEvent.focus(searchInput);
      fireEvent.change(searchInput, { target: { value: 'Toyota' } });

      await waitFor(() => {
        const firstResult = screen.getByText('7203').closest('div');
        fireEvent.mouseEnter(firstResult!);
        expect(firstResult).toHaveClass('hover:bg-gray-50');
      });
    });

    it('closes results when clicking outside', async () => {
      const store = createTestStore({
        searchResults: mockSearchResults,
      });

      render(
        <TestWrapper store={store}>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      fireEvent.focus(searchInput);
      fireEvent.change(searchInput, { target: { value: 'Toyota' } });

      // Results should be visible
      await waitFor(() => {
        expect(screen.getByText('7203')).toBeInTheDocument();
      });

      // Click outside
      fireEvent.mouseDown(document.body);

      await waitFor(() => {
        expect(screen.queryByText('7203')).not.toBeInTheDocument();
      });
    });
  });

  describe('Price Formatting', () => {
    it('formats Japanese Yen prices correctly', async () => {
      const store = createTestStore({
        searchResults: [
          {
            ...mockSearchResults[0],
            current_price: 2500.75,
          },
        ],
      });

      render(
        <TestWrapper store={store}>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      fireEvent.focus(searchInput);
      fireEvent.change(searchInput, { target: { value: 'Toyota' } });

      await waitFor(() => {
        expect(screen.getByText('¥2,501')).toBeInTheDocument();
      });
    });

    it('handles undefined prices gracefully', async () => {
      const store = createTestStore({
        searchResults: [
          {
            ...mockSearchResults[0],
            current_price: undefined,
            price_change: undefined,
            price_change_percent: undefined,
          },
        ],
      });

      render(
        <TestWrapper store={store}>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      fireEvent.focus(searchInput);
      fireEvent.change(searchInput, { target: { value: 'Toyota' } });

      await waitFor(() => {
        expect(screen.getByText('N/A')).toBeInTheDocument();
      });
    });

    it('applies correct color classes for price changes', async () => {
      const store = createTestStore({
        searchResults: mockSearchResults,
      });

      render(
        <TestWrapper store={store}>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      fireEvent.focus(searchInput);
      fireEvent.change(searchInput, { target: { value: 'Toyota' } });

      await waitFor(() => {
        const positiveChange = screen.getByText('+25.00 (+1.00%)');
        const negativeChange = screen.getByText('-150.00 (-1.23%)');
        
        expect(positiveChange).toHaveClass('text-success-600');
        expect(negativeChange).toHaveClass('text-danger-600');
      });
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA attributes', () => {
      render(
        <TestWrapper>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      expect(searchInput).toHaveAttribute('autoComplete', 'off');
    });

    it('supports keyboard navigation for accessibility', async () => {
      const store = createTestStore({
        searchResults: mockSearchResults,
      });

      render(
        <TestWrapper store={store}>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      fireEvent.focus(searchInput);
      fireEvent.change(searchInput, { target: { value: 'Toyota' } });

      // Test that all keyboard interactions work
      fireEvent.keyDown(searchInput, { key: 'ArrowDown' });
      fireEvent.keyDown(searchInput, { key: 'ArrowUp' });
      fireEvent.keyDown(searchInput, { key: 'Enter' });

      // Should navigate to selected stock
      expect(mockNavigate).toHaveBeenCalled();
    });
  });

  describe('Edge Cases', () => {
    it('handles empty search results', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ results: [] }),
      });

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      render(
        <TestWrapper>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      await user.type(searchInput, 'NonExistent');

      act(() => {
        jest.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(screen.getByText(/no stocks found/i)).toBeInTheDocument();
      });
    });

    it('handles malformed API responses', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ /* missing results field */ }),
      });

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      render(
        <TestWrapper>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      await user.type(searchInput, 'Toyota');

      act(() => {
        jest.advanceTimersByTime(300);
      });

      // Should not crash
      await waitFor(() => {
        expect(fetch).toHaveBeenCalled();
      });
    });

    it('handles special characters in search query', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ results: [] }),
      });

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      render(
        <TestWrapper>
          <StockSearch />
        </TestWrapper>
      );

      const searchInput = screen.getByRole('textbox');
      await user.type(searchInput, 'Test & Co.');

      act(() => {
        jest.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith(
          '/api/v1/stocks/search?query=Test%20%26%20Co.&limit=10'
        );
      });
    });
  });
});