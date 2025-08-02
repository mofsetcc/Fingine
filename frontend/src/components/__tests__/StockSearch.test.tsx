/**
 * Tests for StockSearch component
 */

import { configureStore } from '@reduxjs/toolkit';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import stocksReducer from '../../store/slices/stocksSlice';
import StockSearch from '../StockSearch';

// Mock fetch
global.fetch = jest.fn();

// Mock react-router-dom
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

const createTestStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      stocks: stocksReducer,
    },
    preloadedState: {
      stocks: {
        searchResults: [],
        selectedStock: null,
        watchlist: [],
        marketIndices: [],
        hotStocks: [],
        isLoading: false,
        error: null,
        ...initialState,
      },
    },
  });
};

const renderWithProviders = (component: React.ReactElement, initialState = {}) => {
  const store = createTestStore(initialState);
  return render(
    <Provider store={store}>
      <BrowserRouter>
        {component}
      </BrowserRouter>
    </Provider>
  );
};

const mockSearchResults = [
  {
    ticker: '7203',
    company_name_jp: 'トヨタ自動車',
    company_name_en: 'Toyota Motor Corporation',
    sector_jp: '輸送用機器',
    industry_jp: '自動車',
    match_score: 0.95,
    current_price: 2000,
    price_change: 50,
    price_change_percent: 2.5,
  },
  {
    ticker: '6758',
    company_name_jp: 'ソニーグループ',
    company_name_en: 'Sony Group Corporation',
    sector_jp: '電気機器',
    industry_jp: 'AV機器',
    match_score: 0.85,
    current_price: 12000,
    price_change: -100,
    price_change_percent: -0.83,
  },
];

describe('StockSearch Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (fetch as jest.Mock).mockClear();
    mockNavigate.mockClear();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('renders search input with placeholder', () => {
    renderWithProviders(<StockSearch />);

    const searchInput = screen.getByPlaceholderText(/search stocks by ticker or company name/i);
    expect(searchInput).toBeInTheDocument();
  });

  it('shows search tips when input is empty', () => {
    renderWithProviders(<StockSearch />);

    expect(screen.getByText('💡 Search tips:')).toBeInTheDocument();
    expect(screen.getByText(/Use 4-digit ticker symbols/)).toBeInTheDocument();
  });

  it('performs search with debouncing', async () => {
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ results: mockSearchResults }),
    });

    renderWithProviders(<StockSearch />);

    const searchInput = screen.getByPlaceholderText(/search stocks by ticker or company name/i);
    
    await userEvent.type(searchInput, 'Toyota');

    // Fast-forward past debounce delay
    act(() => {
      jest.advanceTimersByTime(300);
    });

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/v1/stocks/search?query=Toyota&limit=10');
    });
  });

  it('shows loading spinner during search', async () => {
    (fetch as jest.Mock).mockImplementation(() => new Promise(() => {})); // Never resolves

    renderWithProviders(<StockSearch />);

    const searchInput = screen.getByPlaceholderText(/search stocks by ticker or company name/i);
    await userEvent.type(searchInput, 'Toyota');

    act(() => {
      jest.advanceTimersByTime(300);
    });

    await waitFor(() => {
      expect(screen.getByRole('status')).toBeInTheDocument(); // Loading spinner
    });
  });

  it('displays search results', async () => {
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ results: mockSearchResults }),
    });

    renderWithProviders(<StockSearch />);

    const searchInput = screen.getByPlaceholderText(/search stocks by ticker or company name/i);
    await userEvent.type(searchInput, 'Toyota');

    act(() => {
      jest.advanceTimersByTime(300);
    });

    await waitFor(() => {
      expect(screen.getByText('7203')).toBeInTheDocument();
      expect(screen.getByText('トヨタ自動車')).toBeInTheDocument();
      expect(screen.getByText('Toyota Motor Corporation')).toBeInTheDocument();
    });
  });

  it('shows match scores for results', async () => {
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ results: mockSearchResults }),
    });

    renderWithProviders(<StockSearch />);

    const searchInput = screen.getByPlaceholderText(/search stocks by ticker or company name/i);
    await userEvent.type(searchInput, 'Toyota');

    act(() => {
      jest.advanceTimersByTime(300);
    });

    await waitFor(() => {
      expect(screen.getByText('Match: 95%')).toBeInTheDocument();
      expect(screen.getByText('Match: 85%')).toBeInTheDocument();
    });
  });

  it('formats prices and changes correctly', async () => {
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ results: mockSearchResults }),
    });

    renderWithProviders(<StockSearch />);

    const searchInput = screen.getByPlaceholderText(/search stocks by ticker or company name/i);
    await userEvent.type(searchInput, 'Toyota');

    act(() => {
      jest.advanceTimersByTime(300);
    });

    await waitFor(() => {
      expect(screen.getByText('¥2,000')).toBeInTheDocument();
      expect(screen.getByText('+50.00 (+2.50%)')).toBeInTheDocument();
      expect(screen.getByText('¥12,000')).toBeInTheDocument();
      expect(screen.getByText('-100.00 (-0.83%)')).toBeInTheDocument();
    });
  });

  it('navigates to stock page when result is clicked', async () => {
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ results: mockSearchResults }),
    });

    renderWithProviders(<StockSearch />);

    const searchInput = screen.getByPlaceholderText(/search stocks by ticker or company name/i);
    await userEvent.type(searchInput, 'Toyota');

    act(() => {
      jest.advanceTimersByTime(300);
    });

    await waitFor(() => {
      const toyotaResult = screen.getByText('トヨタ自動車');
      fireEvent.click(toyotaResult.closest('div')!);
    });

    expect(mockNavigate).toHaveBeenCalledWith('/stocks/7203');
  });

  it('handles keyboard navigation', async () => {
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ results: mockSearchResults }),
    });

    renderWithProviders(<StockSearch />);

    const searchInput = screen.getByPlaceholderText(/search stocks by ticker or company name/i);
    await userEvent.type(searchInput, 'Toyota');

    act(() => {
      jest.advanceTimersByTime(300);
    });

    await waitFor(() => {
      expect(screen.getByText('7203')).toBeInTheDocument();
    });

    // Test arrow down navigation
    fireEvent.keyDown(searchInput, { key: 'ArrowDown' });
    fireEvent.keyDown(searchInput, { key: 'ArrowDown' });
    
    // Test Enter key selection
    fireEvent.keyDown(searchInput, { key: 'Enter' });

    expect(mockNavigate).toHaveBeenCalledWith('/stocks/6758');
  });

  it('handles Escape key to close results', async () => {
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ results: mockSearchResults }),
    });

    renderWithProviders(<StockSearch />);

    const searchInput = screen.getByPlaceholderText(/search stocks by ticker or company name/i);
    await userEvent.type(searchInput, 'Toyota');

    act(() => {
      jest.advanceTimersByTime(300);
    });

    await waitFor(() => {
      expect(screen.getByText('7203')).toBeInTheDocument();
    });

    fireEvent.keyDown(searchInput, { key: 'Escape' });

    await waitFor(() => {
      expect(screen.queryByText('7203')).not.toBeInTheDocument();
    });
  });

  it('closes results when clicking outside', async () => {
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ results: mockSearchResults }),
    });

    renderWithProviders(<StockSearch />);

    const searchInput = screen.getByPlaceholderText(/search stocks by ticker or company name/i);
    await userEvent.type(searchInput, 'Toyota');

    act(() => {
      jest.advanceTimersByTime(300);
    });

    await waitFor(() => {
      expect(screen.getByText('7203')).toBeInTheDocument();
    });

    fireEvent.mouseDown(document.body);

    await waitFor(() => {
      expect(screen.queryByText('7203')).not.toBeInTheDocument();
    });
  });

  it('shows no results message when search returns empty', async () => {
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ results: [] }),
    });

    renderWithProviders(<StockSearch />);

    const searchInput = screen.getByPlaceholderText(/search stocks by ticker or company name/i);
    await userEvent.type(searchInput, 'NonExistent');

    act(() => {
      jest.advanceTimersByTime(300);
    });

    await waitFor(() => {
      expect(screen.getByText('No stocks found for "NonExistent"')).toBeInTheDocument();
    });
  });

  it('does not search for queries shorter than 2 characters', async () => {
    renderWithProviders(<StockSearch />);

    const searchInput = screen.getByPlaceholderText(/search stocks by ticker or company name/i);
    await userEvent.type(searchInput, 'T');

    act(() => {
      jest.advanceTimersByTime(300);
    });

    expect(fetch).not.toHaveBeenCalled();
  });

  it('handles search API errors gracefully', async () => {
    (fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

    renderWithProviders(<StockSearch />);

    const searchInput = screen.getByPlaceholderText(/search stocks by ticker or company name/i);
    await userEvent.type(searchInput, 'Toyota');

    act(() => {
      jest.advanceTimersByTime(300);
    });

    await waitFor(() => {
      expect(fetch).toHaveBeenCalled();
    });

    // Should not crash and should clear results
    expect(screen.queryByText('7203')).not.toBeInTheDocument();
  });

  it('clears results when query becomes too short', async () => {
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ results: mockSearchResults }),
    });

    renderWithProviders(<StockSearch />);

    const searchInput = screen.getByPlaceholderText(/search stocks by ticker or company name/i);
    await userEvent.type(searchInput, 'Toyota');

    act(() => {
      jest.advanceTimersByTime(300);
    });

    await waitFor(() => {
      expect(screen.getByText('7203')).toBeInTheDocument();
    });

    // Clear input to make it shorter than 2 characters
    await userEvent.clear(searchInput);
    await userEvent.type(searchInput, 'T');

    expect(screen.queryByText('7203')).not.toBeInTheDocument();
  });
});