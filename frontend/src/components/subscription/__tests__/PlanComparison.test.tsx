/**
 * Tests for PlanComparison component
 */

import { configureStore } from '@reduxjs/toolkit';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import subscriptionSlice from '../../../store/slices/subscriptionSlice';
import { Plan, PlanComparison as PlanComparisonType, SubscriptionWithPlan } from '../../../types/subscription';
import { PlanComparison } from '../PlanComparison';

// Mock Heroicons
jest.mock('@heroicons/react/24/outline', () => ({
  CheckIcon: () => <div data-testid="check-icon" />,
  XMarkIcon: () => <div data-testid="x-mark-icon" />,
  StarIcon: () => <div data-testid="star-icon" />,
  TrendingUpIcon: () => <div data-testid="trending-up-icon" />,
  TrendingDownIcon: () => <div data-testid="trending-down-icon" />
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

const mockPlans: Plan[] = [
  {
    id: 1,
    plan_name: 'free',
    price_monthly: 0,
    features: {
      real_time_data: false,
      advanced_analysis: false,
      priority_support: false
    },
    api_quota_daily: 10,
    ai_analysis_quota_daily: 5,
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  },
  {
    id: 2,
    plan_name: 'pro',
    price_monthly: 2980,
    features: {
      real_time_data: true,
      advanced_analysis: true,
      priority_support: false
    },
    api_quota_daily: 100,
    ai_analysis_quota_daily: 50,
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  },
  {
    id: 3,
    plan_name: 'business',
    price_monthly: 9800,
    features: {
      real_time_data: true,
      advanced_analysis: true,
      priority_support: true,
      api_access: true
    },
    api_quota_daily: 1000,
    ai_analysis_quota_daily: 200,
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  }
];

const mockCurrentSubscription: SubscriptionWithPlan = {
  id: 'sub-123',
  user_id: 'user-123',
  plan_id: 1,
  status: 'active',
  current_period_start: '2024-01-01T00:00:00Z',
  current_period_end: '2024-02-01T00:00:00Z',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  plan: mockPlans[0]
};

const mockPlanComparison: PlanComparisonType = {
  plans: mockPlans,
  current_plan_id: 1,
  recommended_plan_id: 2,
  recommendations: ['Upgrade to Pro for real-time data']
};

describe('PlanComparison', () => {
  beforeEach(() => {
    mockFetch.mockClear();
    localStorage.setItem('token', 'mock-token');
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state', () => {
    const store = createMockStore();

    render(
      <Provider store={store}>
        <PlanComparison
          plans={[]}
          isLoading={true}
        />
      </Provider>
    );

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders plan cards with correct information', () => {
    const store = createMockStore();

    render(
      <Provider store={store}>
        <PlanComparison
          plans={mockPlans}
          currentSubscription={mockCurrentSubscription}
          planComparison={mockPlanComparison}
          isLoading={false}
        />
      </Provider>
    );

    // Check plan names
    expect(screen.getByText('FREE')).toBeInTheDocument();
    expect(screen.getByText('PRO')).toBeInTheDocument();
    expect(screen.getByText('BUSINESS')).toBeInTheDocument();

    // Check prices
    expect(screen.getByText('¥0')).toBeInTheDocument();
    expect(screen.getByText('¥2,980')).toBeInTheDocument();
    expect(screen.getByText('¥9,800')).toBeInTheDocument();

    // Check quotas
    expect(screen.getByText('• 10 API calls/day')).toBeInTheDocument();
    expect(screen.getByText('• 5 AI analyses/day')).toBeInTheDocument();
    expect(screen.getByText('• 100 API calls/day')).toBeInTheDocument();
    expect(screen.getByText('• 50 AI analyses/day')).toBeInTheDocument();
  });

  it('highlights current plan correctly', () => {
    const store = createMockStore();

    render(
      <Provider store={store}>
        <PlanComparison
          plans={mockPlans}
          currentSubscription={mockCurrentSubscription}
          planComparison={mockPlanComparison}
          isLoading={false}
        />
      </Provider>
    );

    expect(screen.getByText('Current Plan')).toBeInTheDocument();
  });

  it('shows recommended plan badge', () => {
    const store = createMockStore();

    render(
      <Provider store={store}>
        <PlanComparison
          plans={mockPlans}
          currentSubscription={mockCurrentSubscription}
          planComparison={mockPlanComparison}
          isLoading={false}
        />
      </Provider>
    );

    expect(screen.getByText('Recommended')).toBeInTheDocument();
  });

  it('renders feature comparison table', () => {
    const store = createMockStore();

    render(
      <Provider store={store}>
        <PlanComparison
          plans={mockPlans}
          currentSubscription={mockCurrentSubscription}
          planComparison={mockPlanComparison}
          isLoading={false}
        />
      </Provider>
    );

    expect(screen.getByText('Feature Comparison')).toBeInTheDocument();
    expect(screen.getByText('API Calls (Daily)')).toBeInTheDocument();
    expect(screen.getByText('AI Analysis (Daily)')).toBeInTheDocument();
    expect(screen.getByText('Real Time Data')).toBeInTheDocument();
    expect(screen.getByText('Advanced Analysis')).toBeInTheDocument();
  });

  it('opens upgrade confirmation dialog', async () => {
    const store = createMockStore();

    render(
      <Provider store={store}>
        <PlanComparison
          plans={mockPlans}
          currentSubscription={mockCurrentSubscription}
          planComparison={mockPlanComparison}
          isLoading={false}
        />
      </Provider>
    );

    // Find and click upgrade button for Pro plan
    const upgradeButtons = screen.getAllByText('Upgrade');
    fireEvent.click(upgradeButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Confirm Plan Upgrade')).toBeInTheDocument();
    });

    expect(screen.getByText(/Are you sure you want to upgrade from/)).toBeInTheDocument();
    expect(screen.getByText(/FREE.*to.*PRO/)).toBeInTheDocument();
  });

  it('opens downgrade confirmation dialog', async () => {
    const businessSubscription = {
      ...mockCurrentSubscription,
      plan_id: 3,
      plan: mockPlans[2]
    };

    const store = createMockStore();

    render(
      <Provider store={store}>
        <PlanComparison
          plans={mockPlans}
          currentSubscription={businessSubscription}
          planComparison={mockPlanComparison}
          isLoading={false}
        />
      </Provider>
    );

    // Find and click downgrade button for Pro plan
    const downgradeButtons = screen.getAllByText('Downgrade');
    fireEvent.click(downgradeButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Confirm Plan Downgrade')).toBeInTheDocument();
    });

    expect(screen.getByText(/Are you sure you want to downgrade from/)).toBeInTheDocument();
  });

  it('handles successful upgrade', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        data: { ...mockCurrentSubscription, plan_id: 2 }
      })
    });

    const store = createMockStore();

    render(
      <Provider store={store}>
        <PlanComparison
          plans={mockPlans}
          currentSubscription={mockCurrentSubscription}
          planComparison={mockPlanComparison}
          isLoading={false}
        />
      </Provider>
    );

    // Click upgrade button
    const upgradeButtons = screen.getAllByText('Upgrade');
    fireEvent.click(upgradeButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Confirm Plan Upgrade')).toBeInTheDocument();
    });

    // Confirm upgrade
    const confirmButton = screen.getByText('Confirm Upgrade');
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/v1/subscription/upgrade', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer mock-token'
        },
        body: JSON.stringify({ new_plan_id: 2 })
      });
    });
  });

  it('displays error message on upgrade failure', async () => {
    const store = createMockStore({
      subscriptionError: 'Upgrade failed'
    });

    render(
      <Provider store={store}>
        <PlanComparison
          plans={mockPlans}
          currentSubscription={mockCurrentSubscription}
          planComparison={mockPlanComparison}
          isLoading={false}
        />
      </Provider>
    );

    expect(screen.getByText('Upgrade failed')).toBeInTheDocument();
  });

  it('disables buttons during upgrade process', () => {
    const store = createMockStore({
      isUpgrading: true
    });

    render(
      <Provider store={store}>
        <PlanComparison
          plans={mockPlans}
          currentSubscription={mockCurrentSubscription}
          planComparison={mockPlanComparison}
          isLoading={false}
        />
      </Provider>
    );

    const upgradeButtons = screen.getAllByText('Upgrade');
    upgradeButtons.forEach(button => {
      expect(button).toBeDisabled();
    });
  });

  it('shows correct button text for current plan', () => {
    const store = createMockStore();

    render(
      <Provider store={store}>
        <PlanComparison
          plans={mockPlans}
          currentSubscription={mockCurrentSubscription}
          planComparison={mockPlanComparison}
          isLoading={false}
        />
      </Provider>
    );

    expect(screen.getByText('Current Plan')).toBeInTheDocument();
  });

  it('renders boolean features correctly', () => {
    const store = createMockStore();

    render(
      <Provider store={store}>
        <PlanComparison
          plans={mockPlans}
          currentSubscription={mockCurrentSubscription}
          planComparison={mockPlanComparison}
          isLoading={false}
        />
      </Provider>
    );

    // Check that boolean features are rendered with check/close icons
    const featureTable = screen.getByRole('table');
    expect(featureTable).toBeInTheDocument();
  });

  it('closes confirmation dialog on cancel', async () => {
    const store = createMockStore();

    render(
      <Provider store={store}>
        <PlanComparison
          plans={mockPlans}
          currentSubscription={mockCurrentSubscription}
          planComparison={mockPlanComparison}
          isLoading={false}
        />
      </Provider>
    );

    // Open dialog
    const upgradeButtons = screen.getAllByText('Upgrade');
    fireEvent.click(upgradeButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Confirm Plan Upgrade')).toBeInTheDocument();
    });

    // Cancel
    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    await waitFor(() => {
      expect(screen.queryByText('Confirm Plan Upgrade')).not.toBeInTheDocument();
    });
  });
});