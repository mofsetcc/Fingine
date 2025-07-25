# OAuth Integration Setup Guide

This guide explains how to set up OAuth integration with Google and LINE for the Japanese Stock Analysis Platform.

## Overview

The platform supports OAuth authentication with:
- **Google OAuth 2.0** - For users with Google accounts
- **LINE Login** - Popular in Japan for social authentication

## Google OAuth Setup

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API and Google OAuth2 API

### 2. Configure OAuth Consent Screen

1. Go to "APIs & Services" > "OAuth consent screen"
2. Choose "External" user type
3. Fill in the required information:
   - App name: "Project Kessan"
   - User support email: your support email
   - Developer contact information: your email
4. Add scopes:
   - `openid`
   - `email`
   - `profile`
5. Add test users if needed

### 3. Create OAuth Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. Choose "Web application"
4. Configure:
   - Name: "Project Kessan Web Client"
   - Authorized JavaScript origins:
     - `http://localhost:3000` (development)
     - `https://yourdomain.com` (production)
   - Authorized redirect URIs:
     - `http://localhost:8000/api/v1/oauth/callback/google` (development)
     - `https://api.yourdomain.com/api/v1/oauth/callback/google` (production)

### 4. Environment Variables

Add to your `.env` file:

```env
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/oauth/callback/google
```

## LINE Login Setup

### 1. Create LINE Login Channel

1. Go to [LINE Developers Console](https://developers.line.biz/)
2. Create a new provider or use existing one
3. Create a new channel with type "LINE Login"

### 2. Configure Channel Settings

1. In the channel settings, configure:
   - App name: "Project Kessan"
   - App description: "AI-powered Japanese stock analysis platform"
   - App icon: Upload your app icon
2. In "LINE Login" tab:
   - Callback URL: 
     - `http://localhost:8000/api/v1/oauth/callback/line` (development)
     - `https://api.yourdomain.com/api/v1/oauth/callback/line` (production)
3. Enable required scopes:
   - `profile`
   - `openid`
   - `email` (if available)

### 3. Environment Variables

Add to your `.env` file:

```env
LINE_CLIENT_ID=your_line_channel_id
LINE_CLIENT_SECRET=your_line_channel_secret
LINE_REDIRECT_URI=http://localhost:8000/api/v1/oauth/callback/line
```

## Frontend Integration

### OAuth Flow

1. **Initiate OAuth**: Frontend redirects to `/api/v1/oauth/authorize/{provider}`
2. **User Authorization**: User authorizes on provider's site
3. **Callback Handling**: Provider redirects to `/api/v1/oauth/callback/{provider}`
4. **Token Exchange**: Backend exchanges code for tokens and creates user session
5. **Frontend Redirect**: Backend redirects to frontend with tokens

### Frontend Implementation Example

```typescript
// Initiate Google OAuth
const initiateGoogleOAuth = () => {
  window.location.href = `${API_BASE_URL}/api/v1/oauth/authorize/google?redirect_uri=${encodeURIComponent(window.location.origin + '/auth/callback')}`;
};

// Initiate LINE OAuth
const initiateLINEOAuth = () => {
  window.location.href = `${API_BASE_URL}/api/v1/oauth/authorize/line?redirect_uri=${encodeURIComponent(window.location.origin + '/auth/callback')}`;
};

// Handle OAuth callback (in your callback page)
const handleOAuthCallback = () => {
  const urlParams = new URLSearchParams(window.location.search);
  const accessToken = urlParams.get('access_token');
  const refreshToken = urlParams.get('refresh_token');
  const error = urlParams.get('error');
  
  if (error) {
    // Handle error
    console.error('OAuth error:', error);
    return;
  }
  
  if (accessToken && refreshToken) {
    // Store tokens and redirect to dashboard
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
    window.location.href = '/dashboard';
  }
};
```

## API Endpoints

### OAuth Authorization
- `GET /api/v1/oauth/authorize/{provider}` - Initiate OAuth flow
- `GET /api/v1/oauth/callback/{provider}` - Handle OAuth callback

### OAuth Management
- `POST /api/v1/oauth/link/{provider}` - Link OAuth account to existing user
- `DELETE /api/v1/oauth/unlink/{provider}` - Unlink OAuth account
- `GET /api/v1/oauth/linked` - Get linked OAuth accounts
- `GET /api/v1/oauth/providers` - Get supported providers

### Direct OAuth Authentication
- `POST /api/v1/auth/oauth/{provider}` - Authenticate with OAuth token directly

## Security Considerations

### State Parameter
- Always use the `state` parameter for CSRF protection
- Generate a random state value for each OAuth request
- Validate the state parameter in the callback

### Token Security
- Store OAuth tokens securely
- Use HTTPS in production
- Implement token refresh logic
- Set appropriate token expiration times

### Error Handling
- Handle OAuth errors gracefully
- Don't expose sensitive error information to users
- Log OAuth errors for debugging

## Testing

### Development Testing
1. Set up OAuth applications with localhost URLs
2. Use test accounts for OAuth providers
3. Test both new user registration and existing user linking

### Production Testing
1. Update OAuth applications with production URLs
2. Test with real user accounts
3. Monitor OAuth success/failure rates

## Troubleshooting

### Common Issues

1. **Invalid Redirect URI**
   - Ensure redirect URIs match exactly in OAuth app configuration
   - Check for trailing slashes and protocol (http vs https)

2. **Invalid Client ID/Secret**
   - Verify environment variables are set correctly
   - Check for extra spaces or characters in credentials

3. **Scope Issues**
   - Ensure required scopes are enabled in OAuth app
   - Check if user has granted necessary permissions

4. **CORS Issues**
   - Configure CORS origins in backend settings
   - Ensure frontend domain is allowed

### Debug Mode

Enable debug logging for OAuth:

```python
import logging
logging.getLogger('app.services.oauth_service').setLevel(logging.DEBUG)
```

## Production Deployment

### Environment Variables
Update production environment with:
- Production OAuth client IDs and secrets
- Production redirect URIs
- HTTPS URLs

### SSL/TLS
- Ensure all OAuth endpoints use HTTPS
- Configure proper SSL certificates
- Update OAuth app configurations with HTTPS URLs

### Monitoring
- Monitor OAuth success/failure rates
- Set up alerts for OAuth errors
- Track user registration/login patterns

## Support

For OAuth-related issues:
1. Check the logs for detailed error messages
2. Verify OAuth app configurations
3. Test with OAuth provider's debugging tools
4. Contact support with specific error details