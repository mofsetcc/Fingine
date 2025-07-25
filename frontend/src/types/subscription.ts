/**
 * Subscription TypeScript interfaces
 */

import { BaseEntity, Timestamp, UUID } from './base';

// Plan Types
export interface Plan extends BaseEntity {
  id: number;
  plan_name: string;
  price_monthly: number; // in Japanese Yen
  features: Record<string, any>;
  api_quota_daily: number;
  ai_analysis_quota_daily: number;
  is_active: boolean;
}

export interface PlanCreate {
  plan_name: string;
  price_monthly: number;
  features?: Record<string, any>;
  api_quota_daily?: number;
  ai_analysis_quota_daily?: number;
  is_active?: boolean;
}

export interface PlanUpdate {
  plan_name?: string;
  price_monthly?: number;
  features?: Record<string, any>;
  api_quota_daily?: number;
  ai_analysis_quota_daily?: number;
  is_active?: boolean;
}

// Subscription Types
export type SubscriptionStatus = 'active' | 'inactive' | 'cancelled' | 'expired';

export interface Subscription extends BaseEntity {
  user_id: UUID;
  plan_id: number;
  status: SubscriptionStatus;
  current_period_start: Timestamp;
  current_period_end: Timestamp;
  plan?: Plan;
}

export interface SubscriptionCreate {
  plan_id: number;
  payment_method_id?: string;
}

export interface SubscriptionUpdate {
  plan_id?: number;
  status?: SubscriptionStatus;
}

export interface SubscriptionWithPlan extends Subscription {
  plan: Plan;
}

// Usage and Quota Types
export interface UsageQuota {
  api_calls_today: number;
  api_quota_daily: number;
  ai_analysis_today: number;
  ai_analysis_quota_daily: number;
  quota_reset_at: Timestamp;
  api_calls_remaining: number;
  ai_analysis_remaining: number;
  api_quota_percentage: number;
  ai_quota_percentage: number;
}

export interface UsageHistory {
  date: string; // YYYY-MM-DD
  api_calls: number;
  ai_analyses: number;
  cost_usd?: number;
}

// Billing Types
export interface BillingInfo {
  customer_id?: string;
  payment_method_id?: string;
  billing_email?: string;
  next_billing_date?: Timestamp;
  billing_amount?: number; // in JPY
}

export interface Invoice {
  id: string;
  subscription_id: UUID;
  amount: number; // in Japanese Yen
  currency: string;
  status: string;
  created_at: Timestamp;
  due_date?: Timestamp;
  paid_at?: Timestamp;
  invoice_url?: string;
}

// Plan Comparison Types
export interface PlanComparison {
  plans: Plan[];
  current_plan_id?: number;
  recommendations: string[];
}

// Subscription Analytics Types
export interface SubscriptionAnalytics {
  total_subscribers: number;
  active_subscribers: number;
  plan_distribution: Record<string, number>;
  monthly_revenue: number; // in JPY
  churn_rate: number;
  growth_rate: number;
}

// Subscription Form Types
export interface SubscriptionFormData {
  plan_id: number;
  payment_method: 'credit_card' | 'bank_transfer' | 'paypal';
  billing_cycle: 'monthly' | 'yearly';
  auto_renew: boolean;
}

export interface PaymentMethodFormData {
  type: 'credit_card' | 'bank_account';
  card_number?: string;
  expiry_month?: string;
  expiry_year?: string;
  cvv?: string;
  cardholder_name?: string;
  bank_account_number?: string;
  bank_code?: string;
  account_holder_name?: string;
  billing_address: {
    line1: string;
    line2?: string;
    city: string;
    state: string;
    postal_code: string;
    country: string;
  };
}

export interface BillingAddressFormData {
  line1: string;
  line2?: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  is_default: boolean;
}

// Subscription State Types (for Redux/Context)
export interface SubscriptionState {
  // Current subscription
  currentSubscription?: SubscriptionWithPlan;
  
  // Available plans
  plans: Plan[];
  
  // Usage and quotas
  usageQuota?: UsageQuota;
  usageHistory: UsageHistory[];
  
  // Billing information
  billingInfo?: BillingInfo;
  invoices: Invoice[];
  
  // Plan comparison
  planComparison?: PlanComparison;
  
  // Payment methods
  paymentMethods: PaymentMethod[];
  defaultPaymentMethod?: PaymentMethod;
  
  // Loading states
  isLoadingSubscription: boolean;
  isLoadingPlans: boolean;
  isLoadingUsage: boolean;
  isLoadingBilling: boolean;
  isLoadingInvoices: boolean;
  isLoadingPaymentMethods: boolean;
  
  // Error states
  subscriptionError?: string;
  plansError?: string;
  usageError?: string;
  billingError?: string;
  invoicesError?: string;
  paymentMethodsError?: string;
  
  // Operation states
  isUpgrading: boolean;
  isDowngrading: boolean;
  isCancelling: boolean;
  isAddingPaymentMethod: boolean;
  isUpdatingBilling: boolean;
  
  // UI state
  selectedPlanId?: number;
  showPlanComparison: boolean;
  showUsageDetails: boolean;
  
  // Last updated timestamps
  lastUpdated: {
    subscription?: Timestamp;
    plans?: Timestamp;
    usage?: Timestamp;
    billing?: Timestamp;
    invoices?: Timestamp;
    paymentMethods?: Timestamp;
  };
}

// Payment Method Types
export interface PaymentMethod {
  id: string;
  type: 'credit_card' | 'bank_account' | 'paypal';
  is_default: boolean;
  
  // Credit card specific
  card_brand?: string;
  card_last4?: string;
  card_exp_month?: number;
  card_exp_year?: number;
  
  // Bank account specific
  bank_name?: string;
  account_last4?: string;
  
  // Common
  billing_address?: BillingAddress;
  created_at: Timestamp;
  updated_at: Timestamp;
}

export interface BillingAddress {
  line1: string;
  line2?: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
}

// Subscription Events Types
export interface SubscriptionEvent {
  id: UUID;
  subscription_id: UUID;
  event_type: SubscriptionEventType;
  event_data: Record<string, any>;
  created_at: Timestamp;
}

export type SubscriptionEventType = 
  | 'subscription_created'
  | 'subscription_updated'
  | 'subscription_cancelled'
  | 'subscription_renewed'
  | 'plan_upgraded'
  | 'plan_downgraded'
  | 'payment_succeeded'
  | 'payment_failed'
  | 'invoice_created'
  | 'invoice_paid'
  | 'quota_exceeded'
  | 'quota_reset';

// Subscription Notifications Types
export interface SubscriptionNotification {
  id: UUID;
  user_id: UUID;
  notification_type: SubscriptionNotificationType;
  title: string;
  message: string;
  is_read: boolean;
  created_at: Timestamp;
}

export type SubscriptionNotificationType = 
  | 'payment_due'
  | 'payment_failed'
  | 'subscription_expiring'
  | 'quota_warning'
  | 'quota_exceeded'
  | 'plan_upgrade_available'
  | 'billing_update_required';

// Subscription Metrics Types
export interface SubscriptionMetrics {
  user_id: UUID;
  current_period: {
    api_calls: number;
    ai_analyses: number;
    cost_usd: number;
    days_remaining: number;
  };
  historical: {
    total_api_calls: number;
    total_ai_analyses: number;
    total_cost_usd: number;
    subscription_duration_days: number;
    average_daily_usage: {
      api_calls: number;
      ai_analyses: number;
    };
  };
  projections: {
    monthly_api_calls: number;
    monthly_ai_analyses: number;
    monthly_cost_usd: number;
    recommended_plan?: string;
  };
}

// Subscription Upgrade/Downgrade Types
export interface PlanChangeRequest {
  new_plan_id: number;
  change_type: 'upgrade' | 'downgrade';
  effective_date: 'immediate' | 'next_billing_cycle';
  proration_amount?: number;
  reason?: string;
}

export interface PlanChangePreview {
  current_plan: Plan;
  new_plan: Plan;
  change_type: 'upgrade' | 'downgrade';
  proration_amount: number;
  next_billing_amount: number;
  effective_date: Timestamp;
  feature_changes: {
    added: string[];
    removed: string[];
    modified: Array<{
      feature: string;
      old_value: any;
      new_value: any;
    }>;
  };
}

// Subscription Cancellation Types
export interface CancellationRequest {
  reason: string;
  feedback?: string;
  effective_date: 'immediate' | 'end_of_period';
  cancel_immediately: boolean;
}

export interface CancellationPreview {
  effective_date: Timestamp;
  refund_amount: number;
  access_until: Timestamp;
  data_retention_period: number; // days
  reactivation_deadline?: Timestamp;
}

// Subscription Renewal Types
export interface RenewalInfo {
  next_renewal_date: Timestamp;
  renewal_amount: number;
  auto_renew_enabled: boolean;
  payment_method_valid: boolean;
  renewal_warnings: string[];
}

// Subscription Discount Types
export interface Discount {
  id: string;
  code: string;
  type: 'percentage' | 'fixed_amount';
  value: number;
  description: string;
  valid_from: Timestamp;
  valid_until: Timestamp;
  max_uses?: number;
  current_uses: number;
  applicable_plans: number[];
  is_active: boolean;
}

export interface DiscountApplication {
  discount_id: string;
  subscription_id: UUID;
  applied_at: Timestamp;
  discount_amount: number;
  expires_at?: Timestamp;
}