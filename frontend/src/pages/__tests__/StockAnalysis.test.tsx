/**
 * StockAnalysis Component Tests
 * Tests for the main stock analysis page with AI analysis, charts, and financial data
 */

import { configureStore } from '@reduxjs/toolkit';
import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';

import analysisReducer from '../../store/slices/analysisSlice';
import stocksReducer from '../../store/slices/stocksSlice';
import { AIAnalysisResult } from '../../types/ai-analysis';
import { StockDetail } from '../../types/stock';
import StockAnalysis from '../StockAnalysis';

// Mock fetch globally
global.fetch = jest.fn();

// Mock react-router-dom
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useParams: () => ({ ticker: '7203' }),
  useNavigate: () => mockNavigate,
}));

// Mock TradingView
Object.defineProperty(window, 'TradingView', {
  value: {
    widget: jest.fn().mockImplementation(() => ({
      onChartReady: jest.fn(),
      remove: jest.fn(),
    })),
  },
  writable: true,
});

// Test data
const mockStockData: StockDetail = {
  id: '1',
  ticker: '7203',
  company_name_jp: 'トヨタ自動車株式会社',
  company_name_en: 'Toyota Motor Corporation',
  sector_jp: '輸送用機器',
  industry_jp: '自動車',
  description: 'Leading automotive manufacturer',
  logo_url: 'https://example.com/toyota-logo.png',
  listing_date: '1949-05-16',
  is_active: true,
  current_price: 2500,
  price_change: 50,
  price_change_percent: 2.04,
  volume_today: 15000000,
  market_cap: 35000000000000,
  pe_ratio: 12.5,
  pb_ratio: 1.2,
  dividend_yield: 0.025,
  week_52_high: 2800,
  week_52_low: 1800,
  avg_volume_30d: 12000000,
  beta: 0.8,
  last_updated: '2024-01-15T15:00:00Z',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-15T15:00:00Z',
};

const mockAnalysisData: AIAnalysisResult = {
  ticker: '7203',
  analysisType: 'short_term',
  rating: 'Bullish',
  confidence: 0.75,
  keyFactors: [
    'Strong quarterly earnings growth',
    'Positive technical momentum',
    'Favorable market sentiment'
  ],
  priceTargetRange: {
    min: 2400,
    max: 2700
  },
  riskFactors: [
    'Global supply chain disruptions',
    'Rising raw material costs'
  ],
  reasoning: 'Toyota shows strong fundamentals with consistent earnings growth and positive technical indicators.',
  generatedAt: '2024-01-15T10:00:00Z',
  modelVersion: 'gemini-pro-1.0'
};

// Helper function to create test store
const createTestStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      stocks: stocksReducer,
      analysis: analysisReducer,
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
        ...initialState.stocks,
      },
      analysis: {
        currentAnalysis: null,
        analysisHistory: [],
        isLoading: false,
        error: null,
        ...initialState.analysis,
      },
    },
  });
};

// Helper function to render component with providers
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

describe('StockAnalysis Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (fetch as jest.Mock).mockClear();
  });

  describe('Loading States', () => {
    it('displays loading spinner when fetching stock data', () => {
      renderWithProviders(<StockAnalysis />, {
        stocks: { isLoading: true }
      });

      expect(screen.getByRole('generic', { name: /loading/i })).toBeInTheDocument();
    });

    it('displays loading state for AI analysis', () => {
      renderWithProviders(<StockAnalysis />, {
        stocks: { selectedStock: mockStockData },
        analysis: { isLoading: true }
      });

      expect(screen.getByText(/generating ai analysis/i)).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('displays error message when stock fetch fails', () => {
      const errorMessage = 'Failed to fetch stock data';
      renderWithProviders(<StockAnalysis />, {
        stocks: { error: errorMessage }
      });

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    it('displays retry button on error', () => {
      renderWithProviders(<StockAnalysis />, {
        stocks: { error: 'Network error' }
      });

      const retryButton = screen.getByRole('button', { name: /try again/i });
      expect(retryButton).toBeInTheDocument();
    });
  });

  describe('Stock Data Display', () => {
    beforeEach(() => {
      (fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockStockData,
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            analysis: {
              rating: 'Bullish',
              confidence: 0.75,
              key_factors: mockAnalysisData.keyFactors,
              price_target_range: mockAnalysisData.priceTargetRange,
              risk_factors: mockAnalysisData.riskFactors,
              reasoning: mockAnalysisData.reasoning,
              model_version: 'gemini-pro-1.0'
            }
          }),
        });
    });

    it('displays stock header with company information', async () => {
      renderWithProviders(<StockAnalysis />);

      await waitFor(() => {
        expect(screen.getByText('7203')).toBeInTheDocument();
        expect(screen.getByText('トヨタ自動車株式会社')).toBeInTheDocument();
        expect(screen.getByText('Toyota Motor Corporation')).toBeInTheDocument();
      });
    });

    it('displays current price and change information', async () => {
      renderWithProviders(<StockAnalysis />);

      await waitFor(() => {
        expect(screen.getByText('¥2,500')).toBeInTheDocument();
        expect(screen.getByText('+¥50.00 (+2.04%)')).toBeInTheDocument();
      });
    });

    it('displays key financial metrics', async () => {
      renderWithProviders(<StockAnalysis />);

      await waitFor(() => {
        expect(screen.getByText('12.50')).toBeInTheDocument(); // P/E Ratio
        expect(screen.getByText('2.50%')).toBeInTheDocument(); // Dividend Yield
      });
    });
  });

  describe('AI Analysis Display', () => {
    beforeEach(() => {
      (fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockStockData,
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            analysis: {
              rating: 'Bullish',
              confidence: 0.75,
              key_factors: mockAnalysisData.keyFactors,
              price_target_range: mockAnalysisData.priceTargetRange,
              risk_factors: mockAnalysisData.riskFactors,
              reasoning: mockAnalysisData.reasoning,
              model_version: 'gemini-pro-1.0'
            }
          }),
        });
    });

    it('displays analysis type buttons', async () => {
      renderWithProviders(<StockAnalysis />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /short-term/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /mid-term/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /long-term/i })).toBeInTheDocument();
      });
    });

    it('switches analysis type when button is clicked', async () => {
      renderWithProviders(<StockAnalysis />);

      await waitFor(() => {
        const midTermButton = screen.getByRole('button', { name: /mid-term/i });
        fireEvent.click(midTermButton);
      });

      // Should trigger new API call for mid-term analysis
      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith('/api/v1/analysis/7203/mid_term');
      });
    });

    it('displays analysis rating and confidence', async () => {
      renderWithProviders(<StockAnalysis />);

      await waitFor(() => {
        expect(screen.getByText('Bullish')).toBeInTheDocument();
        expect(screen.getByText('75%')).toBeInTheDocument();
      });
    });

    it('displays key factors and risk factors', async () => {
      renderWithProviders(<StockAnalysis />);

      await waitFor(() => {
        expect(screen.getByText('Strong quarterly earnings growth')).toBeInTheDocument();
        expect(screen.getByText('Global supply chain disruptions')).toBeInTheDocument();
      });
    });
  });

  describe('Chart Integration', () => {
    beforeEach(() => {
      (fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockStockData,
      });
    });

    it('displays chart period buttons', async () => {
      renderWithProviders(<StockAnalysis />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: '1D' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: '1W' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: '1M' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: '3M' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: '6M' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: '1Y' })).toBeInTheDocument();
      });
    });

    it('changes chart period when button is clicked', async () => {
      renderWithProviders(<StockAnalysis />);

      await waitFor(() => {
        const weekButton = screen.getByRole('button', { name: '1W' });
        fireEvent.click(weekButton);
      });

      // Chart should update with new period
      expect(weekButton).toHaveClass('bg-primary-600');
    });
  });

  describe('Financial Data Section', () => {
    beforeEach(() => {
      (fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockStockData,
      });
    });

    it('displays financial data section', async () => {
      renderWithProviders(<StockAnalysis />);

      await waitFor(() => {
        expect(screen.getByText('Financial Data & Metrics')).toBeInTheDocument();
      });
    });

    it('toggles financial details when button is clicked', async () => {
      renderWithProviders(<StockAnalysis />);

      await waitFor(() => {
        const toggleButton = screen.getByRole('button', { name: /show details/i });
        fireEvent.click(toggleButton);
      });

      expect(screen.getByRole('button', { name: /hide details/i })).toBeInTheDocument();
    });
  });

  describe('News and Sentiment Section', () => {
    beforeEach(() => {
      (fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockStockData,
      });
    });

    it('displays news and sentiment section', async () => {
      renderWithProviders(<StockAnalysis />);

      await waitFor(() => {
        expect(screen.getByText('News & Market Sentiment')).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    beforeEach(() => {
      (fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockStockData,
      });
    });

    it('has proper heading hierarchy', async () => {
      renderWithProviders(<StockAnalysis />);

      await waitFor(() => {
        const headings = screen.getAllByRole('heading');
        expect(headings.length).toBeGreaterThan(0);
      });
    });

    it('has accessible button labels', async () => {
      renderWithProviders(<StockAnalysis />);

      await waitFor(() => {
        const buttons = screen.getAllByRole('button');
        buttons.forEach(button => {
          expect(button).toHaveAccessibleName();
        });
      });
    });
  });

  describe('Responsive Design', () => {
    beforeEach(() => {
      (fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockStockData,
      });
    });

    it('applies responsive classes for mobile layout', async () => {
      renderWithProviders(<StockAnalysis />);

      await waitFor(() => {
        const container = screen.getByRole('main') || document.querySelector('.max-w-7xl');
        expect(container).toHaveClass('max-w-7xl');
      });
    });
  });

  describe('API Integration', () => {
    it('fetches stock data on component mount', async () => {
      (fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockStockData,
      });

      renderWithProviders(<StockAnalysis />);

      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith('/api/v1/stocks/7203');
      });
    });

    it('fetches AI analysis on component mount', async () => {
      (fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockStockData,
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ analysis: mockAnalysisData }),
        });

      renderWithProviders(<StockAnalysis />);

      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith('/api/v1/analysis/7203/short_term');
      });
    });

    it('handles API errors gracefully', async () => {
      (fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      renderWithProviders(<StockAnalysis />);

      await waitFor(() => {
        expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
      });
    });
  });

  describe('Performance', () => {
    it('does not re-fetch data unnecessarily', async () => {
      (fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockStockData,
      });

      const { rerender } = renderWithProviders(<StockAnalysis />);

      await waitFor(() => {
        expect(fetch).toHaveBeenCalledTimes(2); // Stock data + analysis
      });

      // Re-render without changing ticker
      rerender(
        <Provider store={createTestStore()}>
          <BrowserRouter>
            <StockAnalysis />
          </BrowserRouter>
        </Provider>
      );

      // Should not trigger additional API calls
      expect(fetch).toHaveBeenCalledTimes(2);
    });
  });
});

describe('StockAnalysis Integration Tests', () => {
  it('completes full user workflow', async () => {
    // Mock all API responses
    (fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockStockData,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          analysis: {
            rating: 'Bullish',
            confidence: 0.75,
            key_factors: mockAnalysisData.keyFactors,
            price_target_range: mockAnalysisData.priceTargetRange,
            risk_factors: mockAnalysisData.riskFactors,
            reasoning: mockAnalysisData.reasoning,
            model_version: 'gemini-pro-1.0'
          }
        }),
      });

    renderWithProviders(<StockAnalysis />);

    // 1. Page loads with stock data
    await waitFor(() => {
      expect(screen.getByText('7203')).toBeInTheDocument();
      expect(screen.getByText('トヨタ自動車株式会社')).toBeInTheDocument();
    });

    // 2. AI analysis loads
    await waitFor(() => {
      expect(screen.getByText('Bullish')).toBeInTheDocument();
      expect(screen.getByText('75%')).toBeInTheDocument();
    });

    // 3. User switches to mid-term analysis
    const midTermButton = screen.getByRole('button', { name: /mid-term/i });
    fireEvent.click(midTermButton);

    // 4. User changes chart period
    const weekButton = screen.getByRole('button', { name: '1W' });
    fireEvent.click(weekButton);

    // 5. User toggles financial details
    const detailsButton = screen.getByRole('button', { name: /show details/i });
    fireEvent.click(detailsButton);

    expect(screen.getByRole('button', { name: /hide details/i })).toBeInTheDocument();
  });
});