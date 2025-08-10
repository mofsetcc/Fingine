"""
GDPR compliance API endpoints.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.encryption import data_anonymizer
from app.core.gdpr_compliance import (
    DataProcessingPurpose,
    GDPRComplianceManager,
    get_gdpr_manager,
)
from app.models.user import User
from app.schemas.api_response import APIResponse, SuccessResponse
from app.schemas.user import GDPRConsentRequest, GDPRDataRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/consent", response_model=SuccessResponse)
async def record_consent(
    consent_data: GDPRConsentRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    gdpr_manager: GDPRComplianceManager = Depends(get_gdpr_manager),
) -> SuccessResponse:
    """
    Record user consent for data processing.

    - **purpose**: Purpose of data processing (authentication, analytics, marketing, etc.)
    - **consent_given**: Whether consent is given
    - **consent_text**: Text of the consent agreement

    Records the user's consent for GDPR compliance.
    """
    try:
        # Validate purpose
        try:
            purpose = DataProcessingPurpose(consent_data.purpose)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid processing purpose: {consent_data.purpose}",
            )

        # Get client IP for audit trail
        client_ip = request.client.host if request.client else None

        # Record consent
        success = gdpr_manager.data_processor.record_consent(
            user_id=str(current_user.id),
            purpose=purpose,
            consent_given=consent_data.consent_given,
            consent_text=consent_data.consent_text,
            ip_address=client_ip,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record consent",
            )

        logger.info(
            "GDPR consent recorded",
            user_id=data_anonymizer.anonymize_user_id(str(current_user.id)),
            purpose=consent_data.purpose,
            consent_given=consent_data.consent_given,
        )

        return SuccessResponse(message="Consent recorded successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record consent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record consent",
        )


@router.post("/consent/withdraw", response_model=SuccessResponse)
async def withdraw_consent(
    purpose: str,
    current_user: User = Depends(get_current_active_user),
    gdpr_manager: GDPRComplianceManager = Depends(get_gdpr_manager),
) -> SuccessResponse:
    """
    Withdraw user consent for data processing.

    - **purpose**: Purpose of data processing to withdraw consent for

    Withdraws the user's consent for the specified purpose.
    """
    try:
        # Validate purpose
        try:
            processing_purpose = DataProcessingPurpose(purpose)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid processing purpose: {purpose}",
            )

        # Withdraw consent
        success = gdpr_manager.data_processor.withdraw_consent(
            user_id=str(current_user.id), purpose=processing_purpose
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to withdraw consent",
            )

        logger.info(
            "GDPR consent withdrawn",
            user_id=data_anonymizer.anonymize_user_id(str(current_user.id)),
            purpose=purpose,
        )

        return SuccessResponse(message="Consent withdrawn successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to withdraw consent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to withdraw consent",
        )


@router.get("/consent/status", response_model=APIResponse[Dict[str, Any]])
async def get_consent_status(
    current_user: User = Depends(get_current_active_user),
    gdpr_manager: GDPRComplianceManager = Depends(get_gdpr_manager),
) -> APIResponse[Dict[str, Any]]:
    """
    Get user's current consent status for all processing purposes.

    Returns the current consent status for each data processing purpose.
    """
    try:
        response = gdpr_manager.handle_data_subject_request(
            user_id=str(current_user.id), request_type="consent_status"
        )

        if not response["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response["message"],
            )

        return APIResponse(
            success=True,
            message="Consent status retrieved successfully",
            data=response["data"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get consent status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve consent status",
        )


@router.post("/data/export", response_model=APIResponse[Dict[str, Any]])
async def export_user_data(
    current_user: User = Depends(get_current_active_user),
    gdpr_manager: GDPRComplianceManager = Depends(get_gdpr_manager),
) -> APIResponse[Dict[str, Any]]:
    """
    Export all user data for GDPR data portability.

    Returns a comprehensive export of all user data stored in the system.
    This includes personal information, preferences, usage history, and more.
    """
    try:
        response = gdpr_manager.handle_data_subject_request(
            user_id=str(current_user.id), request_type="export"
        )

        if not response["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response["message"],
            )

        logger.info(
            "User data exported",
            user_id=data_anonymizer.anonymize_user_id(str(current_user.id)),
        )

        return APIResponse(
            success=True,
            message="Data export completed successfully",
            data=response["data"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export user data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export user data",
        )


@router.post("/data/erase", response_model=SuccessResponse)
async def erase_user_data(
    erase_request: GDPRDataRequest,
    current_user: User = Depends(get_current_active_user),
    gdpr_manager: GDPRComplianceManager = Depends(get_gdpr_manager),
) -> SuccessResponse:
    """
    Erase user data for GDPR right to be forgotten.

    - **keep_legal_basis**: Whether to keep data required for legal compliance
    - **confirmation**: Confirmation that user understands the consequences

    This will permanently erase or anonymize the user's personal data.
    This action cannot be undone.
    """
    try:
        # Require explicit confirmation
        if not erase_request.confirmation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Explicit confirmation required for data erasure",
            )

        response = gdpr_manager.handle_data_subject_request(
            user_id=str(current_user.id),
            request_type="erase",
            additional_params={"keep_legal_basis": erase_request.keep_legal_basis},
        )

        if not response["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response["message"],
            )

        logger.info(
            "User data erased",
            user_id=data_anonymizer.anonymize_user_id(str(current_user.id)),
            keep_legal_basis=erase_request.keep_legal_basis,
        )

        return SuccessResponse(
            message="Data erasure completed successfully. Your account has been anonymized."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to erase user data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to erase user data",
        )


@router.get("/privacy-policy", response_model=APIResponse[Dict[str, Any]])
async def get_privacy_policy() -> APIResponse[Dict[str, Any]]:
    """
    Get the current privacy policy and data processing information.

    Returns information about how user data is processed, stored, and protected.
    """
    privacy_policy = {
        "version": "1.0",
        "effective_date": "2024-01-01",
        "data_controller": {"name": "Project Kessan", "contact": "privacy@kessan.com"},
        "data_processing_purposes": [
            {
                "purpose": "authentication",
                "description": "To authenticate users and manage accounts",
                "legal_basis": "Contract performance",
                "retention_period": "Until account deletion",
            },
            {
                "purpose": "service_provision",
                "description": "To provide stock analysis and related services",
                "legal_basis": "Contract performance",
                "retention_period": "Until account deletion",
            },
            {
                "purpose": "analytics",
                "description": "To improve our services and user experience",
                "legal_basis": "Legitimate interest",
                "retention_period": "2 years (anonymized)",
            },
            {
                "purpose": "security",
                "description": "To protect against fraud and security threats",
                "legal_basis": "Legitimate interest",
                "retention_period": "2 years",
            },
        ],
        "user_rights": [
            "Right to access your personal data",
            "Right to rectify inaccurate data",
            "Right to erase your data (right to be forgotten)",
            "Right to restrict processing",
            "Right to data portability",
            "Right to object to processing",
            "Right to withdraw consent",
        ],
        "data_retention": {
            "personal_data": "Until account deletion or 2 years after last activity",
            "usage_logs": "2 years (anonymized after 90 days)",
            "financial_records": "7 years (legal requirement)",
        },
        "contact_information": {
            "data_protection_officer": "dpo@kessan.com",
            "privacy_inquiries": "privacy@kessan.com",
        },
    }

    return APIResponse(
        success=True,
        message="Privacy policy retrieved successfully",
        data=privacy_policy,
    )
