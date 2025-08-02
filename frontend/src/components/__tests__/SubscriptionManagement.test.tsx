/**
 * Tests for SubscriptionManagement component
 */

import { configureStore } from '@reduxjs/toolkit';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import subscriptionSlice from '../../store/slices/subscriptionSlice';
import { Plan, SubscriptionWithPlan, UsageQuota } from '../../types/subscription';
import { SubscriptionManagement } from '../SubscriptionManagement';

// Mock Heroicons
jest.mock('@heroicons/react/24/outline', () => ({
  ChartBarIcon: () => <div data-testid="chart-bar-icon" />,
  CreditCardIcon: () => <div data-testid="credit-card-icon" />,
  ClockIcon: () => <div data-testid="clock-icon" />,
  CogIcon: () => <div data-testid="cog-icon" />,
  TrendingUpIcon: () => <div data-testid="trending-up-icon" />
}));

// Mock the subscription sub-components
jest.mock('../subscription/PlanComparison', () => ({
  PlanComparison: ({ plans, currentSubscription }: any) => (
    <div data-testid="plan-comparison">
      Plan Comparison - Plans: {plans.length}, Current: {currentSubscription?.plan?.plan_name}
    </div>
  )
}));

jest.mock('../subscription/BillingHistory', () => ({
  BillingHistory: ({ subscription }: any) => (
    <div data-testid="billing-history">
      Billing History - Subscription: {subscription?.id}
    </div>
  )
}));

jest.mock('../subscription/UsageOverview', () => ({
  UsageOverview: ({ usageQuota, subscription }: any) => (
    <div data-testid="usage-overview">
      Usage Overview - API: {usageQuota?.api_calls_today}, AI: {usageQuota?.ai_analysis_today}
    </div>
  )
}));

jest.mock('../subscription/SubscriptionSettings', () => ({
  SubscriptionSettings: ({ subscription }: any) => (
    <div data-testid="subscription-settings">
      Settings - Status: {subscription?.status}
    </div>
  )
}));

// Mock fetch
global.fetch = jest.fn();

const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

const createMockStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      subscription: subscriptionSlice
    },
    preloadedState: {
      subscription: {
        plans: [],
        usageHistory: [],
        invoices: [],
        paymentMethods: [],
        isLoadingSubscription: false,
        isLoadingPlans: false,
        isLoadingUsage: false,
        isLoadingBilling: false,
        isLoadingInvoices: false,
        isLoadingPaymentMethods: false,
        isUpgrading: false,
        isDowngrading: false,
        isCancelling: false,
        isAddingPaymentMethod: false,
        isUpdatingBilling: false,
        showPlanComparison: false,
        showUsageDetails: false,
        lastUpdated: {},
        ...initialState
      }
    }
  });
};

const mockPlan: Plan = {
  id: 1,
  plan_name: 'pro',
  price_monthly: 2980,
  features: {
    real_time_data: true,
    advanced_analysis: true
  },
  api_quota_daily: 100,
  ai_analysis_quota_daily: 50,
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z'
};

const mockSubscription: SubscriptionWithPlan = {
  id: 'sub-123',
  user_id: 'user-123',
  plan_id: 1,
  status: 'active',
  current_period_start: '2024-01-01T00:00:00Z',
  current_period_end: '2024-02-01T00:00:00Z',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  plan: mockPlan
};

const mockUsageQuota: UsageQuota = {
  api_calls_today: 25,
  api_quota_daily: 100,
  ai_analysis_today: 10,
  ai_analysis_quota_daily: 50,
  quota_reset_at: '2024-01-02T00:00:00Z',
  api_calls_remaining: 75,
  ai_analysis_remaining: 40,
  api_quota_percentage: 25,
  ai_quota_percentage: 20
};

describe('SubscriptionManagement', () => {
  beforeEach(() => {
    mockFetch.mockClear();
    localStorage.setItem('token', 'mock-token');
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    const store = createMockStore({
      isLoadingSubscription: true,
      isLoadingPlans: true,
      isLoadingUsage: true
    });

    render(
      <Provider store={store}>
        <SubscriptionManagement />
      </Provider>
    );

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders subscription management with current subscription', async () => {
    const store = createMockStore({
      currentSubscription: mockSubscription,
      plans: [mockPlan],
      usageQuota: mockUsageQuota,
      isLoadingSubscription: false,
      isLoadingPlans: false,
      isLoadingUsage: false
    });

    render(
      <Provider store={store}>
        <SubscriptionManagement />
      </Provider>
    );

    // Check main heading
    expect(screen.getByText('Subscription Management')).toBeInTheDocument();

    // Check current plan display
    expect(screen.getByText('Current Plan')).toBeInTheDocument();
    expect(screen.getByText('PRO')).toBeInTheDocument();
    expect(screen.getByText('¥2,980/month')).toBeInTheDocument();

    // Check usage display
    expect(screen.getByText('Usage This Month')).toBeInTheDocument();
    expect(screen.getByText('API Calls')).toBeInTheDocument();
    expect(screen.getByText('25/100')).toBeInTheDocument();
    expect(screen.getByText('AI Analysis')).toBeInTheDocument();
    expect(screen.getByText('10/50')).toBeInTheDocument();

    // Check tabs
    expect(screen.getByText('Plan Comparison')).toBeInTheDocument();
    expect(screen.getByText('Billing History')).toBeInTheDocument();
    expect(screen.getByText('Usage Overview')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('displays error message when there is an error', () => {
    const store = createMockStore({
      subscriptionError: 'Failed to load subscription',
      isLoadingSubscription: false
    });

    render(
      <Provider store={store}>
        <SubscriptionManagement />
      </Provider>
    );

    expect(screen.getByText('Failed to load subscription')).toBeInTheDocument();
  });

  it('switches between tabs correctly', async () => {
    const store = createMockStore({
      currentSubscription: mockSubscription,
      plans: [mockPlan],
      usageQuota: mockUsageQuota,
      isLoadingSubscription: false,
      isLoadingPlans: false,
      isLoadingUsage: false
    });

    render(
      <Provider store={store}>
        <SubscriptionManagement />
      </Provider>
    );

    // Initially shows plan comparison
    expect(screen.getByTestId('plan-comparison')).toBeInTheDocument();

    // Click billing history tab
    fireEvent.click(screen.getByText('Billing History'));
    await waitFor(() => {
      expect(screen.getByTestId('billing-history')).toBeInTheDocument();
    });

    // Click usage overview tab
    fireEvent.click(screen.getByText('Usage Overview'));
    await waitFor(() => {
      expect(screen.getByTestId('usage-overview')).toBeInTheDocument();
    });

    // Click settings tab
    fireEvent.click(screen.getByText('Settings'));
    await waitFor(() => {
      expect(screen.getByTestId('subscription-settings')).toBeInTheDocument();
    });
  });

  it('handles upgrade plan button click', async () => {
    const store = createMockStore({
      currentSubscription: mockSubscription,
      plans: [mockPlan],
      usageQuota: mockUsageQuota,
      isLoadingSubscription: false,
      isLoadingPlans: false,
      isLoadingUsage: false
    });

    render(
      <Provider store={store}>
        <SubscriptionManagement />
      </Provider>
    );

    const upgradeButton = screen.getByText('Upgrade Plan');
    fireEvent.click(upgradeButton);

    // Should switch to plan comparison tab
    await waitFor(() => {
      expect(screen.getByTestId('plan-comparison')).toBeInTheDocument();
    });
  });

  it('handles view usage details button click', async () => {
    const store = createMockStore({
      currentSubscription: mockSubscription,
      plans: [mockPlan],
      usageQuota: mockUsageQuota,
      isLoadingSubscription: false,
      isLoadingPlans: false,
      isLoadingUsage: false
    });

    render(
      <Provider store={store}>
        <SubscriptionManagement />
      </Provider>
    );

    const usageButton = screen.getByText('View Usage Details');
    fireEvent.click(usageButton);

    // Should switch to usage overview tab
    await waitFor(() => {
      expect(screen.getByTestId('usage-overview')).toBeInTheDocument();
    });
  });

  it('displays correct status chip colors', () => {
    const activeStore = createMockStore({
      currentSubscription: { ...mockSubscription, status: 'active' },
      isLoadingSubscription: false
    });

    const { rerender } = render(
      <Provider store={activeStore}>
        <SubscriptionManagement />
      </Provider>
    );

    // Check active status
    expect(screen.getByText('active')).toBeInTheDocument();

    // Test cancelled status
    const cancelledStore = createMockStore({
      currentSubscription: { ...mockSubscription, status: 'cancelled' },
      isLoadingSubscription: false
    });

    rerender(
      <Provider store={cancelledStore}>
        <SubscriptionManagement />
      </Provider>
    );

    expect(screen.getByText('cancelled')).toBeInTheDocument();
  });

  it('formats prices correctly in Japanese Yen', () => {
    const store = createMockStore({
      currentSubscription: mockSubscription,
      isLoadingSubscription: false
    });

    render(
      <Provider store={store}>
        <SubscriptionManagement />
      </Provider>
    );

    expect(screen.getByText('¥2,980/month')).toBeInTheDocument();
  });

  it('displays usage progress bars with correct percentages', () => {
    const store = createMockStore({
      currentSubscription: mockSubscription,
      usageQuota: mockUsageQuota,
      isLoadingSubscription: false,
      isLoadingUsage: false
    });

    render(
      <Provider store={store}>
        <SubscriptionManagement />
      </Provider>
    );

    // Check that progress bars are rendered (they have role="progressbar")
    const progressBars = screen.getAllByRole('progressbar');
    expect(progressBars).toHaveLength(2); // One for API calls, one for AI analysis
  });

  it('clears errors when error alert is closed', async () => {
    const store = createMockStore({
      subscriptionError: 'Test error',
      isLoadingSubscription: false
    });

    render(
      <Provider store={store}>
        <SubscriptionManagement />
      </Provider>
    );

    expect(screen.getByText('Test error')).toBeInTheDocument();

    // Find and click the close button on the alert
    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);

    // Error should be cleared from the store
    await waitFor(() => {
      expect(screen.queryByText('Test error')).not.toBeInTheDocument();
    });
  });
});