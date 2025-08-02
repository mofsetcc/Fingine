/**
 * Plan Comparison Component
 * Shows feature matrix and allows plan upgrades/downgrades
 */

import {
    Check as CheckIcon,
    Close as CloseIcon,
    Star as StarIcon,
    TrendingDown as TrendingDownIcon,
    TrendingUp as TrendingUpIcon
} from '@mui/icons-material';
import {
    Alert,
    Box,
    Button,
    Card,
    CardContent,
    Chip,
    CircularProgress,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    Grid,
    Paper,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Typography
} from '@mui/material';
import React, { useState } from 'react';

import { useAppDispatch, useAppSelector } from '../../store';
import {
    downgradeSubscription,
    fetchCurrentSubscription,
    upgradeSubscription
} from '../../store/slices/subscriptionSlice';

import { Plan, PlanComparison as PlanComparisonType, SubscriptionWithPlan } from '../../types/subscription';

interface PlanComparisonProps {
  plans: Plan[];
  currentSubscription?: SubscriptionWithPlan;
  planComparison?: PlanComparisonType;
  isLoading: boolean;
}

export const PlanComparison: React.FC<PlanComparisonProps> = ({
  plans,
  currentSubscription,
  planComparison,
  isLoading
}) => {
  const dispatch = useAppDispatch();
  const { isUpgrading, isDowngrading, subscriptionError } = useAppSelector(
    (state) => state.subscription
  );

  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [changeType, setChangeType] = useState<'upgrade' | 'downgrade'>('upgrade');

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'JPY',
      minimumFractionDigits: 0
    }).format(price);
  };

  const isCurrentPlan = (planId: number) => {
    return currentSubscription?.plan_id === planId;
  };

  const isRecommended = (planId: number) => {
    return planComparison?.recommended_plan_id === planId;
  };

  const canChangeToPlan = (plan: Plan) => {
    if (!currentSubscription?.plan) return true;
    return plan.id !== currentSubscription.plan.id;
  };

  const getChangeType = (plan: Plan): 'upgrade' | 'downgrade' | null => {
    if (!currentSubscription?.plan) return 'upgrade';
    if (plan.price_monthly > currentSubscription.plan.price_monthly) return 'upgrade';
    if (plan.price_monthly < currentSubscription.plan.price_monthly) return 'downgrade';
    return null;
  };

  const handlePlanSelect = (plan: Plan) => {
    const type = getChangeType(plan);
    if (!type) return;

    setSelectedPlan(plan);
    setChangeType(type);
    setShowConfirmDialog(true);
  };

  const handleConfirmChange = async () => {
    if (!selectedPlan) return;

    try {
      if (changeType === 'upgrade') {
        await dispatch(upgradeSubscription(selectedPlan.id)).unwrap();
      } else {
        await dispatch(downgradeSubscription({ 
          planId: selectedPlan.id 
        })).unwrap();
      }

      // Refresh subscription data
      dispatch(fetchCurrentSubscription());
      setShowConfirmDialog(false);
      setSelectedPlan(null);
    } catch (error) {
      // Error is handled by the slice
      console.error('Failed to change plan:', error);
    }
  };

  const renderFeatureValue = (value: any) => {
    if (typeof value === 'boolean') {
      return value ? (
        <CheckIcon color="success" />
      ) : (
        <CloseIcon color="disabled" />
      );
    }
    return value?.toString() || '-';
  };

  // Get all unique feature keys
  const allFeatures = Array.from(
    new Set(
      plans.flatMap(plan => Object.keys(plan.features || {}))
    )
  );

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="300px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Choose Your Plan
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Compare features and select the plan that best fits your needs.
      </Typography>

      {subscriptionError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {subscriptionError}
        </Alert>
      )}

      {/* Plan Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {plans.map((plan) => (
          <Grid item xs={12} md={4} key={plan.id}>
            <Card
              sx={{
                height: '100%',
                position: 'relative',
                border: isCurrentPlan(plan.id) ? 2 : 1,
                borderColor: isCurrentPlan(plan.id) ? 'primary.main' : 'divider',
                ...(isRecommended(plan.id) && {
                  boxShadow: 3,
                  '&::before': {
                    content: '"Recommended"',
                    position: 'absolute',
                    top: -10,
                    left: '50%',
                    transform: 'translateX(-50%)',
                    backgroundColor: 'warning.main',
                    color: 'warning.contrastText',
                    px: 2,
                    py: 0.5,
                    borderRadius: 1,
                    fontSize: '0.75rem',
                    fontWeight: 'bold'
                  }
                })
              }}
            >
              <CardContent sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
                <Box sx={{ textAlign: 'center', mb: 3 }}>
                  <Typography variant="h5" component="h3" gutterBottom>
                    {plan.plan_name.toUpperCase()}
                  </Typography>
                  <Typography variant="h3" color="primary" gutterBottom>
                    {formatPrice(plan.price_monthly)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    per month
                  </Typography>
                  
                  {isCurrentPlan(plan.id) && (
                    <Chip
                      label="Current Plan"
                      color="primary"
                      size="small"
                      sx={{ mt: 1 }}
                    />
                  )}
                  
                  {isRecommended(plan.id) && !isCurrentPlan(plan.id) && (
                    <Chip
                      label="Recommended"
                      color="warning"
                      size="small"
                      icon={<StarIcon />}
                      sx={{ mt: 1 }}
                    />
                  )}
                </Box>

                <Box sx={{ mb: 3, flexGrow: 1 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Quotas
                  </Typography>
                  <Typography variant="body2" sx={{ mb: 1 }}>
                    • {plan.api_quota_daily} API calls/day
                  </Typography>
                  <Typography variant="body2" sx={{ mb: 2 }}>
                    • {plan.ai_analysis_quota_daily} AI analyses/day
                  </Typography>

                  <Typography variant="subtitle2" gutterBottom>
                    Features
                  </Typography>
                  {Object.entries(plan.features || {}).map(([key, value]) => (
                    <Box key={key} display="flex" alignItems="center" sx={{ mb: 0.5 }}>
                      {typeof value === 'boolean' ? (
                        value ? <CheckIcon color="success" sx={{ mr: 1, fontSize: 16 }} /> : 
                               <CloseIcon color="disabled" sx={{ mr: 1, fontSize: 16 }} />
                      ) : (
                        <CheckIcon color="success" sx={{ mr: 1, fontSize: 16 }} />
                      )}
                      <Typography variant="body2">
                        {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        {typeof value !== 'boolean' && `: ${value}`}
                      </Typography>
                    </Box>
                  ))}
                </Box>

                <Button
                  variant={isCurrentPlan(plan.id) ? "outlined" : "contained"}
                  fullWidth
                  disabled={!canChangeToPlan(plan) || isUpgrading || isDowngrading}
                  onClick={() => handlePlanSelect(plan)}
                  startIcon={
                    isCurrentPlan(plan.id) ? null :
                    getChangeType(plan) === 'upgrade' ? <TrendingUpIcon /> : <TrendingDownIcon />
                  }
                >
                  {isCurrentPlan(plan.id) 
                    ? 'Current Plan' 
                    : getChangeType(plan) === 'upgrade' 
                      ? 'Upgrade' 
                      : 'Downgrade'
                  }
                </Button>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Feature Comparison Table */}
      <Typography variant="h6" gutterBottom>
        Feature Comparison
      </Typography>
      
      <TableContainer component={Paper} sx={{ mb: 3 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Feature</TableCell>
              {plans.map((plan) => (
                <TableCell key={plan.id} align="center">
                  <Box>
                    <Typography variant="subtitle2">
                      {plan.plan_name.toUpperCase()}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {formatPrice(plan.price_monthly)}
                    </Typography>
                  </Box>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            <TableRow>
              <TableCell component="th" scope="row">
                <strong>API Calls (Daily)</strong>
              </TableCell>
              {plans.map((plan) => (
                <TableCell key={plan.id} align="center">
                  {plan.api_quota_daily.toLocaleString()}
                </TableCell>
              ))}
            </TableRow>
            <TableRow>
              <TableCell component="th" scope="row">
                <strong>AI Analysis (Daily)</strong>
              </TableCell>
              {plans.map((plan) => (
                <TableCell key={plan.id} align="center">
                  {plan.ai_analysis_quota_daily.toLocaleString()}
                </TableCell>
              ))}
            </TableRow>
            {allFeatures.map((feature) => (
              <TableRow key={feature}>
                <TableCell component="th" scope="row">
                  {feature.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </TableCell>
                {plans.map((plan) => (
                  <TableCell key={plan.id} align="center">
                    {renderFeatureValue(plan.features?.[feature])}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Confirmation Dialog */}
      <Dialog open={showConfirmDialog} onClose={() => setShowConfirmDialog(false)}>
        <DialogTitle>
          Confirm Plan {changeType === 'upgrade' ? 'Upgrade' : 'Downgrade'}
        </DialogTitle>
        <DialogContent>
          {selectedPlan && currentSubscription?.plan && (
            <Box>
              <Typography paragraph>
                Are you sure you want to {changeType} from{' '}
                <strong>{currentSubscription.plan.plan_name.toUpperCase()}</strong> to{' '}
                <strong>{selectedPlan.plan_name.toUpperCase()}</strong>?
              </Typography>
              
              <Box sx={{ my: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Price Change:
                </Typography>
                <Typography>
                  {formatPrice(currentSubscription.plan.price_monthly)} → {formatPrice(selectedPlan.price_monthly)}
                  {changeType === 'upgrade' && (
                    <Typography component="span" color="success.main">
                      {' '}(+{formatPrice(selectedPlan.price_monthly - currentSubscription.plan.price_monthly)})
                    </Typography>
                  )}
                  {changeType === 'downgrade' && (
                    <Typography component="span" color="info.main">
                      {' '}(-{formatPrice(currentSubscription.plan.price_monthly - selectedPlan.price_monthly)})
                    </Typography>
                  )}
                </Typography>
              </Box>

              <Box sx={{ my: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Quota Changes:
                </Typography>
                <Typography variant="body2">
                  API Calls: {currentSubscription.plan.api_quota_daily} → {selectedPlan.api_quota_daily}
                </Typography>
                <Typography variant="body2">
                  AI Analysis: {currentSubscription.plan.ai_analysis_quota_daily} → {selectedPlan.ai_analysis_quota_daily}
                </Typography>
              </Box>

              {changeType === 'upgrade' && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  Your plan will be upgraded immediately and you'll be charged the prorated amount.
                </Alert>
              )}

              {changeType === 'downgrade' && (
                <Alert severity="warning" sx={{ mt: 2 }}>
                  Your plan will be downgraded at the end of your current billing period.
                </Alert>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowConfirmDialog(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirmChange}
            variant="contained"
            disabled={isUpgrading || isDowngrading}
            startIcon={
              (isUpgrading || isDowngrading) ? <CircularProgress size={16} /> : 
              changeType === 'upgrade' ? <TrendingUpIcon /> : <TrendingDownIcon />
            }
          >
            Confirm {changeType === 'upgrade' ? 'Upgrade' : 'Downgrade'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};