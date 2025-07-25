/**
 * Stock-related TypeScript interfaces
 */

import { BaseEntity, DateString, PaginatedResponse, Timestamp, UUID } from './base';

// Stock Basic Types
export interface Stock extends BaseEntity {
  ticker: string;
  company_name_jp: string;
  company_name_en?: string;
  sector_jp?: string;
  industry_jp?: string;
  description?: string;
  logo_url?: string;
  listing_date?: DateString;
  is_active: boolean;
}

export interface StockCreate {
  ticker: string;
  company_name_jp: string;
  company_name_en?: string;
  sector_jp?: string;
  industry_jp?: string;
  description?: string;
  logo_url?: string;
  listing_date?: DateString;
  is_active?: boolean;
}

export interface StockUpdate {
  company_name_jp?: string;
  company_name_en?: string;
  sector_jp?: string;
  industry_jp?: string;
  description?: string;
  logo_url?: string;
  listing_date?: DateString;
  is_active?: boolean;
}

// Stock Search Types
export interface StockSearchQuery {
  query: string;
  limit?: number;
  include_inactive?: boolean;
  sector_filter?: string;
  industry_filter?: string;
}

export interface StockSearchResult {
  ticker: string;
  company_name_jp: string;
  company_name_en?: string;
  sector_jp?: string;
  industry_jp?: string;
  logo_url?: string;
  match_score: number;
  current_price?: number;
  price_change?: number;
  price_change_percent?: number;
}

// Price Data Types
export interface PriceData extends BaseEntity {
  ticker: string;
  date: DateString;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  adjusted_close?: number;
}

export interface PriceDataCreate {
  ticker: string;
  date: DateString;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  adjusted_close?: number;
}

// Stock Metrics Types
export interface StockDailyMetrics extends BaseEntity {
  ticker: string;
  date: DateString;
  market_cap?: number;
  pe_ratio?: number;
  pb_ratio?: number;
  dividend_yield?: number;
  shares_outstanding?: number;
}

// Market Index Types
export interface MarketIndex {
  name: string;
  symbol: string;
  value: number;
  change: number;
  change_percent: number;
  volume?: number;
  updated_at: Timestamp;
}

// Hot Stocks Types
export type HotStockCategory = 'gainer' | 'loser' | 'most_traded' | 'most_active';

export interface HotStock {
  ticker: string;
  company_name: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  category: HotStockCategory;
}

export interface HotStocksResponse {
  gainers: HotStock[];
  losers: HotStock[];
  most_traded: HotStock[];
  most_active: HotStock[];
  updated_at: Timestamp;
}

// Stock Detail Types
export interface StockDetail extends Stock {
  current_price?: number;
  price_change?: number;
  price_change_percent?: number;
  volume_today?: number;
  market_cap?: number;
  pe_ratio?: number;
  pb_ratio?: number;
  dividend_yield?: number;
  week_52_high?: number;
  week_52_low?: number;
  avg_volume_30d?: number;
  beta?: number;
  last_updated?: Timestamp;
}

// Price History Types
export type TimePeriod = '1d' | '1w' | '1m' | '3m' | '6m' | '1y' | '2y' | '5y' | 'max';
export type DataInterval = '1m' | '5m' | '15m' | '30m' | '1h' | '1d' | '1w' | '1mo';

export interface PriceHistoryQuery {
  start_date?: DateString;
  end_date?: DateString;
  period?: TimePeriod;
  interval?: DataInterval;
}

export interface PriceHistoryResponse {
  ticker: string;
  data: PriceData[];
  period: string;
  interval: string;
  total_points: number;
  start_date: DateString;
  end_date: DateString;
}

// Technical Indicators Types
export interface TechnicalIndicators {
  ticker: string;
  date: DateString;
  sma_20?: number;
  sma_50?: number;
  sma_200?: number;
  ema_12?: number;
  ema_26?: number;
  rsi_14?: number;
  macd?: number;
  macd_signal?: number;
  macd_histogram?: number;
  bollinger_upper?: number;
  bollinger_middle?: number;
  bollinger_lower?: number;
  volume_sma_20?: number;
}

// Chart Data Types
export interface CandlestickData {
  timestamp: Timestamp;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface LineChartData {
  timestamp: Timestamp;
  value: number;
  label?: string;
}

export interface VolumeData {
  timestamp: Timestamp;
  volume: number;
  price_change: number; // for coloring bars
}

// Stock Comparison Types
export interface StockComparison {
  tickers: string[];
  metrics: {
    [ticker: string]: {
      current_price: number;
      price_change_percent: number;
      market_cap?: number;
      pe_ratio?: number;
      pb_ratio?: number;
      dividend_yield?: number;
      beta?: number;
    };
  };
  performance: {
    [ticker: string]: {
      '1d': number;
      '1w': number;
      '1m': number;
      '3m': number;
      '6m': number;
      '1y': number;
    };
  };
}

// Stock Screener Types
export interface StockScreenerCriteria {
  market_cap_min?: number;
  market_cap_max?: number;
  pe_ratio_min?: number;
  pe_ratio_max?: number;
  pb_ratio_min?: number;
  pb_ratio_max?: number;
  dividend_yield_min?: number;
  dividend_yield_max?: number;
  price_min?: number;
  price_max?: number;
  volume_min?: number;
  sectors?: string[];
  industries?: string[];
  price_change_percent_min?: number;
  price_change_percent_max?: number;
}

export interface StockScreenerResult {
  stocks: StockDetail[];
  total_matches: number;
  criteria_used: StockScreenerCriteria;
}

// Stock News Types
export interface StockNews {
  id: UUID;
  ticker: string;
  title: string;
  summary: string;
  content?: string;
  source: string;
  author?: string;
  published_at: Timestamp;
  url: string;
  image_url?: string;
  sentiment_score?: number;
  relevance_score: number;
  tags: string[];
}

// Stock Alerts Types
export interface StockAlert extends BaseEntity {
  user_id: UUID;
  ticker: string;
  alert_type: 'price_above' | 'price_below' | 'volume_above' | 'percent_change';
  trigger_value: number;
  current_value?: number;
  is_active: boolean;
  is_triggered: boolean;
  triggered_at?: Timestamp;
  message?: string;
}

export interface StockAlertCreate {
  ticker: string;
  alert_type: 'price_above' | 'price_below' | 'volume_above' | 'percent_change';
  trigger_value: number;
  message?: string;
}

// Stock Portfolio Types (for tracking purposes)
export interface StockPosition {
  ticker: string;
  quantity: number;
  average_cost: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
  day_change: number;
  day_change_percent: number;
}

export interface Portfolio {
  id: UUID;
  user_id: UUID;
  name: string;
  description?: string;
  positions: StockPosition[];
  total_value: number;
  total_cost: number;
  total_pnl: number;
  total_pnl_percent: number;
  day_change: number;
  day_change_percent: number;
  created_at: Timestamp;
  updated_at: Timestamp;
}

// Stock State Types (for Redux/Context)
export interface StockState {
  // Current stock being viewed
  currentStock?: StockDetail;
  
  // Price data
  priceHistory: {
    [ticker: string]: {
      [period: string]: PriceData[];
    };
  };
  
  // Technical indicators
  technicalIndicators: {
    [ticker: string]: TechnicalIndicators;
  };
  
  // Market data
  marketIndices: MarketIndex[];
  hotStocks: HotStocksResponse | null;
  
  // Search results
  searchResults: StockSearchResult[];
  searchQuery: string;
  
  // Loading states
  isLoadingStock: boolean;
  isLoadingPriceHistory: boolean;
  isLoadingTechnicalIndicators: boolean;
  isLoadingMarketData: boolean;
  isSearching: boolean;
  
  // Error states
  stockError?: string;
  priceHistoryError?: string;
  technicalIndicatorsError?: string;
  marketDataError?: string;
  searchError?: string;
  
  // Last updated timestamps
  lastUpdated: {
    stock?: Timestamp;
    priceHistory?: Timestamp;
    technicalIndicators?: Timestamp;
    marketData?: Timestamp;
  };
}

// Chart Configuration Types
export interface ChartConfig {
  type: 'candlestick' | 'line' | 'area' | 'bar';
  period: TimePeriod;
  interval: DataInterval;
  indicators: string[];
  overlays: string[];
  theme: 'light' | 'dark';
  height: number;
  show_volume: boolean;
  show_grid: boolean;
  show_crosshair: boolean;
}

// Stock List Types
export type StockListType = 'all' | 'gainers' | 'losers' | 'most_active' | 'by_sector' | 'by_industry';

export interface StockListFilter {
  type: StockListType;
  sector?: string;
  industry?: string;
  min_price?: number;
  max_price?: number;
  min_volume?: number;
  sort_by?: 'price' | 'change' | 'volume' | 'market_cap';
  sort_order?: 'asc' | 'desc';
}

// Paginated Stock Responses
export type PaginatedStocksResponse = PaginatedResponse<Stock>;
export type PaginatedPriceDataResponse = PaginatedResponse<PriceData>;