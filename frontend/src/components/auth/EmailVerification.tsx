import {
    CheckCircle as CheckCircleIcon,
    Email as EmailIcon,
    Refresh as RefreshIcon
} from '@mui/icons-material';
import {
    Alert,
    Box,
    Button,
    Card,
    CardContent,
    CircularProgress,
    Divider,
    Typography
} from '@mui/material';
import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { APIResponse } from '../../types/base';

export const EmailVerification: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user, updateUser, logout } = useAuth();
  
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [resendCooldown, setResendCooldown] = useState(0);

  const token = searchParams.get('token');

  useEffect(() => {
    // If there's a verification token in the URL, verify it automatically
    if (token) {
      verifyEmail(token);
    }
  }, [token]);

  useEffect(() => {
    // Countdown timer for resend cooldown
    if (resendCooldown > 0) {
      const timer = setTimeout(() => {
        setResendCooldown(resendCooldown - 1);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  const verifyEmail = async (verificationToken: string) => {
    setVerifying(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch('/api/v1/auth/verify-email', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          token: verificationToken
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Email verification failed');
      }

      const data: APIResponse<any> = await response.json();
      
      setSuccess('Email verified successfully! You can now access all features.');
      
      // Update user data to reflect email verification
      if (user) {
        updateUser({
          ...user,
          email_verified_at: new Date().toISOString()
        });
      }
      
      // Redirect to dashboard after a short delay
      setTimeout(() => {
        navigate('/dashboard');
      }, 2000);
      
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Email verification failed');
    } finally {
      setVerifying(false);
    }
  };

  const resendVerificationEmail = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch('/api/v1/auth/resend-verification', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to resend verification email');
      }

      const data: APIResponse<any> = await response.json();
      
      setSuccess('Verification email sent! Please check your inbox.');
      setResendCooldown(60); // 60 second cooldown
      
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to resend verification email');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/auth/login');
  };

  // Show verification in progress
  if (verifying) {
    return (
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          bgcolor: 'grey.50',
          py: 3
        }}
      >
        <Card sx={{ maxWidth: 400, width: '100%', mx: 2 }}>
          <CardContent sx={{ p: 4, textAlign: 'center' }}>
            <CircularProgress size={48} sx={{ mb: 2 }} />
            <Typography variant="h5" gutterBottom>
              Verifying Email
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Please wait while we verify your email address...
            </Typography>
          </CardContent>
        </Card>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: 'grey.50',
        py: 3
      }}
    >
      <Card sx={{ maxWidth: 450, width: '100%', mx: 2 }}>
        <CardContent sx={{ p: 4 }}>
          <Box sx={{ textAlign: 'center', mb: 3 }}>
            {success ? (
              <CheckCircleIcon sx={{ fontSize: 48, color: 'success.main', mb: 1 }} />
            ) : (
              <EmailIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
            )}
            <Typography variant="h4" component="h1" gutterBottom>
              {success ? 'Email Verified!' : 'Verify Your Email'}
            </Typography>
            {!success && (
              <Typography variant="body2" color="text.secondary">
                We've sent a verification email to{' '}
                <strong>{user?.email}</strong>
              </Typography>
            )}
          </Box>

          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          {success && (
            <Alert severity="success" sx={{ mb: 3 }}>
              {success}
            </Alert>
          )}

          {!success && (
            <>
              <Box sx={{ mb: 3 }}>
                <Typography variant="body2" color="text.secondary" paragraph>
                  To complete your registration and access all features, please:
                </Typography>
                <Box component="ol" sx={{ pl: 2, mb: 2 }}>
                  <Typography component="li" variant="body2" color="text.secondary">
                    Check your email inbox (and spam folder)
                  </Typography>
                  <Typography component="li" variant="body2" color="text.secondary">
                    Click the verification link in the email
                  </Typography>
                  <Typography component="li" variant="body2" color="text.secondary">
                    Return to this page to continue
                  </Typography>
                </Box>
              </Box>

              <Button
                fullWidth
                variant="contained"
                startIcon={<RefreshIcon />}
                onClick={resendVerificationEmail}
                disabled={loading || resendCooldown > 0}
                sx={{ mb: 2 }}
              >
                {loading ? (
                  <CircularProgress size={24} color="inherit" />
                ) : resendCooldown > 0 ? (
                  `Resend in ${resendCooldown}s`
                ) : (
                  'Resend Verification Email'
                )}
              </Button>

              <Divider sx={{ my: 2 }} />

              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Wrong email address or want to use a different account?
                </Typography>
                <Button
                  variant="outlined"
                  onClick={handleLogout}
                  fullWidth
                >
                  Sign Out & Use Different Account
                </Button>
              </Box>
            </>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};