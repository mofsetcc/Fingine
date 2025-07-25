/**
 * Base TypeScript interfaces and types for the frontend application
 */

// Common utility types
export type UUID = string;
export type Timestamp = string; // ISO 8601 format
export type DateString = string; // YYYY-MM-DD format

// API Response types
export interface APIResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
  timestamp: Timestamp;
  request_id?: string;
}

export interface APIErrorResponse {
  success: false;
  message: string;
  error_code: string;
  errors?: ErrorDetail[];
  timestamp: Timestamp;
  request_id?: string;
  trace_id?: string;
}

export interface ErrorDetail {
  field?: string;
  code: string;
  message: string;
  details?: Record<string, any>;
}

// Pagination types
export interface PaginationMeta {
  page: number;
  per_page: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
  next_page?: number;
  prev_page?: number;
}

export interface PaginatedResponse<T> {
  success: true;
  message: string;
  data: T[];
  pagination: PaginationMeta;
  timestamp: Timestamp;
}

// Common entity base interfaces
export interface BaseEntity {
  id: UUID;
  created_at: Timestamp;
  updated_at: Timestamp;
}

export interface TimestampEntity {
  created_at: Timestamp;
  updated_at: Timestamp;
}

// Sort and filter types
export type SortOrder = 'asc' | 'desc';

export interface SortOption {
  field: string;
  order: SortOrder;
}

export type FilterOperator = 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'in' | 'like' | 'between';

export interface FilterOption {
  field: string;
  operator: FilterOperator;
  value: any;
}

// Loading and error states
export interface LoadingState {
  isLoading: boolean;
  error?: string | null;
  lastUpdated?: Timestamp;
}

export interface AsyncState<T> extends LoadingState {
  data?: T;
}

// Form validation types
export interface ValidationError {
  field: string;
  message: string;
}

export interface FormState<T> {
  values: T;
  errors: ValidationError[];
  isSubmitting: boolean;
  isDirty: boolean;
  isValid: boolean;
}

// Theme and UI types
export type ThemeMode = 'light' | 'dark' | 'system';

export interface UIPreferences {
  theme: ThemeMode;
  language: 'ja' | 'en';
  timezone: string;
  dateFormat: string;
  numberFormat: string;
}

// Notification types
export type NotificationType = 
  | 'price_alert' 
  | 'volume_alert' 
  | 'earnings_announcement' 
  | 'news_alert'
  | 'ai_analysis_complete' 
  | 'system_maintenance' 
  | 'account_update'
  | 'subscription_update' 
  | 'watchlist_update' 
  | 'market_update';

export type NotificationPriority = 'low' | 'normal' | 'high' | 'urgent';

// WebSocket message types
export interface WebSocketMessage<T = any> {
  type: string;
  data: T;
  timestamp: Timestamp;
  message_id?: string;
}

export interface WebSocketErrorMessage {
  type: 'error';
  error_code: string;
  message: string;
  timestamp: Timestamp;
}

// Chart and visualization types
export interface ChartDataPoint {
  x: number | string | Date;
  y: number;
  label?: string;
}

export interface TimeSeriesDataPoint {
  timestamp: Timestamp;
  value: number;
  volume?: number;
}

export interface OHLCVDataPoint {
  timestamp: Timestamp;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// Search and autocomplete types
export interface SearchResult<T> {
  item: T;
  score: number;
  highlights?: string[];
}

export interface AutocompleteOption {
  value: string;
  label: string;
  description?: string;
  icon?: string;
}

// File upload types
export interface FileUploadProgress {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  error?: string;
}

// Export types
export type ExportFormat = 'csv' | 'excel' | 'pdf' | 'json';

export interface ExportRequest {
  format: ExportFormat;
  data_type: string;
  filters?: FilterOption[];
  date_range?: {
    start: DateString;
    end: DateString;
  };
}

// Utility type helpers
export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>;
export type PartialExcept<T, K extends keyof T> = Partial<T> & Pick<T, K>;

// Environment and configuration types
export interface AppConfig {
  api_base_url: string;
  websocket_url: string;
  environment: 'development' | 'staging' | 'production';
  version: string;
  features: {
    oauth_google: boolean;
    oauth_line: boolean;
    ai_analysis: boolean;
    real_time_data: boolean;
    advanced_charts: boolean;
  };
}

// Route and navigation types
export interface RouteParams {
  [key: string]: string | undefined;
}

export interface NavigationItem {
  path: string;
  label: string;
  icon?: string;
  badge?: string | number;
  children?: NavigationItem[];
  requiresAuth?: boolean;
  requiredSubscription?: string[];
}