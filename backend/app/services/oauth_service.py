"""
OAuth service for Google and LINE authentication.
"""

import logging
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class OAuthError(Exception):
    """Base exception for OAuth errors."""

    pass


class InvalidTokenError(OAuthError):
    """Raised when OAuth token is invalid."""

    pass


class ProviderError(OAuthError):
    """Raised when OAuth provider returns an error."""

    pass


class GoogleOAuthService:
    """Service for Google OAuth authentication."""

    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        self.userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        self.token_info_url = "https://www.googleapis.com/oauth2/v1/tokeninfo"

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Get Google OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "openid email profile",
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
        }

        if state:
            params["state"] = state

        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        return f"{base_url}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from Google

        Returns:
            Token response containing access_token, refresh_token, etc.

        Raises:
            ProviderError: If token exchange fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": self.redirect_uri,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    logger.error(
                        f"Google token exchange failed: {response.status_code} - {response.text}"
                    )
                    raise ProviderError("Failed to exchange code for token")

                token_data = response.json()

                if "error" in token_data:
                    logger.error(f"Google token exchange error: {token_data}")
                    raise ProviderError(f"Token exchange error: {token_data['error']}")

                return token_data

        except httpx.RequestError as e:
            logger.error(f"HTTP error during Google token exchange: {e}")
            raise ProviderError("Network error during token exchange")

    async def verify_token(self, access_token: str) -> Dict[str, Any]:
        """
        Verify Google access token and get user info.

        Args:
            access_token: Google access token

        Returns:
            User information dictionary

        Raises:
            InvalidTokenError: If token is invalid
            ProviderError: If verification fails
        """
        try:
            # First verify the token
            async with httpx.AsyncClient() as client:
                token_info_response = await client.get(
                    f"{self.token_info_url}?access_token={access_token}"
                )

                if token_info_response.status_code != 200:
                    logger.warning(
                        f"Google token verification failed: {token_info_response.status_code}"
                    )
                    raise InvalidTokenError("Invalid access token")

                token_info = token_info_response.json()

                # Check if token is for our app
                if token_info.get("audience") != self.client_id:
                    logger.warning("Google token audience mismatch")
                    raise InvalidTokenError("Token not issued for this application")

                # Get user info
                userinfo_response = await client.get(
                    self.userinfo_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if userinfo_response.status_code != 200:
                    logger.error(
                        f"Failed to get Google user info: {userinfo_response.status_code}"
                    )
                    raise ProviderError("Failed to get user information")

                user_info = userinfo_response.json()

                # Normalize user info
                return {
                    "id": user_info["id"],
                    "email": user_info["email"],
                    "name": user_info.get("name"),
                    "given_name": user_info.get("given_name"),
                    "family_name": user_info.get("family_name"),
                    "picture": user_info.get("picture"),
                    "locale": user_info.get("locale"),
                    "verified_email": user_info.get("verified_email", False),
                }

        except httpx.RequestError as e:
            logger.error(f"HTTP error during Google token verification: {e}")
            raise ProviderError("Network error during token verification")

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh Google access token.

        Args:
            refresh_token: Google refresh token

        Returns:
            New token data

        Raises:
            ProviderError: If token refresh fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    logger.error(f"Google token refresh failed: {response.status_code}")
                    raise ProviderError("Failed to refresh token")

                return response.json()

        except httpx.RequestError as e:
            logger.error(f"HTTP error during Google token refresh: {e}")
            raise ProviderError("Network error during token refresh")


class LineOAuthService:
    """Service for LINE OAuth authentication."""

    def __init__(self):
        self.client_id = settings.LINE_CLIENT_ID
        self.client_secret = settings.LINE_CLIENT_SECRET
        self.redirect_uri = settings.LINE_REDIRECT_URI
        self.profile_url = "https://api.line.me/v2/profile"
        self.verify_url = "https://api.line.me/oauth2/v2.1/verify"

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Get LINE OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "profile openid email",
            "state": state or "",
        }

        base_url = "https://access.line.me/oauth2/v2.1/authorize"
        return f"{base_url}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from LINE

        Returns:
            Token response containing access_token, refresh_token, etc.

        Raises:
            ProviderError: If token exchange fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.line.me/oauth2/v2.1/token",
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": self.redirect_uri,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    logger.error(
                        f"LINE token exchange failed: {response.status_code} - {response.text}"
                    )
                    raise ProviderError("Failed to exchange code for token")

                token_data = response.json()

                if "error" in token_data:
                    logger.error(f"LINE token exchange error: {token_data}")
                    raise ProviderError(f"Token exchange error: {token_data['error']}")

                return token_data

        except httpx.RequestError as e:
            logger.error(f"HTTP error during LINE token exchange: {e}")
            raise ProviderError("Network error during token exchange")

    async def verify_token(self, access_token: str) -> Dict[str, Any]:
        """
        Verify LINE access token and get user info.

        Args:
            access_token: LINE access token

        Returns:
            User information dictionary

        Raises:
            InvalidTokenError: If token is invalid
            ProviderError: If verification fails
        """
        try:
            async with httpx.AsyncClient() as client:
                # Verify token
                verify_response = await client.get(
                    f"{self.verify_url}?access_token={access_token}"
                )

                if verify_response.status_code != 200:
                    logger.warning(
                        f"LINE token verification failed: {verify_response.status_code}"
                    )
                    raise InvalidTokenError("Invalid access token")

                verify_data = verify_response.json()

                # Check if token is for our app
                if verify_data.get("client_id") != self.client_id:
                    logger.warning("LINE token client_id mismatch")
                    raise InvalidTokenError("Token not issued for this application")

                # Get user profile
                profile_response = await client.get(
                    self.profile_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if profile_response.status_code != 200:
                    logger.error(
                        f"Failed to get LINE user profile: {profile_response.status_code}"
                    )
                    raise ProviderError("Failed to get user information")

                profile_data = profile_response.json()

                # Get email if available (requires email scope)
                email = None
                try:
                    email_response = await client.get(
                        "https://api.line.me/oauth2/v2.1/userinfo",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    if email_response.status_code == 200:
                        email_data = email_response.json()
                        email = email_data.get("email")
                except Exception:
                    # Email might not be available
                    pass

                # Normalize user info
                return {
                    "id": profile_data["userId"],
                    "email": email,
                    "name": profile_data.get("displayName"),
                    "picture": profile_data.get("pictureUrl"),
                    "status_message": profile_data.get("statusMessage"),
                }

        except httpx.RequestError as e:
            logger.error(f"HTTP error during LINE token verification: {e}")
            raise ProviderError("Network error during token verification")

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh LINE access token.

        Args:
            refresh_token: LINE refresh token

        Returns:
            New token data

        Raises:
            ProviderError: If token refresh fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.line.me/oauth2/v2.1/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    logger.error(f"LINE token refresh failed: {response.status_code}")
                    raise ProviderError("Failed to refresh token")

                return response.json()

        except httpx.RequestError as e:
            logger.error(f"HTTP error during LINE token refresh: {e}")
            raise ProviderError("Network error during token refresh")


class OAuthService:
    """Main OAuth service that handles multiple providers."""

    def __init__(self):
        self.google = GoogleOAuthService()
        self.line = LineOAuthService()
        self.providers = {"google": self.google, "line": self.line}

    def get_provider(self, provider_name: str):
        """
        Get OAuth provider service.

        Args:
            provider_name: Name of the provider (google, line)

        Returns:
            Provider service instance

        Raises:
            ValueError: If provider is not supported
        """
        if provider_name not in self.providers:
            raise ValueError(f"Unsupported OAuth provider: {provider_name}")

        return self.providers[provider_name]

    def get_authorization_url(
        self, provider_name: str, state: Optional[str] = None
    ) -> str:
        """
        Get authorization URL for provider.

        Args:
            provider_name: Name of the provider
            state: Optional state parameter

        Returns:
            Authorization URL
        """
        provider = self.get_provider(provider_name)
        return provider.get_authorization_url(state)

    async def exchange_code_for_token(
        self, provider_name: str, code: str
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            provider_name: Name of the provider
            code: Authorization code

        Returns:
            Token data
        """
        provider = self.get_provider(provider_name)
        return await provider.exchange_code_for_token(code)

    async def verify_token(
        self, provider_name: str, access_token: str
    ) -> Dict[str, Any]:
        """
        Verify access token and get user info.

        Args:
            provider_name: Name of the provider
            access_token: Access token to verify

        Returns:
            User information
        """
        provider = self.get_provider(provider_name)
        return await provider.verify_token(access_token)

    async def refresh_token(
        self, provider_name: str, refresh_token: str
    ) -> Dict[str, Any]:
        """
        Refresh access token.

        Args:
            provider_name: Name of the provider
            refresh_token: Refresh token

        Returns:
            New token data
        """
        provider = self.get_provider(provider_name)
        return await provider.refresh_token(refresh_token)

    def get_supported_providers(self) -> list[str]:
        """
        Get list of supported OAuth providers.

        Returns:
            List of provider names
        """
        return list(self.providers.keys())
