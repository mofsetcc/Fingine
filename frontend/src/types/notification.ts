/**
 * Notification TypeScript interfaces
 */

import { BaseEntity, NotificationPriority, NotificationType, PaginatedResponse, Timestamp, UUID } from './base';

// Notification Types
export interface Notification extends BaseEntity {
  title: string;
  message: string;
  notification_type: NotificationType;
  priority: NotificationPriority;
  data?: Record<string, any>;
  user_id: UUID;
  is_read: boolean;
  is_archived: boolean;
  read_at?: Timestamp;
  delivered_at?: Timestamp;
  scheduled_for?: Timestamp;
}

export interface NotificationCreate {
  title: string;
  message: string;
  notification_type: NotificationType;
  priority?: NotificationPriority;
  data?: Record<string, any>;
  user_id: UUID;
  scheduled_for?: Timestamp;
}

export interface NotificationUpdate {
  is_read?: boolean;
  is_archived?: boolean;
}

// Notification Preferences Types
export interface NotificationPreferences extends BaseEntity {
  user_id: UUID;
  email_enabled: boolean;
  push_enabled: boolean;
  sms_enabled: boolean;
  
  // Specific notification type preferences
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

export interface NotificationPreferencesCreate {
  email_enabled?: boolean;
  push_enabled?: boolean;
  sms_enabled?: boolean;
  price_alerts?: boolean;
  volume_alerts?: boolean;
  earnings_announcements?: boolean;
  news_alerts?: boolean;
  ai_analysis_complete?: boolean;
  system_maintenance?: boolean;
  account_updates?: boolean;
  subscription_updates?: boolean;
  watchlist_updates?: boolean;
  market_updates?: boolean;
  quiet_hours_enabled?: boolean;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
  timezone?: string;
  digest_enabled?: boolean;
  digest_time?: string;
  max_notifications_per_hour?: number;
}

export interface NotificationPreferencesUpdate {
  email_enabled?: boolean;
  push_enabled?: boolean;
  sms_enabled?: boolean;
  price_alerts?: boolean;
  volume_alerts?: boolean;
  earnings_announcements?: boolean;
  news_alerts?: boolean;
  ai_analysis_complete?: boolean;
  system_maintenance?: boolean;
  account_updates?: boolean;
  subscription_updates?: boolean;
  watchlist_updates?: boolean;
  market_updates?: boolean;
  quiet_hours_enabled?: boolean;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
  timezone?: string;
  digest_enabled?: boolean;
  digest_time?: string;
  max_notifications_per_hour?: number;
}

// Notification Template Types
export interface NotificationTemplate extends BaseEntity {
  name: string;
  notification_type: NotificationType;
  title_template: string;
  message_template: string;
  is_active: boolean;
  language: 'ja' | 'en';
}

export interface NotificationTemplateCreate {
  name: string;
  notification_type: NotificationType;
  title_template: string;
  message_template: string;
  is_active?: boolean;
  language?: 'ja' | 'en';
}

export interface NotificationTemplateUpdate {
  title_template?: string;
  message_template?: string;
  is_active?: boolean;
}

// Notification Channel Types
export type NotificationChannelType = 'email' | 'push' | 'sms' | 'webhook' | 'slack';

export interface NotificationChannel extends BaseEntity {
  user_id: UUID;
  channel_type: NotificationChannelType;
  is_enabled: boolean;
  configuration: Record<string, any>;
  last_used_at?: Timestamp;
  failure_count: number;
}

export interface NotificationChannelCreate {
  user_id: UUID;
  channel_type: NotificationChannelType;
  is_enabled?: boolean;
  configuration: Record<string, any>;
}

export interface NotificationChannelUpdate {
  is_enabled?: boolean;
  configuration?: Record<string, any>;
}

// Notification Delivery Types
export type DeliveryStatus = 'pending' | 'sent' | 'delivered' | 'failed' | 'bounced';

export interface NotificationDelivery extends BaseEntity {
  notification_id: UUID;
  channel_type: NotificationChannelType;
  status: DeliveryStatus;
  attempt_count: number;
  error_message?: string;
  delivered_at?: Timestamp;
}

export interface NotificationDeliveryCreate {
  notification_id: UUID;
  channel_type: NotificationChannelType;
  status: DeliveryStatus;
  attempt_count?: number;
  error_message?: string;
  delivered_at?: Timestamp;
}

// Notification Statistics Types
export interface NotificationStatistics {
  user_id: UUID;
  total_notifications: number;
  unread_notifications: number;
  notifications_today: number;
  notifications_this_week: number;
  notifications_by_type: Record<string, number>;
  notifications_by_priority: Record<string, number>;
  average_read_time?: number; // minutes
  most_active_hours: number[];
}

// Bulk Notification Types
export interface BulkNotificationRequest {
  user_ids: UUID[];
  title: string;
  message: string;
  notification_type: NotificationType;
  priority?: NotificationPriority;
  data?: Record<string, any>;
  scheduled_for?: Timestamp;
}

export interface BulkNotificationResult {
  total_requested: number;
  successful: number;
  failed: number;
  errors: string[];
}

// Notification Digest Types
export interface NotificationDigest {
  user_id: UUID;
  digest_date: string; // YYYY-MM-DD
  total_notifications: number;
  notifications_by_type: Record<string, number>;
  high_priority_count: number;
  unread_count: number;
  summary: string;
  notifications: Notification[];
}

// Notification Form Types
export interface NotificationPreferencesFormData {
  email_enabled: boolean;
  push_enabled: boolean;
  sms_enabled: boolean;
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
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
  timezone: string;
  digest_enabled: boolean;
  digest_time: string;
  max_notifications_per_hour: number;
}

export interface NotificationChannelFormData {
  channel_type: NotificationChannelType;
  is_enabled: boolean;
  
  // Email specific
  email_address?: string;
  
  // SMS specific
  phone_number?: string;
  
  // Webhook specific
  webhook_url?: string;
  webhook_secret?: string;
  
  // Slack specific
  slack_webhook_url?: string;
  slack_channel?: string;
}

// Notification Display Types
export interface NotificationDisplayConfig {
  show_unread_only: boolean;
  show_archived: boolean;
  group_by_type: boolean;
  group_by_date: boolean;
  compact_view: boolean;
  auto_mark_read: boolean;
  sort_by: 'created_at' | 'priority' | 'type';
  sort_order: 'asc' | 'desc';
}

export interface NotificationCard {
  notification: Notification;
  displayConfig: NotificationDisplayConfig;
  onMarkRead?: (notification: Notification) => void;
  onMarkUnread?: (notification: Notification) => void;
  onArchive?: (notification: Notification) => void;
  onDelete?: (notification: Notification) => void;
  onClick?: (notification: Notification) => void;
}

// Notification Filter Types
export interface NotificationFilter {
  is_read?: boolean;
  is_archived?: boolean;
  notification_types?: NotificationType[];
  priorities?: NotificationPriority[];
  date_range?: {
    start: string;
    end: string;
  };
  search_query?: string;
}

// Notification State Types (for Redux/Context)
export interface NotificationState {
  // Notifications
  notifications: Notification[];
  unreadCount: number;
  
  // Preferences
  preferences?: NotificationPreferences;
  
  // Channels
  channels: NotificationChannel[];
  
  // Templates (for admin)
  templates: NotificationTemplate[];
  
  // Statistics
  statistics?: NotificationStatistics;
  
  // Digest
  digest?: NotificationDigest;
  
  // UI state
  displayConfig: NotificationDisplayConfig;
  filters: NotificationFilter;
  selectedNotificationId?: UUID;
  
  // Loading states
  isLoadingNotifications: boolean;
  isLoadingPreferences: boolean;
  isLoadingChannels: boolean;
  isLoadingTemplates: boolean;
  isLoadingStatistics: boolean;
  isLoadingDigest: boolean;
  
  // Error states
  notificationsError?: string;
  preferencesError?: string;
  channelsError?: string;
  templatesError?: string;
  statisticsError?: string;
  digestError?: string;
  
  // Operation states
  isMarkingRead: boolean;
  isArchiving: boolean;
  isDeleting: boolean;
  isUpdatingPreferences: boolean;
  isUpdatingChannel: boolean;
  
  // Last updated timestamps
  lastUpdated: {
    notifications?: Timestamp;
    preferences?: Timestamp;
    channels?: Timestamp;
    templates?: Timestamp;
    statistics?: Timestamp;
    digest?: Timestamp;
  };
}

// Real-time Notification Types
export interface RealtimeNotification {
  notification: Notification;
  action: 'created' | 'updated' | 'deleted';
  timestamp: Timestamp;
}

export interface NotificationSubscription {
  user_id: UUID;
  channel: string;
  is_active: boolean;
  last_ping: Timestamp;
}

// Notification Analytics Types
export interface NotificationAnalytics {
  period: string;
  total_sent: number;
  total_delivered: number;
  total_read: number;
  delivery_rate: number;
  read_rate: number;
  bounce_rate: number;
  
  by_type: Record<NotificationType, {
    sent: number;
    delivered: number;
    read: number;
  }>;
  
  by_channel: Record<NotificationChannelType, {
    sent: number;
    delivered: number;
    failed: number;
  }>;
  
  engagement_metrics: {
    average_time_to_read: number; // minutes
    peak_engagement_hours: number[];
    most_engaging_types: NotificationType[];
  };
}

// Notification Export Types
export interface NotificationExportRequest {
  user_id?: UUID;
  date_range: {
    start: string;
    end: string;
  };
  notification_types?: NotificationType[];
  include_read: boolean;
  include_archived: boolean;
  format: 'csv' | 'json' | 'excel';
}

// Paginated Notification Responses
export type PaginatedNotificationsResponse = PaginatedResponse<Notification>;
export type PaginatedNotificationTemplatesResponse = PaginatedResponse<NotificationTemplate>;
export type PaginatedNotificationChannelsResponse = PaginatedResponse<NotificationChannel>;