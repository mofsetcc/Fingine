/**
 * Redux store and application state TypeScript interfaces
 */

import { AIAnalysisState } from './ai-analysis';
import { AppConfig, Timestamp, UIPreferences } from './base';
import { FinancialState } from './financial';
import { NotificationState } from './notification';
import { StockState } from './stock';
import { SubscriptionState } from './subscription';
import { UserState } from './user';
import { WatchlistState } from './watchlist';

// Root Application State
export interface RootState {
  // Feature states
  user: UserState;
  stock: StockState;
  financial: FinancialState;
  aiAnalysis: AIAnalysisState;
  watchlist: WatchlistState;
  subscription: SubscriptionState;
  notification: NotificationState;
  
  // UI and app states
  ui: UIState;
  app: AppState;
  
  // Router state (if using connected-react-router)
  router?: any;
}

// UI State
export interface UIState {
  // Theme and preferences
  preferences: UIPreferences;
  
  // Layout state
  layout: {
    sidebarOpen: boolean;
    sidebarCollapsed: boolean;
    headerHeight: number;
    footerHeight: number;
    contentPadding: number;
  };
  
  // Modal and dialog state
  modals: {
    [modalId: string]: {
      isOpen: boolean;
      data?: any;
      options?: any;
    };
  };
  
  // Loading overlays
  globalLoading: boolean;
  loadingMessage?: string;
  
  // Toast notifications
  toasts: Toast[];
  
  // Responsive breakpoints
  breakpoint: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  
  // Navigation state
  navigation: {
    currentPath: string;
    previousPath?: string;
    breadcrumbs: Breadcrumb[];
    activeMenuItem?: string;
  };
  
  // Search state
  globalSearch: {
    query: string;
    isOpen: boolean;
    results: any[];
    isSearching: boolean;
    recentSearches: string[];
  };
  
  // Keyboard shortcuts
  shortcuts: {
    enabled: boolean;
    activeShortcuts: Record<string, () => void>;
  };
  
  // Drag and drop state
  dragDrop: {
    isDragging: boolean;
    dragType?: string;
    dragData?: any;
    dropZones: string[];
  };
}

// App State
export interface AppState {
  // Application configuration
  config: AppConfig;
  
  // Initialization state
  isInitialized: boolean;
  isInitializing: boolean;
  initializationError?: string;
  
  // Connection state
  isOnline: boolean;
  connectionQuality: 'good' | 'poor' | 'offline';
  lastOnlineAt?: Timestamp;
  
  // WebSocket connection
  websocket: {
    isConnected: boolean;
    isConnecting: boolean;
    reconnectAttempts: number;
    lastConnectedAt?: Timestamp;
    subscriptions: string[];
  };
  
  // Performance monitoring
  performance: {
    pageLoadTime?: number;
    apiResponseTimes: Record<string, number>;
    renderTimes: Record<string, number>;
    memoryUsage?: number;
  };
  
  // Error tracking
  errors: {
    global: AppError[];
    api: APIError[];
    javascript: JSError[];
  };
  
  // Feature flags
  features: Record<string, boolean>;
  
  // A/B testing
  experiments: Record<string, string>;
  
  // Analytics
  analytics: {
    sessionId: string;
    userId?: string;
    events: AnalyticsEvent[];
    pageViews: PageView[];
  };
  
  // Cache management
  cache: {
    policies: Record<string, CachePolicy>;
    storage: Record<string, CachedData>;
    lastCleanup: Timestamp;
  };
  
  // Background tasks
  backgroundTasks: {
    [taskId: string]: BackgroundTask;
  };
}

// Toast Notification Types
export interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
  persistent?: boolean;
  actions?: ToastAction[];
  createdAt: Timestamp;
}

export interface ToastAction {
  label: string;
  action: () => void;
  style?: 'primary' | 'secondary' | 'danger';
}

// Breadcrumb Types
export interface Breadcrumb {
  label: string;
  path?: string;
  isActive: boolean;
  icon?: string;
}

// Error Types
export interface AppError {
  id: string;
  type: 'network' | 'validation' | 'permission' | 'unknown';
  message: string;
  details?: any;
  timestamp: Timestamp;
  resolved: boolean;
}

export interface APIError extends AppError {
  endpoint: string;
  method: string;
  statusCode: number;
  requestId?: string;
}

export interface JSError extends AppError {
  stack?: string;
  componentStack?: string;
  userAgent: string;
  url: string;
}

// Analytics Types
export interface AnalyticsEvent {
  id: string;
  name: string;
  category: string;
  properties: Record<string, any>;
  timestamp: Timestamp;
  userId?: string;
  sessionId: string;
}

export interface PageView {
  id: string;
  path: string;
  title: string;
  referrer?: string;
  timestamp: Timestamp;
  duration?: number;
  userId?: string;
  sessionId: string;
}

// Cache Types
export interface CachePolicy {
  ttl: number; // seconds
  maxSize?: number;
  strategy: 'lru' | 'fifo' | 'ttl';
  persistent?: boolean;
}

export interface CachedData {
  key: string;
  data: any;
  timestamp: Timestamp;
  expiresAt: Timestamp;
  size: number;
  accessCount: number;
  lastAccessed: Timestamp;
}

// Background Task Types
export interface BackgroundTask {
  id: string;
  type: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number; // 0-100
  startedAt?: Timestamp;
  completedAt?: Timestamp;
  error?: string;
  result?: any;
  metadata?: Record<string, any>;
}

// Redux Action Types
export interface Action<T = any> {
  type: string;
  payload?: T;
  meta?: any;
  error?: boolean;
}

export interface AsyncAction<T = any> extends Action<T> {
  loading?: boolean;
  error?: string | null;
}

// Redux Thunk Types
export type AppThunk<ReturnType = void> = (
  dispatch: AppDispatch,
  getState: () => RootState
) => ReturnType;

export type AppDispatch = (action: Action | AppThunk) => any;

// Selector Types
export type Selector<T> = (state: RootState) => T;
export type ParameterizedSelector<T, P> = (state: RootState, props: P) => T;

// Middleware Types
export interface MiddlewareAPI {
  dispatch: AppDispatch;
  getState: () => RootState;
}

export type Middleware = (api: MiddlewareAPI) => (next: AppDispatch) => (action: Action) => any;

// Store Configuration Types
export interface StoreConfig {
  preloadedState?: Partial<RootState>;
  middleware?: Middleware[];
  devTools?: boolean;
  persistConfig?: PersistConfig;
}

export interface PersistConfig {
  key: string;
  storage: any;
  whitelist?: string[];
  blacklist?: string[];
  transforms?: any[];
  version?: number;
  migrate?: (state: any, version: number) => any;
}

// Hydration Types
export interface HydrationState {
  isHydrated: boolean;
  isHydrating: boolean;
  hydrationError?: string;
  lastHydrated?: Timestamp;
}

// State Persistence Types
export interface PersistedState {
  _persist: {
    version: number;
    rehydrated: boolean;
  };
}

// State Validation Types
export interface StateValidator<T> {
  validate: (state: T) => boolean;
  sanitize?: (state: T) => T;
  migrate?: (state: any, version: number) => T;
}

// Store Enhancer Types
export type StoreEnhancer = (createStore: any) => any;

// Development Tools Types
export interface DevToolsConfig {
  name?: string;
  maxAge?: number;
  trace?: boolean;
  traceLimit?: number;
  actionSanitizer?: (action: Action) => Action;
  stateSanitizer?: (state: RootState) => RootState;
}

// Hot Reloading Types
export interface HotReloadConfig {
  reducers?: boolean;
  sagas?: boolean;
  components?: boolean;
}

// Store Subscription Types
export interface StoreSubscription {
  id: string;
  selector: Selector<any>;
  callback: (value: any, previousValue: any) => void;
  options?: {
    equalityFn?: (a: any, b: any) => boolean;
    fireImmediately?: boolean;
  };
}

// State Snapshot Types
export interface StateSnapshot {
  id: string;
  timestamp: Timestamp;
  state: RootState;
  metadata?: Record<string, any>;
}

// Time Travel Debugging Types
export interface TimeTravelState {
  past: StateSnapshot[];
  present: StateSnapshot;
  future: StateSnapshot[];
  maxHistorySize: number;
}

// Store Metrics Types
export interface StoreMetrics {
  actionCount: number;
  stateSize: number;
  lastActionTime: Timestamp;
  averageActionTime: number;
  slowestActions: Array<{
    type: string;
    duration: number;
    timestamp: Timestamp;
  }>;
}