/**
 * Usage Overview Component
 * Shows detailed usage statistics and quota information
 */

import {
    Api as ApiIcon,
    Psychology as PsychologyIcon,
    Refresh as RefreshIcon,
    Timeline as TimelineIcon,
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
    FormControl,
    Grid,
    InputLabel,
    LinearProgress,
    MenuItem,
    Paper,
    Select,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Typography
} from '@mui/material';
import React, { useEffect, useState } from 'react';

import { APIResponse } from '../../types/base';
import { SubscriptionWithPlan, UsageHistory, UsageQuota } from '../../types/subscription';

interface UsageOverviewProps {
  usageQuota?: UsageQuota;
  subscription?: SubscriptionWithPlan;
  isLoading: boolean;
}

interface UsageSummary {
  daily_usage: UsageHistory[];
  weekly_average: {
    api_calls: number;
    ai_analyses: number;
  };
  monthly_projection: {
    api_calls: number;
    ai_analyses: number;
    cost_usd: number;
  };
  peak_usage_day: string;
  quota_utilization: {
    api_calls: number;
    ai_analyses: number;
  };
}

export const UsageOverview: React.FC<UsageOverviewProps> = ({
  usageQuota,
  subscription,
  isLoading
}) => {
  const [usageSummary, setUsageSummary] = useState<UsageSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<number>(7); // days

  useEffect(() => {
    loadUsageSummary();
  }, [selectedPeriod]);

  const loadUsageSummary = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`/api/v1/subscription/quota/summary?days=${selectedPeriod}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to load usage summary');
      }

      const data: APIResponse<UsageSummary> = await response.json();
      setUsageSummary(data.data);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load usage data');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ja-JP');
  };

  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return 'error';
    if (percentage >= 70) return 'warning';
    return 'primary';
  };

  const getUsageStatus = (percentage: number) => {
    if (percentage >= 100) return 'Quota Exceeded';
    if (percentage >= 90) return 'Near Limit';
    if (percentage >= 70) return 'High Usage';
    return 'Normal';
  };

  if (isLoading && !usageQuota) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="300px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h6">
          Usage Overview
        </Typography>
        <Box display="flex" gap={2} alignItems="center">
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Period</InputLabel>
            <Select
              value={selectedPeriod}
              label="Period"
              onChange={(e) => setSelectedPeriod(Number(e.target.value))}
            >
              <MenuItem value={7}>Last 7 days</MenuItem>
              <MenuItem value={14}>Last 14 days</MenuItem>
              <MenuItem value={30}>Last 30 days</MenuItem>
            </Select>
          </FormControl>
          <Button
            startIcon={<RefreshIcon />}
            onClick={loadUsageSummary}
            disabled={loading}
            size="small"
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Current Usage Cards */}
      {usageQuota && (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" sx={{ mb: 2 }}>
                  <ApiIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6">API Calls</Typography>
                </Box>
                
                <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                  <Typography variant="h4" color="primary">
                    {usageQuota.api_calls_today.toLocaleString()}
                  </Typography>
                  <Chip
                    label={getUsageStatus(usageQuota.api_quota_percentage)}
                    color={getUsageColor(usageQuota.api_quota_percentage) as any}
                    size="small"
                  />
                </Box>
                
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  of {usageQuota.api_quota_daily.toLocaleString()} daily quota
                </Typography>
                
                <LinearProgress
                  variant="determinate"
                  value={Math.min(usageQuota.api_quota_percentage, 100)}
                  color={getUsageColor(usageQuota.api_quota_percentage) as any}
                  sx={{ height: 8, borderRadius: 4 }}
                />
                
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  {usageQuota.api_calls_remaining} calls remaining
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" sx={{ mb: 2 }}>
                  <PsychologyIcon color="secondary" sx={{ mr: 1 }} />
                  <Typography variant="h6">AI Analysis</Typography>
                </Box>
                
                <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                  <Typography variant="h4" color="secondary">
                    {usageQuota.ai_analysis_today.toLocaleString()}
                  </Typography>
                  <Chip
                    label={getUsageStatus(usageQuota.ai_quota_percentage)}
                    color={getUsageColor(usageQuota.ai_quota_percentage) as any}
                    size="small"
                  />
                </Box>
                
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  of {usageQuota.ai_analysis_quota_daily.toLocaleString()} daily quota
                </Typography>
                
                <LinearProgress
                  variant="determinate"
                  value={Math.min(usageQuota.ai_quota_percentage, 100)}
                  color={getUsageColor(usageQuota.ai_quota_percentage) as any}
                  sx={{ height: 8, borderRadius: 4 }}
                />
                
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  {usageQuota.ai_analysis_remaining} analyses remaining
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Usage Summary Statistics */}
      {usageSummary && (
        <>
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <TimelineIcon color="info" sx={{ fontSize: 40, mb: 1 }} />
                  <Typography variant="h4" color="info.main">
                    {usageSummary.weekly_average.api_calls.toFixed(0)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Avg API Calls/Day
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={4}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <TrendingUpIcon color="success" sx={{ fontSize: 40, mb: 1 }} />
                  <Typography variant="h4" color="success.main">
                    {usageSummary.monthly_projection.api_calls.toLocaleString()}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Monthly Projection
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={4}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="warning.main">
                    {usageSummary.quota_utilization.api_calls.toFixed(1)}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Quota Utilization
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Peak: {formatDate(usageSummary.peak_usage_day)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Daily Usage History */}
          <Typography variant="h6" gutterBottom>
            Daily Usage History ({selectedPeriod} days)
          </Typography>
          
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Date</TableCell>
                  <TableCell align="right">API Calls</TableCell>
                  <TableCell align="right">AI Analyses</TableCell>
                  <TableCell align="right">Cost (USD)</TableCell>
                  <TableCell align="center">Usage Level</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {usageSummary.daily_usage.map((day) => {
                  const apiPercentage = subscription?.plan ? 
                    (day.api_calls / subscription.plan.api_quota_daily) * 100 : 0;
                  const aiPercentage = subscription?.plan ? 
                    (day.ai_analyses / subscription.plan.ai_analysis_quota_daily) * 100 : 0;
                  const maxPercentage = Math.max(apiPercentage, aiPercentage);
                  
                  return (
                    <TableRow key={day.date}>
                      <TableCell>
                        {formatDate(day.date)}
                      </TableCell>
                      <TableCell align="right">
                        {day.api_calls.toLocaleString()}
                      </TableCell>
                      <TableCell align="right">
                        {day.ai_analyses.toLocaleString()}
                      </TableCell>
                      <TableCell align="right">
                        ${day.cost_usd?.toFixed(4) || '0.0000'}
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={getUsageStatus(maxPercentage)}
                          color={getUsageColor(maxPercentage) as any}
                          size="small"
                        />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}

      {/* Quota Reset Information */}
      {usageQuota && (
        <Alert severity="info" sx={{ mt: 3 }}>
          <Typography variant="body2">
            Your daily quotas reset at {new Date(usageQuota.quota_reset_at).toLocaleTimeString('ja-JP')} JST.
            {subscription?.plan && (
              <>
                {' '}Current plan: <strong>{subscription.plan.plan_name.toUpperCase()}</strong>
                {' '}({subscription.plan.api_quota_daily} API calls, {subscription.plan.ai_analysis_quota_daily} AI analyses per day)
              </>
            )}
          </Typography>
        </Alert>
      )}
    </Box>
  );
};