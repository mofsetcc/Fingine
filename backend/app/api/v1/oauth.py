"""
OAuth callback and management endpoints.
"""

import logging
import secrets
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_active_user, rate_limit_auth
from app.models.user import User
from app.schemas.api_response import APIResponse, SuccessResponse
from app.schemas.user import AuthResponse, OAuthLogin
from app.services.auth_service import AuthService, InvalidCredentialsError
from app.services.email_service import EmailService
from app.services.oauth_service import (
    InvalidTokenError,
    OAuthError,
    OAuthService,
    ProviderError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Get authentication service instance."""
    email_service = EmailService()
    return AuthService(db, email_service)


@router.get("/authorize/{provider}")
async def oauth_authorize(
    provider: str,
    request: Request,
    redirect_uri: Optional[str] = Query(
        None, description="Custom redirect URI after auth"
    ),
) -> RedirectResponse:
    """
    Initiate OAuth authorization flow.

    - **provider**: OAuth provider (google, line)
    - **redirect_uri**: Optional custom redirect URI after successful auth

    Redirects to the OAuth provider's authorization page.
    """
    try:
        oauth_service = OAuthService()

        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)

        # Store state and redirect_uri in session/cache
        # In production, you'd store this in Redis with expiration
        # For now, we'll include it in the state parameter
        state_data = {
            "state": state,
            "redirect_uri": redirect_uri or f"{settings.FRONTEND_URL}/auth/callback",
        }

        # Get authorization URL
        auth_url = oauth_service.get_authorization_url(provider, state)

        logger.info(f"OAuth authorization initiated for provider: {provider}")

        return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)

    except ValueError as e:
        logger.warning(f"Invalid OAuth provider: {provider}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}",
        )
    except Exception as e:
        logger.error(f"OAuth authorization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate OAuth authorization",
        )


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: Optional[str] = Query(None, description="Authorization code from provider"),
    state: Optional[str] = Query(
        None, description="State parameter for CSRF protection"
    ),
    error: Optional[str] = Query(None, description="Error from OAuth provider"),
    error_description: Optional[str] = Query(None, description="Error description"),
    auth_service: AuthService = Depends(get_auth_service),
) -> RedirectResponse:
    """
    Handle OAuth callback from provider.

    - **provider**: OAuth provider (google, line)
    - **code**: Authorization code from provider
    - **state**: State parameter for CSRF protection
    - **error**: Error code if authorization failed
    - **error_description**: Human-readable error description

    Processes the OAuth callback and redirects to frontend with result.
    """
    try:
        # Check for OAuth errors
        if error:
            logger.warning(
                f"OAuth error from {provider}: {error} - {error_description}"
            )
            error_url = f"{settings.FRONTEND_URL}/auth/error?error={error}&description={error_description or ''}"
            return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)

        # Validate required parameters
        if not code:
            logger.warning(f"OAuth callback missing authorization code for {provider}")
            error_url = f"{settings.FRONTEND_URL}/auth/error?error=missing_code"
            return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)

        if not state:
            logger.warning(f"OAuth callback missing state parameter for {provider}")
            error_url = f"{settings.FRONTEND_URL}/auth/error?error=missing_state"
            return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)

        # TODO: Validate state parameter against stored value
        # In production, retrieve and validate state from Redis/cache

        oauth_service = OAuthService()

        # Exchange code for token
        token_data = await oauth_service.exchange_code_for_token(provider, code)
        access_token = token_data.get("access_token")

        if not access_token:
            logger.error(f"No access token received from {provider}")
            error_url = f"{settings.FRONTEND_URL}/auth/error?error=no_token"
            return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)

        # Authenticate user with OAuth token
        oauth_login = OAuthLogin(provider=provider, access_token=access_token)

        auth_response = await auth_service.oauth_authenticate(oauth_login)

        # Create success redirect with tokens
        # In production, you might want to use secure HTTP-only cookies
        success_url = (
            f"{settings.FRONTEND_URL}/auth/success"
            f"?access_token={auth_response.tokens.access_token}"
            f"&refresh_token={auth_response.tokens.refresh_token}"
            f"&user_id={auth_response.user.id}"
        )

        logger.info(f"OAuth authentication successful for {provider}")

        return RedirectResponse(url=success_url, status_code=status.HTTP_302_FOUND)

    except InvalidCredentialsError as e:
        logger.warning(f"OAuth authentication failed for {provider}: {e}")
        error_url = f"{settings.FRONTEND_URL}/auth/error?error=invalid_credentials"
        return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)
    except ProviderError as e:
        logger.error(f"OAuth provider error for {provider}: {e}")
        error_url = f"{settings.FRONTEND_URL}/auth/error?error=provider_error"
        return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)
    except Exception as e:
        logger.error(f"OAuth callback failed for {provider}: {e}")
        error_url = f"{settings.FRONTEND_URL}/auth/error?error=callback_failed"
        return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)


@router.post("/link/{provider}", response_model=SuccessResponse)
async def link_oauth_account(
    provider: str,
    oauth_data: OAuthLogin,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: Any = Depends(rate_limit_auth),
) -> SuccessResponse:
    """
    Link OAuth account to existing user account.

    - **provider**: OAuth provider (google, line)
    - **access_token**: OAuth access token

    Links the OAuth identity to the current user's account.
    """
    try:
        from app.models.user import UserOAuthIdentity
        from app.services.oauth_service import OAuthService

        # Validate provider
        if provider not in ["google", "line"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported OAuth provider",
            )

        oauth_service = OAuthService()

        # Verify OAuth token and get user info
        user_info = await oauth_service.verify_token(provider, oauth_data.access_token)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth token"
            )

        # Check if OAuth identity already exists
        existing_identity = (
            db.query(UserOAuthIdentity)
            .filter(
                UserOAuthIdentity.provider == provider,
                UserOAuthIdentity.provider_user_id == user_info["id"],
            )
            .first()
        )

        if existing_identity:
            if existing_identity.user_id == current_user.id:
                return SuccessResponse(
                    message="OAuth account is already linked to your account"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This OAuth account is already linked to another user",
                )

        # Create new OAuth identity
        oauth_identity = UserOAuthIdentity(
            provider=provider, provider_user_id=user_info["id"], user_id=current_user.id
        )

        db.add(oauth_identity)
        db.commit()

        logger.info(
            f"OAuth account linked successfully: {provider} for user {current_user.email}"
        )

        return SuccessResponse(
            message=f"{provider.title()} account linked successfully"
        )

    except HTTPException:
        raise
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth token"
        )
    except ProviderError as e:
        logger.error(f"OAuth provider error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="OAuth provider error"
        )
    except Exception as e:
        logger.error(f"OAuth account linking failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to link OAuth account",
        )


@router.delete("/unlink/{provider}", response_model=SuccessResponse)
async def unlink_oauth_account(
    provider: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """
    Unlink OAuth account from user account.

    - **provider**: OAuth provider (google, line)

    Removes the OAuth identity link from the current user's account.
    """
    try:
        from app.models.user import UserOAuthIdentity

        # Validate provider
        if provider not in ["google", "line"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported OAuth provider",
            )

        # Find OAuth identity
        oauth_identity = (
            db.query(UserOAuthIdentity)
            .filter(
                UserOAuthIdentity.provider == provider,
                UserOAuthIdentity.user_id == current_user.id,
            )
            .first()
        )

        if not oauth_identity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No {provider} account linked to your account",
            )

        # Check if user has password (can't unlink if OAuth is only auth method)
        if not current_user.password_hash:
            # Check if user has other OAuth identities
            other_identities = (
                db.query(UserOAuthIdentity)
                .filter(
                    UserOAuthIdentity.user_id == current_user.id,
                    UserOAuthIdentity.provider != provider,
                )
                .count()
            )

            if other_identities == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot unlink the only authentication method. Please set a password first.",
                )

        # Remove OAuth identity
        db.delete(oauth_identity)
        db.commit()

        logger.info(
            f"OAuth account unlinked successfully: {provider} for user {current_user.email}"
        )

        return SuccessResponse(
            message=f"{provider.title()} account unlinked successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth account unlinking failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlink OAuth account",
        )


@router.get("/linked", response_model=APIResponse[list])
async def get_linked_oauth_accounts(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
) -> APIResponse[list]:
    """
    Get list of OAuth accounts linked to current user.

    Returns list of linked OAuth providers and basic info.
    """
    try:
        from app.models.user import UserOAuthIdentity

        # Get linked OAuth identities
        oauth_identities = (
            db.query(UserOAuthIdentity)
            .filter(UserOAuthIdentity.user_id == current_user.id)
            .all()
        )

        linked_accounts = []
        for identity in oauth_identities:
            linked_accounts.append(
                {
                    "provider": identity.provider,
                    "provider_user_id": identity.provider_user_id,
                    "linked_at": identity.created_at.isoformat(),
                }
            )

        return APIResponse(
            success=True,
            message="Linked OAuth accounts retrieved successfully",
            data=linked_accounts,
        )

    except Exception as e:
        logger.error(f"Failed to get linked OAuth accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve linked accounts",
        )


@router.get("/providers", response_model=APIResponse[dict])
async def get_oauth_providers() -> APIResponse[dict]:
    """
    Get list of supported OAuth providers and their configuration.

    Returns provider information for frontend integration.
    """
    try:
        oauth_service = OAuthService()

        providers_info = {
            "google": {
                "name": "Google",
                "client_id": settings.GOOGLE_CLIENT_ID,
                "authorize_url": "/api/v1/oauth/authorize/google",
                "scopes": ["openid", "email", "profile"],
            },
            "line": {
                "name": "LINE",
                "client_id": settings.LINE_CLIENT_ID,
                "authorize_url": "/api/v1/oauth/authorize/line",
                "scopes": ["profile", "openid", "email"],
            },
        }

        return APIResponse(
            success=True,
            message="OAuth providers retrieved successfully",
            data={
                "supported_providers": oauth_service.get_supported_providers(),
                "providers": providers_info,
            },
        )

    except Exception as e:
        logger.error(f"Failed to get OAuth providers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve OAuth providers",
        )
