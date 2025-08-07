"""
GDPR compliance utilities for data protection and privacy.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import structlog

from sqlalchemy.orm import Session
from fastapi import Depends
from app.core.database import get_db
from app.models.user import User
from app.models.logs import APIUsageLog
from app.core.encryption import data_anonymizer

logger = structlog.get_logger(__name__)


class DataProcessingPurpose(Enum):
    """Enumeration of data processing purposes for GDPR compliance."""
    AUTHENTICATION = "authentication"
    SERVICE_PROVISION = "service_provision"
    ANALYTICS = "analytics"
    MARKETING = "marketing"
    LEGAL_COMPLIANCE = "legal_compliance"
    SECURITY = "security"


class ConsentStatus(Enum):
    """User consent status for data processing."""
    GIVEN = "given"
    WITHDRAWN = "withdrawn"
    NOT_GIVEN = "not_given"


class GDPRDataProcessor:
    """Handles GDPR-compliant data processing operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_consent(
        self,
        user_id: str,
        purpose: DataProcessingPurpose,
        consent_given: bool,
        consent_text: str,
        ip_address: Optional[str] = None
    ) -> bool:
        """
        Record user consent for data processing.
        
        Args:
            user_id: User identifier
            purpose: Purpose of data processing
            consent_given: Whether consent was given
            consent_text: Text of consent agreement
            ip_address: IP address of user (anonymized)
            
        Returns:
            True if consent recorded successfully
        """
        try:
            # Create consent record
            consent_record = {
                "user_id": user_id,
                "purpose": purpose.value,
                "status": ConsentStatus.GIVEN.value if consent_given else ConsentStatus.NOT_GIVEN.value,
                "consent_text": consent_text,
                "timestamp": datetime.utcnow().isoformat(),
                "ip_address": data_anonymizer.anonymize_ip(ip_address) if ip_address else None,
                "version": "1.0"
            }
            
            # Store in user profile or separate consent table
            # For now, we'll store in user profile as JSON
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                if not user.gdpr_consents:
                    user.gdpr_consents = {}
                
                user.gdpr_consents[purpose.value] = consent_record
                self.db.commit()
                
                logger.info(
                    "GDPR consent recorded",
                    user_id=data_anonymizer.anonymize_user_id(user_id),
                    purpose=purpose.value,
                    consent_given=consent_given
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error("Failed to record GDPR consent", error=str(e))
            self.db.rollback()
            return False
    
    def check_consent(self, user_id: str, purpose: DataProcessingPurpose) -> bool:
        """
        Check if user has given consent for specific purpose.
        
        Args:
            user_id: User identifier
            purpose: Purpose of data processing
            
        Returns:
            True if consent is given and valid
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or not user.gdpr_consents:
                return False
            
            consent_record = user.gdpr_consents.get(purpose.value)
            if not consent_record:
                return False
            
            return consent_record.get("status") == ConsentStatus.GIVEN.value
            
        except Exception as e:
            logger.error("Failed to check GDPR consent", error=str(e))
            return False
    
    def withdraw_consent(self, user_id: str, purpose: DataProcessingPurpose) -> bool:
        """
        Withdraw user consent for specific purpose.
        
        Args:
            user_id: User identifier
            purpose: Purpose of data processing
            
        Returns:
            True if consent withdrawn successfully
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            if not user.gdpr_consents:
                user.gdpr_consents = {}
            
            # Update consent status
            if purpose.value in user.gdpr_consents:
                user.gdpr_consents[purpose.value]["status"] = ConsentStatus.WITHDRAWN.value
                user.gdpr_consents[purpose.value]["withdrawal_timestamp"] = datetime.utcnow().isoformat()
            else:
                # Create withdrawal record even if no previous consent
                user.gdpr_consents[purpose.value] = {
                    "user_id": user_id,
                    "purpose": purpose.value,
                    "status": ConsentStatus.WITHDRAWN.value,
                    "withdrawal_timestamp": datetime.utcnow().isoformat(),
                    "version": "1.0"
                }
            
            self.db.commit()
            
            logger.info(
                "GDPR consent withdrawn",
                user_id=data_anonymizer.anonymize_user_id(user_id),
                purpose=purpose.value
            )
            return True
            
        except Exception as e:
            logger.error("Failed to withdraw GDPR consent", error=str(e))
            self.db.rollback()
            return False


class DataExporter:
    """Handles data export for GDPR data portability rights."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Export all user data for GDPR data portability.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary containing all user data
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {}
            
            # Basic user information
            user_data = {
                "personal_information": {
                    "user_id": user.id,
                    "email": user.email,
                    "display_name": getattr(user, 'display_name', None),
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "email_verified": user.email_verified,
                    "timezone": getattr(user, 'timezone', None),
                },
                "preferences": {
                    "notification_preferences": getattr(user, 'notification_preferences', {}),
                },
                "consent_records": user.gdpr_consents or {},
                "subscription_data": self._export_subscription_data(user_id),
                "usage_data": self._export_usage_data(user_id),
                "watchlist_data": self._export_watchlist_data(user_id),
                "analysis_history": self._export_analysis_history(user_id),
                "export_metadata": {
                    "export_date": datetime.utcnow().isoformat(),
                    "export_version": "1.0",
                    "data_retention_policy": "Data is retained as per our privacy policy"
                }
            }
            
            logger.info(
                "User data exported for GDPR compliance",
                user_id=data_anonymizer.anonymize_user_id(user_id)
            )
            
            return user_data
            
        except Exception as e:
            logger.error("Failed to export user data", error=str(e))
            return {}
    
    def _export_subscription_data(self, user_id: str) -> Dict[str, Any]:
        """Export user subscription data."""
        try:
            from app.models.subscription import Subscription
            
            subscription = self.db.query(Subscription).filter(
                Subscription.user_id == user_id
            ).first()
            
            if not subscription:
                return {}
            
            return {
                "plan_name": subscription.plan.plan_name if subscription.plan else None,
                "status": subscription.status,
                "current_period_start": subscription.current_period_start.isoformat(),
                "current_period_end": subscription.current_period_end.isoformat(),
                "created_at": subscription.created_at.isoformat(),
            }
            
        except Exception as e:
            logger.error("Failed to export subscription data", error=str(e))
            return {}
    
    def _export_usage_data(self, user_id: str) -> List[Dict[str, Any]]:
        """Export user API usage data (last 90 days)."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            usage_logs = self.db.query(APIUsageLog).filter(
                APIUsageLog.user_id == user_id,
                APIUsageLog.request_timestamp >= cutoff_date
            ).limit(1000).all()  # Limit to prevent huge exports
            
            return [
                {
                    "timestamp": log.request_timestamp.isoformat(),
                    "endpoint": log.endpoint,
                    "request_type": log.request_type,
                    "status_code": log.status_code,
                    "response_time_ms": log.response_time_ms,
                }
                for log in usage_logs
            ]
            
        except Exception as e:
            logger.error("Failed to export usage data", error=str(e))
            return []
    
    def _export_watchlist_data(self, user_id: str) -> List[Dict[str, Any]]:
        """Export user watchlist data."""
        try:
            from app.models.watchlist import UserWatchlist
            
            watchlist_items = self.db.query(UserWatchlist).filter(
                UserWatchlist.user_id == user_id
            ).all()
            
            return [
                {
                    "ticker": item.ticker,
                    "added_at": item.added_at.isoformat(),
                    "notes": item.notes,
                }
                for item in watchlist_items
            ]
            
        except Exception as e:
            logger.error("Failed to export watchlist data", error=str(e))
            return []
    
    def _export_analysis_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Export user AI analysis history (last 90 days)."""
        try:
            from app.models.analysis import AIAnalysisCache
            
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            # Get analysis requests made by this user
            analysis_history = self.db.query(AIAnalysisCache).filter(
                AIAnalysisCache.requested_by == user_id,
                AIAnalysisCache.created_at >= cutoff_date
            ).limit(100).all()  # Limit to prevent huge exports
            
            return [
                {
                    "ticker": analysis.ticker,
                    "analysis_type": analysis.analysis_type,
                    "created_at": analysis.created_at.isoformat(),
                    "confidence_score": float(analysis.confidence_score) if analysis.confidence_score else None,
                }
                for analysis in analysis_history
            ]
            
        except Exception as e:
            logger.error("Failed to export analysis history", error=str(e))
            return []


class DataEraser:
    """Handles data erasure for GDPR right to be forgotten."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def erase_user_data(self, user_id: str, keep_legal_basis: bool = True) -> bool:
        """
        Erase user data for GDPR right to be forgotten.
        
        Args:
            user_id: User identifier
            keep_legal_basis: Whether to keep data required for legal compliance
            
        Returns:
            True if data erased successfully
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # Anonymize personal data instead of deleting (for referential integrity)
            user.email = f"deleted_user_{user_id[:8]}@deleted.local"
            user.password_hash = "DELETED"
            user.display_name = "Deleted User"
            user.email_verified = False
            user.gdpr_consents = {"data_erased": True, "erasure_date": datetime.utcnow().isoformat()}
            
            # Mark user as deleted
            user.is_deleted = True
            user.deleted_at = datetime.utcnow()
            
            # Erase related data
            self._erase_watchlist_data(user_id)
            self._erase_usage_logs(user_id, keep_legal_basis)
            self._anonymize_analysis_history(user_id)
            
            self.db.commit()
            
            logger.info(
                "User data erased for GDPR compliance",
                user_id=data_anonymizer.anonymize_user_id(user_id),
                keep_legal_basis=keep_legal_basis
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to erase user data", error=str(e))
            self.db.rollback()
            return False
    
    def _erase_watchlist_data(self, user_id: str):
        """Erase user watchlist data."""
        try:
            from app.models.watchlist import UserWatchlist
            
            self.db.query(UserWatchlist).filter(
                UserWatchlist.user_id == user_id
            ).delete()
            
        except Exception as e:
            logger.error("Failed to erase watchlist data", error=str(e))
    
    def _erase_usage_logs(self, user_id: str, keep_legal_basis: bool):
        """Erase or anonymize usage logs."""
        try:
            if keep_legal_basis:
                # Anonymize instead of delete for legal compliance
                usage_logs = self.db.query(APIUsageLog).filter(
                    APIUsageLog.user_id == user_id
                ).all()
                
                for log in usage_logs:
                    log.user_id = None  # Remove user association
                    log.anonymized = True
            else:
                # Delete usage logs older than legal requirement (e.g., 2 years)
                cutoff_date = datetime.utcnow() - timedelta(days=730)
                self.db.query(APIUsageLog).filter(
                    APIUsageLog.user_id == user_id,
                    APIUsageLog.request_timestamp < cutoff_date
                ).delete()
                
        except Exception as e:
            logger.error("Failed to erase usage logs", error=str(e))
    
    def _anonymize_analysis_history(self, user_id: str):
        """Anonymize analysis history."""
        try:
            from app.models.analysis import AIAnalysisCache
            
            analysis_records = self.db.query(AIAnalysisCache).filter(
                AIAnalysisCache.requested_by == user_id
            ).all()
            
            for record in analysis_records:
                record.requested_by = None  # Remove user association
                record.anonymized = True
                
        except Exception as e:
            logger.error("Failed to anonymize analysis history", error=str(e))


class GDPRComplianceManager:
    """Main GDPR compliance manager."""
    
    def __init__(self, db: Session):
        self.db = db
        self.data_processor = GDPRDataProcessor(db)
        self.data_exporter = DataExporter(db)
        self.data_eraser = DataEraser(db)
    
    def handle_data_subject_request(
        self,
        user_id: str,
        request_type: str,
        additional_params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Handle GDPR data subject requests.
        
        Args:
            user_id: User identifier
            request_type: Type of request (export, erase, consent_status)
            additional_params: Additional parameters for the request
            
        Returns:
            Response data for the request
        """
        additional_params = additional_params or {}
        
        try:
            if request_type == "export":
                return {
                    "success": True,
                    "data": self.data_exporter.export_user_data(user_id),
                    "message": "Data export completed successfully"
                }
            
            elif request_type == "erase":
                keep_legal_basis = additional_params.get("keep_legal_basis", True)
                success = self.data_eraser.erase_user_data(user_id, keep_legal_basis)
                return {
                    "success": success,
                    "message": "Data erasure completed successfully" if success else "Data erasure failed"
                }
            
            elif request_type == "consent_status":
                consents = {}
                for purpose in DataProcessingPurpose:
                    consents[purpose.value] = self.data_processor.check_consent(user_id, purpose)
                
                return {
                    "success": True,
                    "data": {"consents": consents},
                    "message": "Consent status retrieved successfully"
                }
            
            else:
                return {
                    "success": False,
                    "message": f"Unknown request type: {request_type}"
                }
                
        except Exception as e:
            logger.error("Failed to handle GDPR request", error=str(e))
            return {
                "success": False,
                "message": "Failed to process GDPR request"
            }


def get_gdpr_manager(db: Session = Depends(get_db)) -> GDPRComplianceManager:
    """Get GDPR compliance manager instance."""
    return GDPRComplianceManager(db)