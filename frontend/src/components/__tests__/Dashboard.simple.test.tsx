/**
 * Simple tests for Dashboard component
 */

import { configureStore } from '@reduxjs/toolkit';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import Dashboard from '../../pages/Dashboard';
import stocksReducer from '../../store/slices/stocksSlice';

// Mock fetch
global.fetch = jest.fn();

// Mock components to avoid complex dependencies
jest.mock('../../components/StockSearch', () => {
  return function MockStockSearch() {
    return <div data-testid="stock-search">Stock Search Component</div>;
  };
});

jest.mock('../../components/MarketIndicesDisplay', () => {
  return function MockMarketIndicesDisplay() {
    return <div data-testid="market-indices">Market Indices Component</div>;
  };
});

jest.mock('../../components/HotStocksSection', () => {
  return function MockHotStocksSection() {
    return <div data-testid="hot-stocks">Hot Stocks Component</div>;
  };
});

const createTestStore = () => {
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
      },
    },
  });
};

const renderWithProviders = (component: React.ReactElement) => {
  const store = createTestStore();
  return render(
    <Provider store={store}>
      <BrowserRouter>
        {component}
      </BrowserRouter>
    </Provider>
  );
};

describe('Dashboard Component - Simple Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    });
  });

  it('renders dashboard title', () => {
    renderWithProviders(<Dashboard />);
    expect(screen.getByText('Market Dashboard')).toBeInTheDocument();
  });

  it('renders dashboard subtitle', () => {
    renderWithProviders(<Dashboard />);
    expect(screen.getByText('Real-time Japanese stock market insights powered by AI')).toBeInTheDocument();
  });

  it('renders all main components', () => {
    renderWithProviders(<Dashboard />);
    
    expect(screen.getByTestId('stock-search')).toBeInTheDocument();
    expect(screen.getByTestId('market-indices')).toBeInTheDocument();
    expect(screen.getByTestId('hot-stocks')).toBeInTheDocument();
  });

  it('renders refresh button', () => {
    renderWithProviders(<Dashboard />);
    expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
  });

  it('has proper section headings', () => {
    renderWithProviders(<Dashboard />);
    
    expect(screen.getByText('Stock Search')).toBeInTheDocument();
    expect(screen.getByText('Market Indices')).toBeInTheDocument();
    expect(screen.getByText('Hot Stocks Today')).toBeInTheDocument();
  });
});