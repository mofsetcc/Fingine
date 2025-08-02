/**
 * Subscription Settings Component
 * Handles subscription cancellation and other settings
 */

import {
    Cancel as CancelIcon,
    ExpandMore as ExpandMoreIcon,
    Info as InfoIcon,
    Schedule as ScheduleIcon,
    Warning as WarningIcon
} from '@mui/icons-material';
import {
    Accordion,
    AccordionDetails,
    AccordionSummary,
    Alert,
    Box,
    Button,
    Card,
    CardContent,
    Chip,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    Divider,
    FormControl,
    FormControlLabel,
    FormLabel,
    Grid,
    Radio,
    RadioGroup,
    TextField,
    Typography
} from '@mui/material';
import React, { useState } from 'react';

import { useAppDispatch, useAppSelector } from '../../store';
import { cancelSubscription, fetchCurrentSubscription } from '../../store/slices/subscriptionSlice';
import { CancellationRequest, SubscriptionWithPlan } from '../../types/subscription';

interface SubscriptionSettingsProps {
  subscription?: SubscriptionWithPlan;
}

export const SubscriptionSettings: React.FC<SubscriptionSettingsProps> = ({
  subscription
}) => {
  const dispatch = useAppDispatch();
  const { isCancelling, subscriptionError } = useAppSelector(
    (state) => state.subscription
  );

  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const [cancelForm, setCancelForm] = useState<CancellationRequest>({
    reason: '',
    feedback: '',
    effective_date: 'end_of_period',
    cancel_immediately: false
  });

  const handleCancelSubscription = async () => {
    try {
      await dispatch(cancelSubscription(cancelForm)).unwrap();
      dispatch(fetchCurrentSubscription());
      setShowCancelDialog(false);
      setCancelForm({
        reason: '',
        feedback: '',
        effective_date: 'end_of_period',
        cancel_immediately: false
      });
    } catch (error) {
      // Error is handled by the slice
      console.error('Failed to cancel subscription:', error);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ja-JP');
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'JPY',
      minimumFractionDigits: 0
    }).format(price);
  };

  const cancellationReasons = [
    'Too expensive',
    'Not using enough features',
    'Found a better alternative',
    'Technical issues',
    'Poor customer service',
    'No longer need the service',
    'Other'
  ];

  if (!subscription) {
    return (
      <Alert severity="info">
        No active subscription found.
      </Alert>
    );
  }

  const isActive = subscription.status === 'active';
  const isCancelled = subscription.status === 'cancelled';

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Subscription Settings
      </Typography>

      {subscriptionError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {subscriptionError}
        </Alert>
      )}

      {/* Subscription Status */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle1" gutterBottom>
                Current Status
              </Typography>
              <Box display="flex" alignItems="center" gap={2} sx={{ mb: 2 }}>
                <Chip
                  label={subscription.status.toUpperCase()}
                  color={isActive ? 'success' : isCancelled ? 'error' : 'default'}
                />
                <Typography variant="body2" color="text.secondary">
                  {subscription.plan?.plan_name?.toUpperCase() || 'FREE'} Plan
                </Typography>
              </Box>
              
              <Typography variant="body2" color="text.secondary">
                Current period: {formatDate(subscription.current_period_start)} - {formatDate(subscription.current_period_end)}
              </Typography>
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography variant="subtitle1" gutterBottom>
                Billing Information
              </Typography>
              <Typography variant="h6" color="primary" sx={{ mb: 1 }}>
                {formatPrice(subscription.plan?.price_monthly || 0)}/month
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Next billing: {formatDate(subscription.current_period_end)}
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Settings Accordions */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center">
            <ScheduleIcon sx={{ mr: 1 }} />
            <Typography>Auto-Renewal Settings</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Alert severity="info" sx={{ mb: 2 }}>
            Your subscription will automatically renew at the end of each billing period unless cancelled.
          </Alert>
          <Typography variant="body2" color="text.secondary" paragraph>
            Auto-renewal ensures uninterrupted access to your plan features. You can cancel at any time 
            before your next billing date to avoid charges.
          </Typography>
          <Typography variant="body2">
            <strong>Next renewal:</strong> {formatDate(subscription.current_period_end)}
          </Typography>
          <Typography variant="body2">
            <strong>Renewal amount:</strong> {formatPrice(subscription.plan?.price_monthly || 0)}
          </Typography>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center">
            <InfoIcon sx={{ mr: 1 }} />
            <Typography>Plan Features</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle2" gutterBottom>
                Daily Quotas
              </Typography>
              <Typography variant="body2">
                • {subscription.plan?.api_quota_daily.toLocaleString()} API calls
              </Typography>
              <Typography variant="body2">
                • {subscription.plan?.ai_analysis_quota_daily.toLocaleString()} AI analyses
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle2" gutterBottom>
                Features
              </Typography>
              {Object.entries(subscription.plan?.features || {}).map(([key, value]) => (
                <Typography key={key} variant="body2">
                  • {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}: {
                    typeof value === 'boolean' ? (value ? 'Yes' : 'No') : value
                  }
                </Typography>
              ))}
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* Cancellation Section */}
      {isActive && (
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box display="flex" alignItems="center">
              <CancelIcon color="error" sx={{ mr: 1 }} />
              <Typography color="error">Cancel Subscription</Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Alert severity="warning" sx={{ mb: 2 }}>
              <Typography variant="body2">
                Cancelling your subscription will remove access to premium features. 
                You can choose to cancel immediately or at the end of your current billing period.
              </Typography>
            </Alert>
            
            <Typography variant="body2" color="text.secondary" paragraph>
              If you cancel at the end of your billing period, you'll continue to have access 
              to all features until {formatDate(subscription.current_period_end)}.
            </Typography>

            <Button
              variant="outlined"
              color="error"
              startIcon={<CancelIcon />}
              onClick={() => setShowCancelDialog(true)}
              disabled={isCancelling}
            >
              Cancel Subscription
            </Button>
          </AccordionDetails>
        </Accordion>
      )}

      {/* Already Cancelled Info */}
      {isCancelled && (
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            Your subscription has been cancelled and will end on {formatDate(subscription.current_period_end)}.
            You'll continue to have access to all features until then.
          </Typography>
        </Alert>
      )}

      {/* Cancellation Dialog */}
      <Dialog 
        open={showCancelDialog} 
        onClose={() => setShowCancelDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" alignItems="center">
            <WarningIcon color="warning" sx={{ mr: 1 }} />
            Cancel Subscription
          </Box>
        </DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 3 }}>
            Are you sure you want to cancel your subscription? This action cannot be undone.
          </Alert>

          <Box sx={{ mb: 3 }}>
            <FormControl component="fieldset" fullWidth>
              <FormLabel component="legend">When should the cancellation take effect?</FormLabel>
              <RadioGroup
                value={cancelForm.effective_date}
                onChange={(e) => setCancelForm({
                  ...cancelForm,
                  effective_date: e.target.value as 'immediate' | 'end_of_period',
                  cancel_immediately: e.target.value === 'immediate'
                })}
              >
                <FormControlLabel
                  value="end_of_period"
                  control={<Radio />}
                  label={`End of current period (${formatDate(subscription.current_period_end)})`}
                />
                <FormControlLabel
                  value="immediate"
                  control={<Radio />}
                  label="Immediately (no refund)"
                />
              </RadioGroup>
            </FormControl>
          </Box>

          <TextField
            select
            fullWidth
            label="Reason for cancellation"
            value={cancelForm.reason}
            onChange={(e) => setCancelForm({ ...cancelForm, reason: e.target.value })}
            SelectProps={{ native: true }}
            sx={{ mb: 2 }}
            required
          >
            <option value="">Select a reason</option>
            {cancellationReasons.map((reason) => (
              <option key={reason} value={reason}>
                {reason}
              </option>
            ))}
          </TextField>

          <TextField
            fullWidth
            multiline
            rows={3}
            label="Additional feedback (optional)"
            value={cancelForm.feedback}
            onChange={(e) => setCancelForm({ ...cancelForm, feedback: e.target.value })}
            placeholder="Help us improve by sharing your feedback..."
          />

          <Divider sx={{ my: 2 }} />

          <Typography variant="body2" color="text.secondary">
            <strong>What happens after cancellation:</strong>
          </Typography>
          <Typography variant="body2" color="text.secondary" component="ul" sx={{ mt: 1, pl: 2 }}>
            <li>You'll lose access to premium features</li>
            <li>Your account will revert to the free plan</li>
            <li>Historical data will be preserved for 90 days</li>
            <li>You can reactivate anytime before the end of your billing period</li>
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCancelDialog(false)}>
            Keep Subscription
          </Button>
          <Button
            onClick={handleCancelSubscription}
            color="error"
            variant="contained"
            disabled={!cancelForm.reason || isCancelling}
            startIcon={isCancelling ? <Box sx={{ width: 16, height: 16 }}><div className="spinner" /></Box> : <CancelIcon />}
          >
            {isCancelling ? 'Cancelling...' : 'Confirm Cancellation'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};