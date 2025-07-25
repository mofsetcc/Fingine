import {
    CheckCircle as CheckCircleIcon,
    Error as ErrorIcon
} from '@mui/icons-material';
import {
    Alert,
    Box,
    Button,
    Card,
    CardContent,
    CircularProgress,
    Typography
} from '@mui/material';
import React, { useEffect, useState } from 'react';
import { Link as RouterLink, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { APIResponse } from '../../types/base';

interface OAuthCallbackResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    email_verified_at: string | null;
  };
}

export const OAuthCallback: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login } = useAuth();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const code = searchParams.get('code');
  const state = searchParams.get('state');
  const errorParam = searchParams.get('error');
  const provider = searchParams.get('provider') || 'google'; // Default to google

  useEffect(() => {
    handleOAuthCallback();
  }, []);

  const handleOAuthCallback = async () => {
    // Check for OAuth error
    if (errorParam) {
      setError(`OAuth authentication failed: ${errorParam}`);
      setLoading(false);
      return;
    }

    // Check for required parameters
    if (!code) {
      setError('Missing authorization code from OAuth provider');
      setLoading(false);
      return;
    }

    try {
      // Exchange authorization code for access token
      const response = await fetch(`/api/v1/oauth/${provider}/callback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code: code,
          state: state
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'OAuth authentication failed');
      }

      const data: APIResponse<OAuthCallbackResponse> = await response.json();
      
      // Store token and update auth context
      localStorage.setItem('token', data.data.access_token);
      login(data.data.user, data.data.access_token);
      
      setSuccess(true);
      
      // Redirect to dashboard after a short delay
      setTimeout(() => {
        navigate('/dashboard');
      }, 2000);
      
    } catch (error) {
      setError(error instanceof Error ? error.message : 'OAuth authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const getProviderName = (provider: string): string => {
    switch (provider.toLowerCase()) {
      case 'google':
        return 'Google';
      case 'line':
        return 'LINE';
      default:
        return provider;
    }
  };

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
          {loading && (
            <>
              <CircularProgress size={48} sx={{ mb: 2 }} />
              <Typography variant="h5" gutterBottom>
                Completing Sign In
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Please wait while we complete your {getProviderName(provider)} authentication...
              </Typography>
            </>
          )}

          {success && (
            <>
              <CheckCircleIcon sx={{ fontSize: 48, color: 'success.main', mb: 2 }} />
              <Typography variant="h5" gutterBottom>
                Sign In Successful!
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                You have successfully signed in with {getProviderName(provider)}. 
                Redirecting to your dashboard...
              </Typography>
              <CircularProgress size={24} />
            </>
          )}

          {error && (
            <>
              <ErrorIcon sx={{ fontSize: 48, color: 'error.main', mb: 2 }} />
              <Typography variant="h5" gutterBottom>
                Authentication Failed
              </Typography>
              <Alert severity="error" sx={{ mb: 3, textAlign: 'left' }}>
                {error}
              </Alert>
              <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
                <Button
                  component={RouterLink}
                  to="/auth/login"
                  variant="contained"
                >
                  Try Again
                </Button>
                <Button
                  component={RouterLink}
                  to="/auth/register"
                  variant="outlined"
                >
                  Create Account
                </Button>
              </Box>
            </>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};