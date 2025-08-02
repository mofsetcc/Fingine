import {
    Info as InfoIcon,
    Refresh as RefreshIcon,
    TrendingUp as TrendingUpIcon,
    Upgrade as UpgradeIcon
} from '@mui/icons-material';
import {
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
    Grid,
    IconButton,
    LinearProgress,
    Paper,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Tooltip,
    Typography
} from '@mui/material';
import React, { useEffect, useState } from 'react';
import { APIResponse } from '../types/base';

interface UsageQuota {
  api_quota_daily: number;
  api_usage_today: number;
  ai_analysis_quota_daily: number;
  ai_analysis_usage_today: number;
  quota_reset_at: string;
}

interface DailyUsage {
  date: string;
  api_calls: number;
  ai_analysis_calls: number;
  avg_response_time_ms: number;
  total_cost_usd: number;
}

interface QuotaUsageSummary {
  period_days: number;
  start_date: string;
  end_date: string;
  current_quotas: {
    api_quota_daily: number;
    ai_analysis_quota_daily: number;
  };
  usage_by_date: DailyUsage[];
  total_api_calls: number;
  total_ai_analysis_calls: number;
  total_cost_usd: number;
}

interface QuotaUsageDisplayProps {
  showUpgradeButton?: boolean;
  onUpgradeClick?: () => void;
}

export const QuotaUsageDisplay: React.FC<QuotaUsageDisplayProps> = ({
  showUpgradeButton = true,
  onUpgradeClick
}) => {
  const [usageQuota, setUsageQuota] = useState<UsageQuota | null>(null);
  const [usageSummary, setUsageSummary] = useState<QuotaUsageSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadUsageQuota();
  }, []);

  const loadUsageQuota = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/subscription/usage', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to load usage quota');
      }

      const data: APIResponse<UsageQuota> = await response.json();
      setUsageQuota(data.data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load usage quota');
    } finally {
      setLoading(false);
    }
  };

  const loadUsageSummary = async () => {
    try {
      const response = await fetch('/api/v1/subscription/quota/summary?days=7', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to load usage summary');
      }

      const data: APIResponse<QuotaUsageSummary> = await response.json();
      setUsageSummary(data.data);
    } catch (err) {
      console.error('Failed to load usage summary:', err);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadUsageQuota();
    if (showDetailDialog && usageSummary) {
      await loadUsageSummary();
    }
    setRefreshing(false);
  };

  const handleShowDetails = async () => {
    if (!usageSummary) {
      await loadUsageSummary();
    }
    setShowDetailDialog(true);
  };

  const getUsageColor = (usage: number, quota: number): 'success' | 'warning' | 'error' => {
    const percentage = (usage / quota) * 100;
    if (percentage >= 90) return 'error';
    if (percentage >= 70) return 'warning';
    return 'success';
  };

  const getUsagePercentage = (usage: number, quota: number): number => {
    return Math.min((usage / quota) * 100, 100);
  };

  const formatTimeUntilReset = (resetTime: string): string => {
    const now = new Date();
    const reset = new Date(resetTime);
    const diff = reset.getTime() - now.getTime();
    
    if (diff <= 0) return 'Resetting now';
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    
    if (hours > 0) {
      return `Resets in ${hours}h ${minutes}m`;
    }
    return `Resets in ${minutes}m`;
  };

  if (loading) {
    return (
      <Card>
        <CardContent>
          <Box display="flex" alignItems="center" justifyContent="center" minHeight="200px">
            <LinearProgress sx={{ width: '100%' }} />
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent>
          <Alert severity="error" action={
            <Button color="inherit" size="small" onClick={loadUsageQuota}>
              Retry
            </Button>
          }>
            {error}
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (!usageQuota) {
    return null;
  }

  const apiUsagePercentage = getUsagePercentage(usageQuota.api_usage_today, usageQuota.api_quota_daily);
  const aiUsagePercentage = getUsagePercentage(usageQuota.ai_analysis_usage_today, usageQuota.ai_analysis_quota_daily);
  const apiUsageColor = getUsageColor(usageQuota.api_usage_today, usageQuota.api_quota_daily);
  const aiUsageColor = getUsageColor(usageQuota.ai_analysis_usage_today, usageQuota.ai_analysis_quota_daily);

  return (
    <>
      <Card>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6" component="h2">
              Daily Usage Quota
            </Typography>
            <Box>
              <Tooltip title="Refresh usage data">
                <IconButton onClick={handleRefresh} disabled={refreshing} size="small">
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="View detailed usage">
                <IconButton onClick={handleShowDetails} size="small">
                  <InfoIcon />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>

          <Grid container spacing={3}>
            {/* API Calls Usage */}
            <Grid item xs={12} md={6}>
              <Box>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                  <Typography variant="body2" color="text.secondary">
                    API Calls
                  </Typography>
                  <Chip
                    label={`${usageQuota.api_usage_today} / ${usageQuota.api_quota_daily}`}
                    color={apiUsageColor}
                    size="small"
                  />
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={apiUsagePercentage}
                  color={apiUsageColor}
                  sx={{ height: 8, borderRadius: 4 }}
                />
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                  {apiUsagePercentage.toFixed(1)}% used
                </Typography>
              </Box>
            </Grid>

            {/* AI Analysis Usage */}
            <Grid item xs={12} md={6}>
              <Box>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                  <Typography variant="body2" color="text.secondary">
                    AI Analysis
                  </Typography>
                  <Chip
                    label={`${usageQuota.ai_analysis_usage_today} / ${usageQuota.ai_analysis_quota_daily}`}
                    color={aiUsageColor}
                    size="small"
                  />
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={aiUsagePercentage}
                  color={aiUsageColor}
                  sx={{ height: 8, borderRadius: 4 }}
                />
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                  {aiUsagePercentage.toFixed(1)}% used
                </Typography>
              </Box>
            </Grid>
          </Grid>

          <Box mt={2} display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="caption" color="text.secondary">
              {formatTimeUntilReset(usageQuota.quota_reset_at)}
            </Typography>
            
            {showUpgradeButton && (apiUsagePercentage > 70 || aiUsagePercentage > 70) && (
              <Button
                variant="outlined"
                size="small"
                startIcon={<UpgradeIcon />}
                onClick={onUpgradeClick}
                color="primary"
              >
                Upgrade Plan
              </Button>
            )}
          </Box>

          {(apiUsagePercentage >= 90 || aiUsagePercentage >= 90) && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              You're approaching your daily quota limits. Consider upgrading your plan for higher limits.
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Usage Details Dialog */}
      <Dialog
        open={showDetailDialog}
        onClose={() => setShowDetailDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" alignItems="center">
            <TrendingUpIcon sx={{ mr: 1 }} />
            Usage Details (Last 7 Days)
          </Box>
        </DialogTitle>
        <DialogContent>
          {usageSummary ? (
            <>
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={3}>
                  <Card variant="outlined">
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" color="primary">
                        {usageSummary.total_api_calls}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Total API Calls
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={3}>
                  <Card variant="outlined">
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" color="secondary">
                        {usageSummary.total_ai_analysis_calls}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        AI Analysis Calls
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={3}>
                  <Card variant="outlined">
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" color="success.main">
                        ${usageSummary.total_cost_usd.toFixed(4)}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Total Cost
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={3}>
                  <Card variant="outlined">
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" color="info.main">
                        {usageSummary.current_quotas.api_quota_daily}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Daily API Limit
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Date</TableCell>
                      <TableCell align="right">API Calls</TableCell>
                      <TableCell align="right">AI Analysis</TableCell>
                      <TableCell align="right">Avg Response (ms)</TableCell>
                      <TableCell align="right">Cost (USD)</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {usageSummary.usage_by_date.map((day) => (
                      <TableRow key={day.date}>
                        <TableCell>
                          {new Date(day.date).toLocaleDateString()}
                        </TableCell>
                        <TableCell align="right">{day.api_calls}</TableCell>
                        <TableCell align="right">{day.ai_analysis_calls}</TableCell>
                        <TableCell align="right">
                          {day.avg_response_time_ms.toFixed(0)}
                        </TableCell>
                        <TableCell align="right">
                          ${day.total_cost_usd.toFixed(4)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </>
          ) : (
            <Box display="flex" justifyContent="center" p={3}>
              <LinearProgress sx={{ width: '100%' }} />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowDetailDialog(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default QuotaUsageDisplay;