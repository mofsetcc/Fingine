/**
 * Tests for Dashboard component
 */

import { configureStore } from '@reduxjs/toolkit';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import Dashboard from '../../pages/Dashboard';
import stocksReducer from '../../store/slices/stocksSlice';

// Mock fetch
global.fetch = jest.fn();

// Mock components
jest.mock('../../components/StockSearch', () => {
  return function MockStockSearch() {
    return <div data-testid="stock-search">Stock Search Component</div>;
  };
});

jest.mock('../../components/MarketIndicesDisplay', () => {
  return function MockMarketIndicesDisplay({ indices, isLoading }: any) {
    return (
      <div data-testid="market-indices">
        {isLoading ? 'Loading...' : `${indices.length} indices`}
      </div>
    );
  };
});

jest.mock('../../components/HotStocksSection', () => {
  return function MockHotStocksSection({ hotStocks, isLoading }: any) {
    return (
      <div data-testid="hot-stocks">
        {isLoading ? 'Loading...' : `${hotStocks.length} hot stocks`}
      </div>
    );
  };
});

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

describe('Dashboard Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (fetch as jest.Mock).mockClear();
  });

  it('renders dashboard with all main sections', () => {
    renderWithProviders(<Dashboard />);

    expect(screen.getByText('Market Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Real-time Japanese stock market insights powered by AI')).toBeInTheDocument();
    expect(screen.getByTestId('stock-search')).toBeInTheDocument();
    expect(screen.getByTestId('market-indices')).toBeInTheDocument();
    expect(screen.getByTestId('hot-stocks')).toBeInTheDocument();
  });

  it('shows refresh button', () => {
    renderWithProviders(<Dashboard />);

    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    expect(refreshButton).toBeInTheDocument();
  });

  it('fetches market data on mount', async () => {
    const mockIndices = [
      {
        name: 'Nikkei 225',
        symbol: 'N225',
        value: 30000,
        change: 100,
        change_percent: 0.33,
        updated_at: new Date().toISOString(),
      },
    ];

    const mockHotStocks = {
      gainers: [
        {
          ticker: '7203',
          company_name: 'Toyota',
          price: 2000,
          change: 50,
          change_percent: 2.5,
          volume: 1000000,
        },
      ],
      losers: [],
      most_traded: [],
    };

    (fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockIndices),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockHotStocks),
      });

    renderWithProviders(<Dashboard />);

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/v1/stocks/market/indices');
      expect(fetch).toHaveBeenCalledWith('/api/v1/stocks/market/hot-stocks');
    });
  });

  it('handles fetch errors gracefully', async () => {
    (fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

    renderWithProviders(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('Failed to fetch market data')).toBeInTheDocument();
    });
  });

  it('shows loading state', () => {
    renderWithProviders(<Dashboard />, { isLoading: true });

    expect(screen.getByTestId('market-indices')).toHaveTextContent('Loading...');
    expect(screen.getByTestId('hot-stocks')).toHaveTextContent('Loading...');
  });

  it('shows error state', () => {
    renderWithProviders(<Dashboard />, { error: 'Test error message' });

    expect(screen.getByText('Test error message')).toBeInTheDocument();
  });

  it('refreshes data when refresh button is clicked', async () => {
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    });

    renderWithProviders(<Dashboard />);

    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    fireEvent.click(refreshButton);

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledTimes(4); // 2 initial calls + 2 refresh calls
    });
  });

  it('disables refresh button when loading', () => {
    renderWithProviders(<Dashboard />, { isLoading: true });

    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    expect(refreshButton).toBeDisabled();
  });

  it('shows last updated time', () => {
    renderWithProviders(<Dashboard />);

    expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
  });

  it('has responsive design classes', () => {
    const { container } = renderWithProviders(<Dashboard />);

    // Check for responsive grid classes
    const gridElements = container.querySelectorAll('.grid');
    expect(gridElements.length).toBeGreaterThan(0);

    // Check for animation classes
    const animatedElements = container.querySelectorAll('.animate-fade-in');
    expect(animatedElements.length).toBeGreaterThan(0);
  });

  it('sets up auto-refresh interval', () => {
    jest.useFakeTimers();
    
    renderWithProviders(<Dashboard />);

    // Fast-forward time to trigger interval
    jest.advanceTimersByTime(5 * 60 * 1000); // 5 minutes

    jest.useRealTimers();
  });

  it('cleans up interval on unmount', () => {
    jest.useFakeTimers();
    const clearIntervalSpy = jest.spyOn(global, 'clearInterval');

    const { unmount } = renderWithProviders(<Dashboard />);
    unmount();

    expect(clearIntervalSpy).toHaveBeenCalled();

    jest.useRealTimers();
    clearIntervalSpy.mockRestore();
  });
});