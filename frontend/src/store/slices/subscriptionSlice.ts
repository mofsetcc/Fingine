/**
 * Subscription Redux slice for managing subscription state
 */

import { createAsyncThunk, createSlice, PayloadAction } from '@reduxjs/toolkit';
import { APIResponse } from '../../types/base';
import {
    CancellationRequest,
    Plan,
    PlanComparison,
    Subscription,
    SubscriptionState,
    SubscriptionWithPlan,
    UsageQuota
} from '../../types/subscription';

// Initial state
const initialState: SubscriptionState = {
  plans: [],
  usageHistory: [],
  invoices: [],
  paymentMethods: [],
  
  // Loading states
  isLoadingSubscription: false,
  isLoadingPlans: false,
  isLoadingUsage: false,
  isLoadingBilling: false,
  isLoadingInvoices: false,
  isLoadingPaymentMethods: false,
  
  // Operation states
  isUpgrading: false,
  isDowngrading: false,
  isCancelling: false,
  isAddingPaymentMethod: false,
  isUpdatingBilling: false,
  
  // UI state
  showPlanComparison: false,
  showUsageDetails: false,
  
  // Last updated timestamps
  lastUpdated: {}
};

// Async thunks
export const fetchPlans = createAsyncThunk(
  'subscription/fetchPlans',
  async (activeOnly: boolean = true) => {
    const response = await fetch(`/api/v1/subscription/plans?active_only=${activeOnly}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch plans');
    }
    
    const data: APIResponse<Plan[]> = await response.json();
    return data.data;
  }
);

export const fetchCurrentSubscription = createAsyncThunk(
  'subscription/fetchCurrentSubscription',
  async () => {
    const response = await fetch('/api/v1/subscription/my-subscription', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch subscription');
    }
    
    const data: APIResponse<SubscriptionWithPlan> = await response.json();
    return data.data;
  }
);

export const fetchUsageQuota = createAsyncThunk(
  'subscription/fetchUsageQuota',
  async () => {
    const response = await fetch('/api/v1/subscription/usage', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch usage quota');
    }
    
    const data: APIResponse<UsageQuota> = await response.json();
    return data.data;
  }
);

export const fetchPlanComparison = createAsyncThunk(
  'subscription/fetchPlanComparison',
  async () => {
    const response = await fetch('/api/v1/subscription/plans/compare', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch plan comparison');
    }
    
    const data: APIResponse<PlanComparison> = await response.json();
    return data.data;
  }
);

export const upgradeSubscription = createAsyncThunk(
  'subscription/upgradeSubscription',
  async (planId: number) => {
    const response = await fetch('/api/v1/subscription/upgrade', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({ new_plan_id: planId })
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to upgrade subscription');
    }
    
    const data: APIResponse<Subscription> = await response.json();
    return data.data;
  }
);

export const downgradeSubscription = createAsyncThunk(
  'subscription/downgradeSubscription',
  async (request: { planId: number; effectiveDate?: string }) => {
    const response = await fetch('/api/v1/subscription/downgrade', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({ 
        new_plan_id: request.planId,
        effective_date: request.effectiveDate
      })
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to downgrade subscription');
    }
    
    const data: APIResponse<Subscription> = await response.json();
    return data.data;
  }
);

export const cancelSubscription = createAsyncThunk(
  'subscription/cancelSubscription',
  async (request: CancellationRequest) => {
    const response = await fetch('/api/v1/subscription/cancel', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify(request)
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to cancel subscription');
    }
    
    const data: APIResponse<Subscription> = await response.json();
    return data.data;
  }
);

// Slice
const subscriptionSlice = createSlice({
  name: 'subscription',
  initialState,
  reducers: {
    clearErrors: (state) => {
      state.subscriptionError = undefined;
      state.plansError = undefined;
      state.usageError = undefined;
      state.billingError = undefined;
      state.invoicesError = undefined;
      state.paymentMethodsError = undefined;
    },
    
    setSelectedPlan: (state, action: PayloadAction<number>) => {
      state.selectedPlanId = action.payload;
    },
    
    togglePlanComparison: (state) => {
      state.showPlanComparison = !state.showPlanComparison;
    },
    
    toggleUsageDetails: (state) => {
      state.showUsageDetails = !state.showUsageDetails;
    },
    
    resetOperationStates: (state) => {
      state.isUpgrading = false;
      state.isDowngrading = false;
      state.isCancelling = false;
      state.isAddingPaymentMethod = false;
      state.isUpdatingBilling = false;
    }
  },
  
  extraReducers: (builder) => {
    // Fetch plans
    builder
      .addCase(fetchPlans.pending, (state) => {
        state.isLoadingPlans = true;
        state.plansError = undefined;
      })
      .addCase(fetchPlans.fulfilled, (state, action) => {
        state.isLoadingPlans = false;
        state.plans = action.payload;
        state.lastUpdated.plans = new Date().toISOString();
      })
      .addCase(fetchPlans.rejected, (state, action) => {
        state.isLoadingPlans = false;
        state.plansError = action.error.message;
      });
    
    // Fetch current subscription
    builder
      .addCase(fetchCurrentSubscription.pending, (state) => {
        state.isLoadingSubscription = true;
        state.subscriptionError = undefined;
      })
      .addCase(fetchCurrentSubscription.fulfilled, (state, action) => {
        state.isLoadingSubscription = false;
        state.currentSubscription = action.payload;
        state.lastUpdated.subscription = new Date().toISOString();
      })
      .addCase(fetchCurrentSubscription.rejected, (state, action) => {
        state.isLoadingSubscription = false;
        state.subscriptionError = action.error.message;
      });
    
    // Fetch usage quota
    builder
      .addCase(fetchUsageQuota.pending, (state) => {
        state.isLoadingUsage = true;
        state.usageError = undefined;
      })
      .addCase(fetchUsageQuota.fulfilled, (state, action) => {
        state.isLoadingUsage = false;
        state.usageQuota = action.payload;
        state.lastUpdated.usage = new Date().toISOString();
      })
      .addCase(fetchUsageQuota.rejected, (state, action) => {
        state.isLoadingUsage = false;
        state.usageError = action.error.message;
      });
    
    // Fetch plan comparison
    builder
      .addCase(fetchPlanComparison.pending, (state) => {
        state.isLoadingPlans = true;
      })
      .addCase(fetchPlanComparison.fulfilled, (state, action) => {
        state.isLoadingPlans = false;
        state.planComparison = action.payload;
        state.plans = action.payload.plans;
      })
      .addCase(fetchPlanComparison.rejected, (state, action) => {
        state.isLoadingPlans = false;
        state.plansError = action.error.message;
      });
    
    // Upgrade subscription
    builder
      .addCase(upgradeSubscription.pending, (state) => {
        state.isUpgrading = true;
        state.subscriptionError = undefined;
      })
      .addCase(upgradeSubscription.fulfilled, (state, action) => {
        state.isUpgrading = false;
        // Refresh subscription data after upgrade
      })
      .addCase(upgradeSubscription.rejected, (state, action) => {
        state.isUpgrading = false;
        state.subscriptionError = action.error.message;
      });
    
    // Downgrade subscription
    builder
      .addCase(downgradeSubscription.pending, (state) => {
        state.isDowngrading = true;
        state.subscriptionError = undefined;
      })
      .addCase(downgradeSubscription.fulfilled, (state, action) => {
        state.isDowngrading = false;
        // Refresh subscription data after downgrade
      })
      .addCase(downgradeSubscription.rejected, (state, action) => {
        state.isDowngrading = false;
        state.subscriptionError = action.error.message;
      });
    
    // Cancel subscription
    builder
      .addCase(cancelSubscription.pending, (state) => {
        state.isCancelling = true;
        state.subscriptionError = undefined;
      })
      .addCase(cancelSubscription.fulfilled, (state, action) => {
        state.isCancelling = false;
        // Refresh subscription data after cancellation
      })
      .addCase(cancelSubscription.rejected, (state, action) => {
        state.isCancelling = false;
        state.subscriptionError = action.error.message;
      });
  }
});

export const {
  clearErrors,
  setSelectedPlan,
  togglePlanComparison,
  toggleUsageDetails,
  resetOperationStates
} = subscriptionSlice.actions;

export default subscriptionSlice.reducer;