"""Notification Pydantic schemas."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, validator

from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema, PaginatedResponse


# Notification Schemas
class NotificationBase(BaseModel):
    """Base notification schema."""
    
    title: str = Field(..., max_length=200, description="Notification title")
    message: str = Field(..., max_length=1000, description="Notification message")
    notification_type: str = Field(..., description="Type of notification")
    priority: str = Field("normal", description="Notification priority")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional notification data")
    
    @validator('notification_type')
    def validate_notification_type(cls, v):
        """Validate notification type."""
        valid_types = [
            'price_alert', 'volume_alert', 'earnings_announcement', 'news_alert',
            'ai_analysis_complete', 'system_maintenance', 'account_update',
            'subscription_update', 'watchlist_update', 'market_update'
        ]
        if v not in valid_types:
            raise ValueError(f'Notification type must be one of: {", ".join(valid_types)}')
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        """Validate notification priority."""
        if v not in ['low', 'normal', 'high', 'urgent']:
            raise ValueError('Priority must be one of: low, normal, high, urgent')
        return v


class NotificationCreate(NotificationBase):
    """Notification creation schema."""
    
    user_id: UUID = Field(..., description="Target user ID")
    scheduled_for: Optional[datetime] = Field(None, description="Schedule notification for later")


class NotificationUpdate(BaseModel):
    """Notification update schema."""
    
    is_read: Optional[bool] = Field(None, description="Mark as read/unread")
    is_archived: Optional[bool] = Field(None, description="Archive/unarchive notification")


class Notification(BaseSchema, UUIDSchema, NotificationBase, TimestampSchema):
    """Notification response schema."""
    
    user_id: UUID = Field(..., description="Target user ID")
    is_read: bool = Field(False, description="Whether notification has been read")
    is_archived: bool = Field(False, description="Whether notification is archived")
    read_at: Optional[datetime] = Field(None, description="When notification was read")
    delivered_at: Optional[datetime] = Field(None, description="When notification was delivered")
    scheduled_for: Optional[datetime] = Field(None, description="Scheduled delivery time")


# Notification Preferences Schemas
class NotificationPreferencesBase(BaseModel):
    """Base notification preferences schema."""
    
    email_enabled: bool = Field(True, description="Enable email notifications")
    push_enabled: bool = Field(True, description="Enable push notifications")
    sms_enabled: bool = Field(False, description="Enable SMS notifications")
    
    # Specific notification type preferences
    price_alerts: bool = Field(True, description="Price alert notifications")
    volume_alerts: bool = Field(True, description="Volume alert notifications")
    earnings_announcements: bool = Field(True, description="Earnings announcement notifications")
    news_alerts: bool = Field(True, description="News alert notifications")
    ai_analysis_complete: bool = Field(True, description="AI analysis completion notifications")
    system_maintenance: bool = Field(True, description="System maintenance notifications")
    account_updates: bool = Field(True, description="Account update notifications")
    subscription_updates: bool = Field(True, description="Subscription update notifications")
    watchlist_updates: bool = Field(True, description="Watchlist update notifications")
    market_updates: bool = Field(False, description="Market update notifications")
    
    # Timing preferences
    quiet_hours_enabled: bool = Field(False, description="Enable quiet hours")
    quiet_hours_start: Optional[str] = Field(None, description="Quiet hours start time (HH:MM)")
    quiet_hours_end: Optional[str] = Field(None, description="Quiet hours end time (HH:MM)")
    timezone: str = Field("Asia/Tokyo", description="User timezone")
    
    # Frequency preferences
    digest_enabled: bool = Field(False, description="Enable daily digest")
    digest_time: str = Field("09:00", description="Daily digest time (HH:MM)")
    max_notifications_per_hour: int = Field(10, ge=1, le=100, description="Max notifications per hour")
    
    @validator('quiet_hours_start', 'quiet_hours_end', 'digest_time')
    def validate_time_format(cls, v):
        """Validate time format."""
        if v is not None:
            try:
                hour, minute = map(int, v.split(':'))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError('Invalid time format')
            except (ValueError, AttributeError):
                raise ValueError('Time must be in HH:MM format')
        return v


class NotificationPreferencesCreate(NotificationPreferencesBase):
    """Notification preferences creation schema."""
    pass


class NotificationPreferencesUpdate(BaseModel):
    """Notification preferences update schema."""
    
    email_enabled: Optional[bool] = Field(None, description="Enable email notifications")
    push_enabled: Optional[bool] = Field(None, description="Enable push notifications")
    sms_enabled: Optional[bool] = Field(None, description="Enable SMS notifications")
    
    price_alerts: Optional[bool] = Field(None, description="Price alert notifications")
    volume_alerts: Optional[bool] = Field(None, description="Volume alert notifications")
    earnings_announcements: Optional[bool] = Field(None, description="Earnings announcement notifications")
    news_alerts: Optional[bool] = Field(None, description="News alert notifications")
    ai_analysis_complete: Optional[bool] = Field(None, description="AI analysis completion notifications")
    system_maintenance: Optional[bool] = Field(None, description="System maintenance notifications")
    account_updates: Optional[bool] = Field(None, description="Account update notifications")
    subscription_updates: Optional[bool] = Field(None, description="Subscription update notifications")
    watchlist_updates: Optional[bool] = Field(None, description="Watchlist update notifications")
    market_updates: Optional[bool] = Field(None, description="Market update notifications")
    
    quiet_hours_enabled: Optional[bool] = Field(None, description="Enable quiet hours")
    quiet_hours_start: Optional[str] = Field(None, description="Quiet hours start time (HH:MM)")
    quiet_hours_end: Optional[str] = Field(None, description="Quiet hours end time (HH:MM)")
    timezone: Optional[str] = Field(None, description="User timezone")
    
    digest_enabled: Optional[bool] = Field(None, description="Enable daily digest")
    digest_time: Optional[str] = Field(None, description="Daily digest time (HH:MM)")
    max_notifications_per_hour: Optional[int] = Field(None, ge=1, le=100, description="Max notifications per hour")


class NotificationPreferences(BaseSchema, UUIDSchema, NotificationPreferencesBase, TimestampSchema):
    """Notification preferences response schema."""
    
    user_id: UUID = Field(..., description="User ID")


# Notification Template Schemas
class NotificationTemplateBase(BaseModel):
    """Base notification template schema."""
    
    name: str = Field(..., max_length=100, description="Template name")
    notification_type: str = Field(..., description="Notification type")
    title_template: str = Field(..., max_length=200, description="Title template with placeholders")
    message_template: str = Field(..., max_length=1000, description="Message template with placeholders")
    is_active: bool = Field(True, description="Whether template is active")
    language: str = Field("ja", description="Template language")
    
    @validator('language')
    def validate_language(cls, v):
        """Validate language code."""
        if v not in ['ja', 'en']:
            raise ValueError('Language must be ja or en')
        return v


class NotificationTemplateCreate(NotificationTemplateBase):
    """Notification template creation schema."""
    pass


class NotificationTemplateUpdate(BaseModel):
    """Notification template update schema."""
    
    title_template: Optional[str] = Field(None, max_length=200, description="Title template")
    message_template: Optional[str] = Field(None, max_length=1000, description="Message template")
    is_active: Optional[bool] = Field(None, description="Whether template is active")


class NotificationTemplate(BaseSchema, UUIDSchema, NotificationTemplateBase, TimestampSchema):
    """Notification template response schema."""
    pass


# Notification Channel Schemas
class NotificationChannelBase(BaseModel):
    """Base notification channel schema."""
    
    channel_type: str = Field(..., description="Channel type")
    is_enabled: bool = Field(True, description="Whether channel is enabled")
    configuration: Dict[str, Any] = Field(..., description="Channel configuration")
    
    @validator('channel_type')
    def validate_channel_type(cls, v):
        """Validate channel type."""
        if v not in ['email', 'push', 'sms', 'webhook', 'slack']:
            raise ValueError('Channel type must be one of: email, push, sms, webhook, slack')
        return v


class NotificationChannelCreate(NotificationChannelBase):
    """Notification channel creation schema."""
    
    user_id: UUID = Field(..., description="User ID")


class NotificationChannelUpdate(BaseModel):
    """Notification channel update schema."""
    
    is_enabled: Optional[bool] = Field(None, description="Whether channel is enabled")
    configuration: Optional[Dict[str, Any]] = Field(None, description="Channel configuration")


class NotificationChannel(BaseSchema, UUIDSchema, NotificationChannelBase, TimestampSchema):
    """Notification channel response schema."""
    
    user_id: UUID = Field(..., description="User ID")
    last_used_at: Optional[datetime] = Field(None, description="Last time channel was used")
    failure_count: int = Field(0, description="Number of consecutive failures")


# Notification Delivery Schemas
class NotificationDeliveryBase(BaseModel):
    """Base notification delivery schema."""
    
    notification_id: UUID = Field(..., description="Notification ID")
    channel_type: str = Field(..., description="Delivery channel type")
    status: str = Field(..., description="Delivery status")
    attempt_count: int = Field(1, description="Number of delivery attempts")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    delivered_at: Optional[datetime] = Field(None, description="Delivery timestamp")
    
    @validator('status')
    def validate_status(cls, v):
        """Validate delivery status."""
        if v not in ['pending', 'sent', 'delivered', 'failed', 'bounced']:
            raise ValueError('Status must be one of: pending, sent, delivered, failed, bounced')
        return v


class NotificationDeliveryCreate(NotificationDeliveryBase):
    """Notification delivery creation schema."""
    pass


class NotificationDelivery(BaseSchema, UUIDSchema, NotificationDeliveryBase, TimestampSchema):
    """Notification delivery response schema."""
    pass


# Notification Statistics Schemas
class NotificationStatistics(BaseModel):
    """Notification statistics schema."""
    
    user_id: UUID = Field(..., description="User ID")
    total_notifications: int = Field(..., description="Total notifications received")
    unread_notifications: int = Field(..., description="Unread notifications")
    notifications_today: int = Field(..., description="Notifications received today")
    notifications_this_week: int = Field(..., description="Notifications received this week")
    notifications_by_type: Dict[str, int] = Field(..., description="Notifications by type")
    notifications_by_priority: Dict[str, int] = Field(..., description="Notifications by priority")
    average_read_time: Optional[float] = Field(None, description="Average time to read (minutes)")
    most_active_hours: List[int] = Field(..., description="Hours with most notifications")


# Bulk Notification Schemas
class BulkNotificationRequest(BaseModel):
    """Bulk notification request schema."""
    
    user_ids: List[UUID] = Field(..., min_items=1, max_items=1000, description="Target user IDs")
    title: str = Field(..., max_length=200, description="Notification title")
    message: str = Field(..., max_length=1000, description="Notification message")
    notification_type: str = Field(..., description="Type of notification")
    priority: str = Field("normal", description="Notification priority")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional notification data")
    scheduled_for: Optional[datetime] = Field(None, description="Schedule for later")


class BulkNotificationResult(BaseModel):
    """Bulk notification result schema."""
    
    total_requested: int = Field(..., description="Total notifications requested")
    successful: int = Field(..., description="Successfully created notifications")
    failed: int = Field(..., description="Failed notifications")
    errors: List[str] = Field(..., description="Error messages")


# Notification Digest Schemas
class NotificationDigest(BaseModel):
    """Notification digest schema."""
    
    user_id: UUID = Field(..., description="User ID")
    digest_date: str = Field(..., description="Digest date (YYYY-MM-DD)")
    total_notifications: int = Field(..., description="Total notifications in digest")
    notifications_by_type: Dict[str, int] = Field(..., description="Notifications by type")
    high_priority_count: int = Field(..., description="High priority notifications")
    unread_count: int = Field(..., description="Unread notifications")
    summary: str = Field(..., description="Digest summary")
    notifications: List[Notification] = Field(..., description="Digest notifications")


# Paginated Notification Responses
class PaginatedNotificationsResponse(PaginatedResponse):
    """Paginated notifications response."""
    
    items: List[Notification]


class PaginatedNotificationTemplatesResponse(PaginatedResponse):
    """Paginated notification templates response."""
    
    items: List[NotificationTemplate]


class PaginatedNotificationChannelsResponse(PaginatedResponse):
    """Paginated notification channels response."""
    
    items: List[NotificationChannel]