/**
 * Main TypeScript types export file
 */

// Base types
export * from './base';

// User types
export * from './user';

// Stock types
export * from './stock';

// Financial types
export * from './financial';

// AI Analysis types
export * from './ai-analysis';

// Watchlist types
export * from './watchlist';

// Subscription types
export * from './subscription';

// News types
export * from './news';

// Notification types
export * from './notification';

// Store and Redux types
export * from './store';

// Re-export commonly used types for convenience
export type {

    // AI Analysis
    AIAnalysis,
    AIAnalysisRequest, AIAnalysisState, APIErrorResponse, APIResponse, AppDispatch, AppState, AppThunk, AsyncState, AuthResponse, AuthToken, BalanceSheet, CashFlow, DateString,
    // Financial
    Earnings, FinancialState, FinancialSummary, FundamentalAnalysisResult, HotStocksResponse, IncomeStatement, LoadingState,
    // Notification
    Notification,
    NotificationPreferences,
    NotificationState, PaginatedResponse, Plan, PriceData,
    // Store
    RootState, SentimentAnalysisResult,
    // Stock
    Stock,
    StockDetail, StockSearchResult, StockState,
    // Subscription
    Subscription, SubscriptionState, TechnicalAnalysisResult, Timestamp, UIState,
    // Base
    UUID, UsageQuota,
    // User
    User, UserProfile, UserState, UserWithProfile,
    // Watchlist
    Watchlist, WatchlistAlert,
    WatchlistState, WatchlistStock,
    WatchlistStockWithPrice
} from './base';

// Type guards and utility functions
export const isAPIError = (response: any): response is APIErrorResponse => {
  return response && response.success === false && 'error_code' in response;
};

export const isAPISuccess = <T>(response: any): response is APIResponse<T> => {
  return response && response.success === true;
};

export const isPaginatedResponse = <T>(response: any): response is PaginatedResponse<T> => {
  return response && response.success === true && 'pagination' in response;
};

// Common type predicates
export const isValidUUID = (value: string): value is UUID => {
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(value);
};

export const isValidTimestamp = (value: string): value is Timestamp => {
  return !isNaN(Date.parse(value));
};

export const isValidDateString = (value: string): value is DateString => {
  const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
  return dateRegex.test(value) && !isNaN(Date.parse(value));
};

// Utility types for form handling
export type FormErrors<T> = {
  [K in keyof T]?: string;
};

export type FormTouched<T> = {
  [K in keyof T]?: boolean;
};

export type FormValues<T> = {
  [K in keyof T]: T[K];
};

// API endpoint types
export interface APIEndpoint {
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  path: string;
  authenticated?: boolean;
  rateLimit?: number;
}

export interface APIEndpoints {
  // User endpoints
  user: {
    register: APIEndpoint;
    login: APIEndpoint;
    logout: APIEndpoint;
    profile: APIEndpoint;
    updateProfile: APIEndpoint;
    changePassword: APIEndpoint;
    resetPassword: APIEndpoint;
    verifyEmail: APIEndpoint;
  };
  
  // Stock endpoints
  stock: {
    search: APIEndpoint;
    detail: APIEndpoint;
    priceHistory: APIEndpoint;
    technicalIndicators: APIEndpoint;
    hotStocks: APIEndpoint;
    marketIndices: APIEndpoint;
  };
  
  // Financial endpoints
  financial: {
    earnings: APIEndpoint;
    balanceSheet: APIEndpoint;
    incomeStatement: APIEndpoint;
    cashFlow: APIEndpoint;
    ratios: APIEndpoint;
    summary: APIEndpoint;
    earningsCalendar: APIEndpoint;
  };
  
  // AI Analysis endpoints
  aiAnalysis: {
    request: APIEndpoint;
    bulkRequest: APIEndpoint;
    history: APIEndpoint;
    result: APIEndpoint;
    export: APIEndpoint;
    templates: APIEndpoint;
  };
  
  // Watchlist endpoints
  watchlist: {
    list: APIEndpoint;
    create: APIEndpoint;
    update: APIEndpoint;
    delete: APIEndpoint;
    addStock: APIEndpoint;
    removeStock: APIEndpoint;
    updateStock: APIEndpoint;
    alerts: APIEndpoint;
    performance: APIEndpoint;
  };
  
  // Subscription endpoints
  subscription: {
    plans: APIEndpoint;
    current: APIEndpoint;
    subscribe: APIEndpoint;
    update: APIEndpoint;
    cancel: APIEndpoint;
    usage: APIEndpoint;
    billing: APIEndpoint;
    invoices: APIEndpoint;
  };
  
  // Notification endpoints
  notification: {
    list: APIEndpoint;
    markRead: APIEndpoint;
    markAllRead: APIEndpoint;
    preferences: APIEndpoint;
    updatePreferences: APIEndpoint;
    channels: APIEndpoint;
    statistics: APIEndpoint;
  };
}

// WebSocket event types
export interface WebSocketEvents {
  // Stock price updates
  'stock.price.update': {
    ticker: string;
    price: number;
    change: number;
    change_percent: number;
    volume: number;
    timestamp: Timestamp;
  };
  
  // Market updates
  'market.index.update': {
    symbol: string;
    value: number;
    change: number;
    change_percent: number;
    timestamp: Timestamp;
  };
  
  // Watchlist alerts
  'watchlist.alert': {
    alert_id: UUID;
    watchlist_id: UUID;
    ticker: string;
    alert_type: string;
    message: string;
    timestamp: Timestamp;
  };
  
  // AI analysis completion
  'ai.analysis.complete': {
    analysis_id: UUID;
    ticker: string;
    analysis_type: string;
    status: string;
    timestamp: Timestamp;
  };
  
  // Notifications
  'notification.new': {
    notification_id: UUID;
    title: string;
    message: string;
    type: string;
    priority: string;
    timestamp: Timestamp;
  };
  
  // System events
  'system.maintenance': {
    message: string;
    start_time: Timestamp;
    end_time: Timestamp;
    affected_services: string[];
  };
}

// Component prop types
export interface BaseComponentProps {
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
  testId?: string;
}

export interface LoadingComponentProps extends BaseComponentProps {
  isLoading: boolean;
  error?: string | null;
  retry?: () => void;
  loadingText?: string;
  errorText?: string;
}

export interface PaginationComponentProps extends BaseComponentProps {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  itemsPerPage: number;
  onPageChange: (page: number) => void;
  onItemsPerPageChange?: (itemsPerPage: number) => void;
  showItemsPerPage?: boolean;
  showTotalItems?: boolean;
}

// Chart component types
export interface ChartComponentProps extends BaseComponentProps {
  data: any[];
  width?: number;
  height?: number;
  responsive?: boolean;
  theme?: 'light' | 'dark';
  loading?: boolean;
  error?: string;
  onDataPointClick?: (dataPoint: any) => void;
}

// Table component types
export interface TableColumn<T> {
  key: keyof T;
  title: string;
  width?: number | string;
  align?: 'left' | 'center' | 'right';
  sortable?: boolean;
  filterable?: boolean;
  render?: (value: any, record: T, index: number) => React.ReactNode;
}

export interface TableComponentProps<T> extends BaseComponentProps {
  data: T[];
  columns: TableColumn<T>[];
  loading?: boolean;
  error?: string;
  pagination?: PaginationComponentProps;
  selection?: {
    selectedRowKeys: string[];
    onSelectionChange: (selectedRowKeys: string[]) => void;
  };
  sorting?: {
    sortBy?: keyof T;
    sortOrder?: 'asc' | 'desc';
    onSortChange: (sortBy: keyof T, sortOrder: 'asc' | 'desc') => void;
  };
  filtering?: {
    filters: Record<keyof T, any>;
    onFilterChange: (filters: Record<keyof T, any>) => void;
  };
}