/**
 * Watchlist TypeScript interfaces
 */

import { BaseEntity, PaginatedResponse, Timestamp, UUID } from './base';
import { Stock } from './stock';

// Simple Watchlist Stock Types (matching current backend implementation)
export interface SimpleWatchlistStock {
  id?: string | null;
  user_id: UUID;
  ticker: string;
  notes?: string;
  created_at: Timestamp;
  updated_at: Timestamp;
  stock?: Stock;
}

export interface SimpleWatchlistStockCreate {
  ticker: string;
  notes?: string;
}

export interface SimpleWatchlistStockUpdate {
  notes?: string;
}

export interface WatchlistStockWithPrice extends SimpleWatchlistStock {
  current_price?: number;
  price_change?: number;
  price_change_percent?: number;
  volume_today?: number;
  last_updated?: string;
  
  // Alert status
  price_alert_triggered: boolean;
  volume_alert_triggered: boolean;
}

// Watchlist Types
export interface Watchlist extends BaseEntity {
  name: string;
  description?: string;
  is_public: boolean;
  color?: string; // hex color
  user_id: UUID;
  stock_count: number;
}

export interface WatchlistCreate {
  name: string;
  description?: string;
  is_public?: boolean;
  color?: string;
}

export interface WatchlistUpdate {
  name?: string;
  description?: string;
  is_public?: boolean;
  color?: string;
}

export interface WatchlistWithStocks extends Watchlist {
  stocks: WatchlistStock[];
}

// Watchlist Stock Types
export interface WatchlistStock extends BaseEntity {
  watchlist_id: UUID;
  ticker: string;
  notes?: string;
  target_price?: number;
  stop_loss_price?: number;
  alert_price_above?: number;
  alert_price_below?: number;
  alert_volume_above?: number;
  alert_enabled: boolean;
  stock?: Stock;
}

export interface WatchlistStockCreate {
  watchlist_id: UUID;
  ticker: string;
  notes?: string;
  target_price?: number;
  stop_loss_price?: number;
  alert_price_above?: number;
  alert_price_below?: number;
  alert_volume_above?: number;
  alert_enabled?: boolean;
}

export interface WatchlistStockUpdate {
  notes?: string;
  target_price?: number;
  stop_loss_price?: number;
  alert_price_above?: number;
  alert_price_below?: number;
  alert_volume_above?: number;
  alert_enabled?: boolean;
}

export interface WatchlistStockWithPrice extends WatchlistStock {
  current_price?: number;
  price_change?: number;
  price_change_percent?: number;
  volume_today?: number;
  last_updated?: Timestamp;
  
  // Alert status
  price_alert_triggered: boolean;
  volume_alert_triggered: boolean;
}

// Watchlist Alert Types
export type WatchlistAlertType = 'price_above' | 'price_below' | 'volume_above' | 'target_reached' | 'stop_loss_hit';

export interface WatchlistAlert extends BaseEntity {
  watchlist_stock_id: UUID;
  alert_type: WatchlistAlertType;
  trigger_value: number;
  current_value: number;
  message: string;
  is_read: boolean;
  watchlist_stock?: WatchlistStock;
}

export interface WatchlistAlertCreate {
  watchlist_stock_id: UUID;
  alert_type: WatchlistAlertType;
  trigger_value: number;
  current_value: number;
  message: string;
  is_read?: boolean;
}

// Watchlist Performance Types
export interface WatchlistPerformance {
  watchlist_id: UUID;
  total_value: number;
  total_change: number;
  total_change_percent: number;
  best_performer?: Record<string, any>;
  worst_performer?: Record<string, any>;
  stocks_up: number;
  stocks_down: number;
  stocks_unchanged: number;
  average_change_percent: number;
  calculation_date: Timestamp;
}

// Watchlist Statistics Types
export interface WatchlistStatistics {
  user_id: UUID;
  total_watchlists: number;
  total_stocks_watched: number;
  most_watched_sectors: Array<Record<string, any>>;
  most_watched_stocks: Array<Record<string, any>>;
  average_watchlist_size: number;
  alerts_triggered_today: number;
  alerts_triggered_this_week: number;
  performance_summary: Record<string, any>;
}

// Public Watchlist Types
export interface PublicWatchlistSummary {
  id: UUID;
  name: string;
  description?: string;
  owner_display_name: string;
  stock_count: number;
  followers_count: number;
  performance_1d?: number;
  performance_1w?: number;
  performance_1m?: number;
  created_at: Timestamp;
  updated_at: Timestamp;
}

export interface WatchlistFollower {
  watchlist_id: UUID;
  user_id: UUID;
  followed_at: Timestamp;
}

// Watchlist Import/Export Types
export interface WatchlistImportRequest {
  name: string;
  tickers: string[];
  source?: string;
}

export interface WatchlistExportRequest {
  watchlist_ids: UUID[];
  format: 'csv' | 'excel' | 'json';
  include_notes: boolean;
  include_alerts: boolean;
}

export interface WatchlistExportResponse {
  export_id: UUID;
  download_url?: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: Timestamp;
  expires_at?: Timestamp;
}

// Bulk Operations Types
export type BulkOperationType = 'add' | 'remove' | 'move' | 'copy';

export interface BulkWatchlistStockOperation {
  operation: BulkOperationType;
  watchlist_id: UUID;
  tickers: string[];
}

export interface BulkOperationResult {
  operation: BulkOperationType;
  total_requested: number;
  successful: number;
  failed: number;
  errors: string[];
  warnings: string[];
}

// Watchlist Form Types
export interface WatchlistFormData {
  name: string;
  description: string;
  is_public: boolean;
  color: string;
}

export interface WatchlistStockFormData {
  ticker: string;
  notes: string;
  target_price: string;
  stop_loss_price: string;
  alert_price_above: string;
  alert_price_below: string;
  alert_volume_above: string;
  alert_enabled: boolean;
}

export interface BulkAddStocksFormData {
  watchlist_id: UUID;
  tickers: string;
  source: 'manual' | 'file' | 'portfolio';
}

// Watchlist Display Types
export interface WatchlistDisplayConfig {
  show_performance: boolean;
  show_alerts: boolean;
  show_notes: boolean;
  show_targets: boolean;
  compact_view: boolean;
  sort_by: 'name' | 'ticker' | 'price' | 'change' | 'volume' | 'added_date';
  sort_order: 'asc' | 'desc';
  group_by?: 'sector' | 'industry' | 'performance' | 'alerts';
}

export interface WatchlistCard {
  watchlist: Watchlist;
  performance?: WatchlistPerformance;
  displayConfig: WatchlistDisplayConfig;
  onEdit?: (watchlist: Watchlist) => void;
  onDelete?: (watchlist: Watchlist) => void;
  onShare?: (watchlist: Watchlist) => void;
  onExport?: (watchlist: Watchlist) => void;
}

export interface WatchlistStockCard {
  stock: WatchlistStockWithPrice;
  displayConfig: WatchlistDisplayConfig;
  onEdit?: (stock: WatchlistStock) => void;
  onRemove?: (stock: WatchlistStock) => void;
  onViewAnalysis?: (ticker: string) => void;
  onSetAlert?: (stock: WatchlistStock) => void;
}

// Watchlist Filter Types
export interface WatchlistFilter {
  search_query?: string;
  is_public?: boolean;
  has_alerts?: boolean;
  performance_filter?: 'gainers' | 'losers' | 'all';
  sector_filter?: string;
  created_date_range?: {
    start: string;
    end: string;
  };
  stock_count_range?: {
    min: number;
    max: number;
  };
}

export interface WatchlistStockFilter {
  search_query?: string;
  has_alerts?: boolean;
  alert_triggered?: boolean;
  price_range?: {
    min: number;
    max: number;
  };
  change_range?: {
    min: number;
    max: number;
  };
  sector?: string;
  industry?: string;
}

// Watchlist State Types (for Redux/Context)
export interface WatchlistState {
  // Watchlists
  watchlists: Watchlist[];
  currentWatchlist?: WatchlistWithStocks;
  
  // Watchlist stocks
  watchlistStocks: {
    [watchlistId: string]: WatchlistStockWithPrice[];
  };
  
  // Performance data
  performance: {
    [watchlistId: string]: WatchlistPerformance;
  };
  
  // Alerts
  alerts: WatchlistAlert[];
  unreadAlertsCount: number;
  
  // Public watchlists
  publicWatchlists: PublicWatchlistSummary[];
  followedWatchlists: UUID[];
  
  // Statistics
  statistics: WatchlistStatistics | null;
  
  // UI state
  selectedWatchlistId?: UUID;
  displayConfig: WatchlistDisplayConfig;
  filters: WatchlistFilter;
  stockFilters: WatchlistStockFilter;
  
  // Loading states
  isLoadingWatchlists: boolean;
  isLoadingStocks: boolean;
  isLoadingPerformance: boolean;
  isLoadingAlerts: boolean;
  isLoadingPublicWatchlists: boolean;
  isLoadingStatistics: boolean;
  
  // Error states
  watchlistsError?: string;
  stocksError?: string;
  performanceError?: string;
  alertsError?: string;
  publicWatchlistsError?: string;
  statisticsError?: string;
  
  // Operation states
  isCreatingWatchlist: boolean;
  isUpdatingWatchlist: boolean;
  isDeletingWatchlist: boolean;
  isAddingStock: boolean;
  isRemovingStock: boolean;
  isUpdatingStock: boolean;
  isBulkOperating: boolean;
  
  // Last updated timestamps
  lastUpdated: {
    watchlists?: Timestamp;
    stocks?: Timestamp;
    performance?: Timestamp;
    alerts?: Timestamp;
    publicWatchlists?: Timestamp;
    statistics?: Timestamp;
  };
}

// Watchlist Sharing Types
export interface WatchlistShare {
  id: UUID;
  watchlist_id: UUID;
  shared_by: UUID;
  share_token: string;
  is_public: boolean;
  expires_at?: Timestamp;
  view_count: number;
  created_at: Timestamp;
}

export interface WatchlistShareCreate {
  watchlist_id: UUID;
  is_public: boolean;
  expires_at?: Timestamp;
}

// Watchlist Comparison Types
export interface WatchlistComparison {
  watchlist_ids: UUID[];
  comparison_metrics: {
    [watchlistId: string]: {
      total_value: number;
      total_change_percent: number;
      best_performer: string;
      worst_performer: string;
      sector_allocation: Record<string, number>;
      risk_score: number;
    };
  };
  summary: string;
  created_at: Timestamp;
}

// Watchlist Recommendation Types
export interface WatchlistRecommendation {
  watchlist_id: UUID;
  recommendation_type: 'add_stock' | 'remove_stock' | 'rebalance' | 'take_profit' | 'stop_loss';
  ticker?: string;
  reason: string;
  confidence_score: number;
  potential_impact: number;
  created_at: Timestamp;
}

// Paginated Watchlist Responses
export type PaginatedWatchlistsResponse = PaginatedResponse<Watchlist>;
export type PaginatedWatchlistStocksResponse = PaginatedResponse<WatchlistStockWithPrice>;
export type PaginatedWatchlistAlertsResponse = PaginatedResponse<WatchlistAlert>;
export type PaginatedPublicWatchlistsResponse = PaginatedResponse<PublicWatchlistSummary>;