/**
 * User-related TypeScript interfaces
 */

import { BaseEntity, Timestamp, TimestampEntity, UUID } from './base';

// User Authentication Types
export interface UserRegistrationRequest {
  email: string;
  password: string;
  display_name?: string;
}

export interface UserLoginRequest {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetConfirmRequest {
  token: string;
  new_password: string;
}

export interface OAuthLoginRequest {
  provider: 'google' | 'line';
  access_token: string;
}

// User Profile Types
export interface UserProfileUpdate {
  display_name?: string;
  avatar_url?: string;
  timezone?: string;
  notification_preferences?: Record<string, any>;
}

export interface UserProfile extends BaseEntity {
  user_id: UUID;
  display_name?: string;
  avatar_url?: string;
  timezone: string;
  notification_preferences: Record<string, any>;
}

// User Entity Types
export interface User extends BaseEntity {
  email: string;
  email_verified_at?: Timestamp;
  profile?: UserProfile;
}

export interface UserWithProfile extends User {
  profile: UserProfile;
}

// Authentication Token Types
export interface AuthToken {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  user: User;
  tokens: AuthToken;
  message: string;
}

// OAuth Identity Types
export interface OAuthIdentity extends TimestampEntity {
  provider: string;
  provider_user_id: string;
  user_id: UUID;
}

// User State Types (for Redux/Context)
export interface UserState {
  currentUser?: User;
  isAuthenticated: boolean;
  isLoading: boolean;
  error?: string;
  tokens?: AuthToken;
  loginAttempts: number;
  lastLoginAttempt?: Timestamp;
}

// Authentication Form Types
export interface LoginFormData {
  email: string;
  password: string;
  remember_me: boolean;
}

export interface RegisterFormData {
  email: string;
  password: string;
  confirm_password: string;
  display_name: string;
  agree_to_terms: boolean;
}

export interface PasswordResetFormData {
  email: string;
}

export interface PasswordResetConfirmFormData {
  new_password: string;
  confirm_password: string;
}

export interface ProfileFormData {
  display_name: string;
  timezone: string;
  avatar_file?: File;
}

// User Preferences Types
export interface NotificationPreferences {
  email_enabled: boolean;
  push_enabled: boolean;
  sms_enabled: boolean;
  
  // Specific notification types
  price_alerts: boolean;
  volume_alerts: boolean;
  earnings_announcements: boolean;
  news_alerts: boolean;
  ai_analysis_complete: boolean;
  system_maintenance: boolean;
  account_updates: boolean;
  subscription_updates: boolean;
  watchlist_updates: boolean;
  market_updates: boolean;
  
  // Timing preferences
  quiet_hours_enabled: boolean;
  quiet_hours_start?: string; // HH:MM format
  quiet_hours_end?: string; // HH:MM format
  timezone: string;
  
  // Frequency preferences
  digest_enabled: boolean;
  digest_time: string; // HH:MM format
  max_notifications_per_hour: number;
}

export interface UserPreferences {
  notifications: NotificationPreferences;
  ui: {
    theme: 'light' | 'dark' | 'system';
    language: 'ja' | 'en';
    date_format: string;
    number_format: string;
    default_chart_type: string;
    show_advanced_features: boolean;
  };
  trading: {
    default_watchlist_id?: UUID;
    auto_refresh_interval: number; // seconds
    show_after_hours_data: boolean;
    preferred_exchanges: string[];
  };
}

// User Activity Types
export interface UserActivity {
  id: UUID;
  user_id: UUID;
  activity_type: string;
  description: string;
  metadata?: Record<string, any>;
  ip_address?: string;
  user_agent?: string;
  created_at: Timestamp;
}

export type UserActivityType = 
  | 'login'
  | 'logout'
  | 'password_change'
  | 'profile_update'
  | 'subscription_change'
  | 'watchlist_create'
  | 'watchlist_update'
  | 'analysis_request'
  | 'export_data'
  | 'settings_change';

// User Statistics Types
export interface UserStatistics {
  user_id: UUID;
  total_logins: number;
  last_login_at?: Timestamp;
  analyses_requested: number;
  watchlists_created: number;
  favorite_stocks: string[];
  most_viewed_sectors: string[];
  average_session_duration: number; // minutes
  total_time_spent: number; // minutes
  subscription_start_date?: Timestamp;
  subscription_tier?: string;
}

// User Session Types
export interface UserSession {
  session_id: string;
  user_id: UUID;
  ip_address: string;
  user_agent: string;
  is_active: boolean;
  last_activity: Timestamp;
  expires_at: Timestamp;
  created_at: Timestamp;
}

// Account Security Types
export interface SecuritySettings {
  two_factor_enabled: boolean;
  backup_codes_generated: boolean;
  trusted_devices: TrustedDevice[];
  recent_login_attempts: LoginAttempt[];
  password_last_changed: Timestamp;
  account_locked_until?: Timestamp;
}

export interface TrustedDevice {
  device_id: string;
  device_name: string;
  device_type: 'desktop' | 'mobile' | 'tablet';
  browser: string;
  os: string;
  ip_address: string;
  last_used: Timestamp;
  trusted_at: Timestamp;
}

export interface LoginAttempt {
  ip_address: string;
  user_agent: string;
  success: boolean;
  failure_reason?: string;
  attempted_at: Timestamp;
}

// User Onboarding Types
export interface OnboardingStep {
  step_id: string;
  title: string;
  description: string;
  is_completed: boolean;
  is_required: boolean;
  order: number;
}

export interface OnboardingProgress {
  user_id: UUID;
  current_step: string;
  completed_steps: string[];
  total_steps: number;
  completion_percentage: number;
  started_at: Timestamp;
  completed_at?: Timestamp;
}

// User Feedback Types
export interface UserFeedback {
  id: UUID;
  user_id: UUID;
  feedback_type: 'bug_report' | 'feature_request' | 'general_feedback' | 'rating';
  title: string;
  description: string;
  rating?: number; // 1-5 scale
  page_url?: string;
  browser_info?: string;
  screenshot_url?: string;
  status: 'open' | 'in_progress' | 'resolved' | 'closed';
  created_at: Timestamp;
  updated_at: Timestamp;
}

// User Export Types
export interface UserDataExportRequest {
  export_type: 'full_account' | 'watchlists' | 'analysis_history' | 'preferences';
  format: 'json' | 'csv';
  include_personal_data: boolean;
  include_activity_logs: boolean;
}

export interface UserDataExport {
  export_id: UUID;
  user_id: UUID;
  export_type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  download_url?: string;
  expires_at?: Timestamp;
  created_at: Timestamp;
}