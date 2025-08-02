/**
 * Billing History Component
 * Shows invoice history and payment information
 */

import {
    CalendarToday as CalendarIcon,
    CreditCard as CreditCardIcon,
    Download as DownloadIcon,
    Receipt as ReceiptIcon,
    Visibility as VisibilityIcon
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
    IconButton,
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

import { APIResponse } from '../../types/base';
import { Invoice, SubscriptionWithPlan } from '../../types/subscription';

interface BillingHistoryProps {
  subscription?: SubscriptionWithPlan;
}

interface BillingSummary {
  total_paid: number;
  total_invoices: number;
  next_billing_date: string;
  next_billing_amount: number;
  payment_method: string;
}

export const BillingHistory: React.FC<BillingHistoryProps> = ({
  subscription
}) => {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [billingSummary, setBillingSummary] = useState<BillingSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [showInvoiceDialog, setShowInvoiceDialog] = useState(false);

  useEffect(() => {
    loadBillingData();
  }, [subscription]);

  const loadBillingData = async () => {
    if (!subscription) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Load invoices
      const invoicesResponse = await fetch('/api/v1/billing/invoices', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (invoicesResponse.ok) {
        const invoicesData: APIResponse<Invoice[]> = await invoicesResponse.json();
        setInvoices(invoicesData.data);
      }

      // Load billing summary
      const summaryResponse = await fetch('/api/v1/billing/summary', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (summaryResponse.ok) {
        const summaryData: APIResponse<BillingSummary> = await summaryResponse.json();
        setBillingSummary(summaryData.data);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load billing data');
    } finally {
      setLoading(false);
    }
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'JPY',
      minimumFractionDigits: 0
    }).format(price);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ja-JP');
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'paid':
        return 'success';
      case 'pending':
        return 'warning';
      case 'failed':
        return 'error';
      case 'cancelled':
        return 'default';
      default:
        return 'default';
    }
  };

  const handleDownloadInvoice = async (invoice: Invoice) => {
    try {
      const response = await fetch(`/api/v1/billing/invoices/${invoice.id}/download`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to download invoice');
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `invoice-${invoice.id}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download invoice');
    }
  };

  const handleViewInvoice = (invoice: Invoice) => {
    setSelectedInvoice(invoice);
    setShowInvoiceDialog(true);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="300px">
        <CircularProgress />
      </Box>
    );
  }

  if (!subscription) {
    return (
      <Alert severity="info">
        No subscription found. Please subscribe to a plan to view billing history.
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Billing & Invoices
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Billing Summary */}
      {billingSummary && (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <ReceiptIcon color="primary" sx={{ fontSize: 40, mb: 1 }} />
                <Typography variant="h4" color="primary">
                  {billingSummary.total_invoices}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total Invoices
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <CreditCardIcon color="success" sx={{ fontSize: 40, mb: 1 }} />
                <Typography variant="h4" color="success.main">
                  {formatPrice(billingSummary.total_paid)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total Paid
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <CalendarIcon color="info" sx={{ fontSize: 40, mb: 1 }} />
                <Typography variant="h6" color="info.main">
                  {formatDate(billingSummary.next_billing_date)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Next Billing
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h4" color="warning.main">
                  {formatPrice(billingSummary.next_billing_amount)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Next Amount
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {billingSummary.payment_method}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Invoices Table */}
      <Typography variant="h6" gutterBottom>
        Invoice History
      </Typography>

      {invoices.length === 0 ? (
        <Alert severity="info">
          No invoices found. Your first invoice will appear here after your first billing cycle.
        </Alert>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Invoice #</TableCell>
                <TableCell>Date</TableCell>
                <TableCell>Amount</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Due Date</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {invoices.map((invoice) => (
                <TableRow key={invoice.id}>
                  <TableCell>
                    <Typography variant="body2" fontFamily="monospace">
                      #{invoice.id.slice(-8)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {formatDate(invoice.created_at)}
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {formatPrice(invoice.amount)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {invoice.currency}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={invoice.status}
                      color={getStatusColor(invoice.status) as any}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {invoice.due_date ? formatDate(invoice.due_date) : '-'}
                  </TableCell>
                  <TableCell align="center">
                    <Box display="flex" justifyContent="center" gap={1}>
                      <Tooltip title="View Invoice">
                        <IconButton
                          size="small"
                          onClick={() => handleViewInvoice(invoice)}
                        >
                          <VisibilityIcon />
                        </IconButton>
                      </Tooltip>
                      
                      {invoice.invoice_url && (
                        <Tooltip title="Download PDF">
                          <IconButton
                            size="small"
                            onClick={() => handleDownloadInvoice(invoice)}
                          >
                            <DownloadIcon />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Invoice Detail Dialog */}
      <Dialog 
        open={showInvoiceDialog} 
        onClose={() => setShowInvoiceDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Invoice Details
        </DialogTitle>
        <DialogContent>
          {selectedInvoice && (
            <Box>
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={6}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Invoice Number
                  </Typography>
                  <Typography variant="body1" fontFamily="monospace">
                    #{selectedInvoice.id}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Status
                  </Typography>
                  <Chip
                    label={selectedInvoice.status}
                    color={getStatusColor(selectedInvoice.status) as any}
                    size="small"
                  />
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Issue Date
                  </Typography>
                  <Typography variant="body1">
                    {formatDate(selectedInvoice.created_at)}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Due Date
                  </Typography>
                  <Typography variant="body1">
                    {selectedInvoice.due_date ? formatDate(selectedInvoice.due_date) : 'N/A'}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Amount
                  </Typography>
                  <Typography variant="h6" color="primary">
                    {formatPrice(selectedInvoice.amount)}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Paid Date
                  </Typography>
                  <Typography variant="body1">
                    {selectedInvoice.paid_at ? formatDate(selectedInvoice.paid_at) : 'Not paid'}
                  </Typography>
                </Grid>
              </Grid>

              {selectedInvoice.status === 'pending' && (
                <Alert severity="warning" sx={{ mt: 2 }}>
                  This invoice is pending payment. Please ensure your payment method is up to date.
                </Alert>
              )}

              {selectedInvoice.status === 'failed' && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  Payment failed for this invoice. Please update your payment method and try again.
                </Alert>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowInvoiceDialog(false)}>
            Close
          </Button>
          {selectedInvoice?.invoice_url && (
            <Button
              variant="contained"
              startIcon={<DownloadIcon />}
              onClick={() => selectedInvoice && handleDownloadInvoice(selectedInvoice)}
            >
              Download PDF
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
};