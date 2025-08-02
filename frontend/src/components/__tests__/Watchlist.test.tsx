import { configureStore } from '@reduxjs/toolkit';
import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';

import watchlistSlice from '../../store/slices/watchlistSlice';
import { WatchlistStockWithPrice } from '../../types/watchlist';
import Watchlist from '../Watchlist';

// Mock fetch
global.fetch = jest.fn();

// Mock store setup
const createMockStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      watchlist: watchlistSlice,
    },
    preloadedState: {
      watchlist: {
        stocks: [],
        isLoading: false,
        error: null,
        lastUpdated: null,
        ...initialState,
      },
    },
  });
};

// Sample watchlist stock data
const sampleWatchlistStock: WatchlistStockWithPrice = {
  id: null,
  user_id: 'user-123',
  ticker: '7203',
  notes: 'Great automotive company',
  created_at: '2024-01-15T10:00:00Z',
  updated_at: '2024-01-15T10:00:00Z',
  stock: {
    ticker: '7203',
    company_name_jp: 'トヨタ自動車株式会社',
    company_name_en: 'Toyota Motor Corporation',
    sector_jp: '輸送用機器',
    industry_jp: '自動車',
    description: 'Leading automotive manufacturer',
    logo_url: undefined,
    listing_date: '1949-05-16',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  current_price: 2520.0,
  price_change: 20.0,
  price_change_percent: 0.8,
  volume_today: 1000000,
  last_updated: '2024-01-15',
  price_alert_triggered: false,
  volume_alert_triggered: false,
};

describe('Watchlist Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.setItem('token', 'test-token');
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('renders empty watchlist message when no stocks', () => {
    const store = createMockStore();
    
    render(
      <Provider store={store}>
        <Watchlist />
      </Provider>
    );

    expect(screen.getByText('Your watchlist is empty')).toBeInTheDocument();
    expect(screen.getByText('Add stocks to track their performance and get real-time updates.')).toBeInTheDocument();
    expect(screen.getByText('Add Your First Stock')).toBeInTheDocument();
  });

  it('renders watchlist with stocks', () => {
    const store = createMockStore({
      stocks: [sampleWatchlistStock],
      lastUpdated: '2024-01-15T10:00:00Z',
    });
    
    render(
      <Provider store={store}>
        <Watchlist />
      </Provider>
    );

    expect(screen.getByText('My Watchlist')).toBeInTheDocument();
    expect(screen.getByText('(1 stocks)')).toBeInTheDocument();
    expect(screen.getByText('7203')).toBeInTheDocument();
    expect(screen.getByText('トヨタ自動車株式会社')).toBeInTheDocument();
    expect(screen.getByText('¥2,520')).toBeInTheDocument();
    expect(screen.getByText('+¥20.00 (+0.80%)')).toBeInTheDocument();
  });

  it('displays loading state', () => {
    const store = createMockStore({
      isLoading: true,
    });
    
    render(
      <Provider store={store}>
        <Watchlist />
      </Provider>
    );

    expect(screen.getByText('Refreshing...')).toBeInTheDocument();
  });

  it('displays error message', () => {
    const store = createMockStore({
      error: 'Failed to fetch watchlist',
    });
    
    render(
      <Provider store={store}>
        <Watchlist />
      </Provider>
    );

    expect(screen.getByText('Failed to fetch watchlist')).toBeInTheDocument();
  });

  it('opens add stock modal when add button is clicked', () => {
    const store = createMockStore();
    
    render(
      <Provider store={store}>
        <Watchlist />
      </Provider>
    );

    fireEvent.click(screen.getByText('Add Stock'));
    expect(screen.getByText('Add Stock to Watchlist')).toBeInTheDocument();
  });

  it('calculates total value and change correctly', () => {
    const stocks = [
      { ...sampleWatchlistStock, current_price: 2520.0, price_change: 20.0 },
      { 
        ...sampleWatchlistStock, 
        ticker: '6758', 
        current_price: 1500.0, 
        price_change: -10.0 
      },
    ];
    
    const store = createMockStore({ stocks });
    
    render(
      <Provider store={store}>
        <Watchlist />
      </Provider>
    );

    expect(screen.getByText('¥4,020')).toBeInTheDocument(); // Total value
    expect(screen.getByText('+¥10.00 (0.25%)')).toBeInTheDocument(); // Total change
  });

  it('handles refresh button click', async () => {
    const mockFetch = fetch as jest.MockedFunction<typeof fetch>;
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [sampleWatchlistStock],
    } as Response);

    const store = createMockStore();
    
    render(
      <Provider store={store}>
        <Watchlist />
      </Provider>
    );

    fireEvent.click(screen.getByText('Refresh'));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/v1/watchlist', {
        headers: {
          'Authorization': 'Bearer test-token',
        },
      });
    });
  });

  it('opens edit modal when edit button is clicked', () => {
    const store = createMockStore({
      stocks: [sampleWatchlistStock],
    });
    
    render(
      <Provider store={store}>
        <Watchlist />
      </Provider>
    );

    fireEvent.click(screen.getByTitle('Edit notes'));
    expect(screen.getByText('Edit 7203')).toBeInTheDocument();
  });

  it('confirms before removing stock', () => {
    const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
    const mockFetch = fetch as jest.MockedFunction<typeof fetch>;
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: 'Stock removed from watchlist' }),
    } as Response);

    const store = createMockStore({
      stocks: [sampleWatchlistStock],
    });
    
    render(
      <Provider store={store}>
        <Watchlist />
      </Provider>
    );

    fireEvent.click(screen.getByTitle('Remove from watchlist'));

    expect(confirmSpy).toHaveBeenCalledWith('Are you sure you want to remove 7203 from your watchlist?');
    confirmSpy.mockRestore();
  });

  it('displays last updated timestamp', () => {
    const store = createMockStore({
      stocks: [sampleWatchlistStock],
      lastUpdated: '2024-01-15T10:30:00Z',
    });
    
    render(
      <Provider store={store}>
        <Watchlist />
      </Provider>
    );

    expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
  });

  it('handles view analysis button click', () => {
    // Mock window.location.href
    delete (window as any).location;
    window.location = { href: '' } as any;

    const store = createMockStore({
      stocks: [sampleWatchlistStock],
    });
    
    render(
      <Provider store={store}>
        <Watchlist />
      </Provider>
    );

    fireEvent.click(screen.getByText('View Analysis'));
    expect(window.location.href).toBe('/stocks/7203');
  });

  it('displays alert indicators when alerts are triggered', () => {
    const stockWithAlerts = {
      ...sampleWatchlistStock,
      price_alert_triggered: true,
      volume_alert_triggered: true,
    };

    const store = createMockStore({
      stocks: [stockWithAlerts],
    });
    
    render(
      <Provider store={store}>
        <Watchlist />
      </Provider>
    );

    expect(screen.getByText('Price Alert')).toBeInTheDocument();
    expect(screen.getByText('Volume Alert')).toBeInTheDocument();
  });

  it('formats large numbers correctly', () => {
    const stockWithLargeVolume = {
      ...sampleWatchlistStock,
      volume_today: 5500000, // 5.5M
    };

    const store = createMockStore({
      stocks: [stockWithLargeVolume],
    });
    
    render(
      <Provider store={store}>
        <Watchlist />
      </Provider>
    );

    expect(screen.getByText('5.5M')).toBeInTheDocument();
  });

  it('handles missing price data gracefully', () => {
    const stockWithoutPrice = {
      ...sampleWatchlistStock,
      current_price: null,
      price_change: null,
      price_change_percent: null,
      volume_today: null,
    };

    const store = createMockStore({
      stocks: [stockWithoutPrice],
    });
    
    render(
      <Provider store={store}>
        <Watchlist />
      </Provider>
    );

    expect(screen.getAllByText('N/A')).toHaveLength(3); // Price, change, volume
  });
});