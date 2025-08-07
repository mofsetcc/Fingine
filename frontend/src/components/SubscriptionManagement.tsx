/**
 * Subscription Management Component
 * Provides subscription upgrade/downgrade interface, billing history, and plan comparison
 */

import {
    ChartBarIcon,
    ClockIcon,
    CogIcon,
    CreditCardIcon,
    ArrowTrendingUpIcon
} from '@heroicons/react/24/outline';
import React, { useEffect, useState } from 'react';

import { useAppDispatch, useAppSelector } from '../store';
import {
    clearErrors,
    fetchCurrentSubscription,
    fetchPlanComparison,
    fetchPlans,
    fetchUsageQuota
} from '../store/slices/subscriptionSlice';

import { BillingHistory } from './subscription/BillingHistory';
import { PlanComparison } from './subscription/PlanComparison';
import { SubscriptionSettings } from './subscription/SubscriptionSettings';
import { UsageOverview } from './subscription/UsageOverview';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`subscription-tabpanel-${index}`}
      aria-labelledby={`subscription-tab-${index}`}
      {...other}
    >
      {value === index && <div className="p-6">{children}</div>}
    </div>
  );
}

export const SubscriptionManagement: React.FC = () => {
  const dispatch = useAppDispatch();
  const {
    currentSubscription,
    plans,
    usageQuota,
    planComparison,
    isLoadingSubscription,
    isLoadingPlans,
    isLoadingUsage,
    subscriptionError,
    plansError,
    usageError
  } = useAppSelector((state) => state.subscription);

  const [activeTab, setActiveTab] = useState(0);

  useEffect(() => {
    // Load initial data
    dispatch(fetchCurrentSubscription());
    dispatch(fetchPlans(true));
    dispatch(fetchUsageQuota());
    dispatch(fetchPlanComparison());

    // Clear any existing errors
    dispatch(clearErrors());
  }, [dispatch]);

  const handleTabChange = (newValue: number) => {
    setActiveTab(newValue);
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'JPY',
      minimumFractionDigits: 0
    }).format(price);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'cancelled':
        return 'bg-red-100 text-red-800';
      case 'expired':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const isLoading = isLoadingSubscription || isLoadingPlans || isLoadingUsage;
  const hasError = subscriptionError || plansError || usageError;

  if (isLoading && !currentSubscription) {
    return (
      <div className="flex justify-center items-center min-h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const tabs = [
    { id: 0, name: 'Plan Comparison', icon: ChartBarIcon },
    { id: 1, name: 'Billing History', icon: ClockIcon },
    { id: 2, name: 'Usage Overview', icon: CreditCardIcon },
    { id: 3, name: 'Settings', icon: CogIcon }
  ];

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">
        Subscription Management
      </h1>

      {hasError && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                Error
              </h3>
              <div className="mt-2 text-sm text-red-700">
                {subscriptionError || plansError || usageError}
              </div>
            </div>
            <div className="ml-auto pl-3">
              <button
                onClick={() => dispatch(clearErrors())}
                className="text-red-400 hover:text-red-600"
              >
                <span className="sr-only">Dismiss</span>
                ×
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Current Subscription Overview */}
      {currentSubscription && (
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
            <div>
              <h2 className="text-lg font-medium text-gray-900 mb-2">
                Current Plan
              </h2>
              <div className="flex items-center gap-3 mb-2">
                <h3 className="text-2xl font-bold text-blue-600">
                  {currentSubscription.plan?.plan_name?.toUpperCase() || 'FREE'}
                </h3>
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(currentSubscription.status)}`}>
                  {currentSubscription.status}
                </span>
              </div>
              <p className="text-xl font-semibold text-gray-700 mb-1">
                {formatPrice(currentSubscription.plan?.price_monthly || 0)}/month
              </p>
              <p className="text-sm text-gray-500">
                Next billing: {new Date(currentSubscription.current_period_end).toLocaleDateString('ja-JP')}
              </p>
            </div>

            <div>
              {usageQuota && (
                <div>
                  <h3 className="text-sm font-medium text-gray-900 mb-3">
                    Usage This Month
                  </h3>
                  
                  <div className="mb-4">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-sm text-gray-600">API Calls</span>
                      <span className="text-sm text-gray-900">
                        {usageQuota.api_calls_today}/{usageQuota.api_quota_daily}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full"
                        style={{ width: `${Math.min(usageQuota.api_quota_percentage, 100)}%` }}
                      ></div>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-sm text-gray-600">AI Analysis</span>
                      <span className="text-sm text-gray-900">
                        {usageQuota.ai_analysis_today}/{usageQuota.ai_analysis_quota_daily}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-purple-600 h-2 rounded-full"
                        style={{ width: `${Math.min(usageQuota.ai_quota_percentage, 100)}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="mt-6 flex gap-3">
            <button
              onClick={() => setActiveTab(0)}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <TrendingUpIcon className="h-4 w-4 mr-2" />
              Upgrade Plan
            </button>
            <button
              onClick={() => setActiveTab(2)}
              className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              View Usage Details
            </button>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="bg-white shadow rounded-lg">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8" aria-label="Tabs">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => handleTabChange(tab.id)}
                  className={`${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center`}
                  id={`subscription-tab-${tab.id}`}
                  aria-controls={`subscription-tabpanel-${tab.id}`}
                >
                  <Icon className="h-5 w-5 mr-2" />
                  {tab.name}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Plan Comparison Tab */}
        <TabPanel value={activeTab} index={0}>
          <PlanComparison
            plans={plans}
            currentSubscription={currentSubscription}
            planComparison={planComparison}
            isLoading={isLoadingPlans}
          />
        </TabPanel>

        {/* Billing History Tab */}
        <TabPanel value={activeTab} index={1}>
          <BillingHistory
            subscription={currentSubscription}
          />
        </TabPanel>

        {/* Usage Overview Tab */}
        <TabPanel value={activeTab} index={2}>
          <UsageOverview
            usageQuota={usageQuota}
            subscription={currentSubscription}
            isLoading={isLoadingUsage}
          />
        </TabPanel>

        {/* Settings Tab */}
        <TabPanel value={activeTab} index={3}>
          <SubscriptionSettings
            subscription={currentSubscription}
          />
        </TabPanel>
      </div>
    </div>
  );
};