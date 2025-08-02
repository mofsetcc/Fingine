"""
Tests for GDPR compliance functionality.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.core.gdpr_compliance import (
    GDPRDataProcessor,
    DataExporter,
    DataEraser,
    GDPRComplianceManager,
    DataProcessingPurpose
)
from app.models.user import User


class TestGDPRDataProcessor:
    """Test GDPR data processor functionality."""
    
    @pytest.fixture
    def mock_db(self):
        return Mock()
    
    @pytest.fixture
    def processor(self, mock_db):
        return GDPRDataProcessor(mock_db)
    
    def test_record_consent_success(self, processor, mock_db):
        """Test successful consent recording."""
        # Mock user
        mock_user = Mock()
        mock_user.gdpr_consents = {}
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Record consent
        result = processor.record_consent(
            user_id="user123",
            purpose=DataProcessingPurpose.AUTHENTICATION,
            consent_given=True,
            consent_text="I agree to data processing",
            ip_address="192.168.1.1"
        )
        
        assert result is True
        assert DataProcessingPurpose.AUTHENTICATION.value in mock_user.gdpr_consents
        mock_db.commit.assert_called_once()
    
    def test_check_consent_given(self, processor, mock_db):
        """Test checking consent when given."""
        # Mock user with consent
        mock_user = Mock()
        mock_user.gdpr_consents = {
            "authentication": {"status": "given"}
        }
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = processor.check_consent("user123", DataProcessingPurpose.AUTHENTICATION)
        
        assert result is True
    
    def test_check_consent_not_given(self, processor, mock_db):
        """Test checking consent when not given."""
        # Mock user without consent
        mock_user = Mock()
        mock_user.gdpr_consents = {}
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = processor.check_consent("user123", DataProcessingPurpose.AUTHENTICATION)
        
        assert result is False
    
    def test_withdraw_consent(self, processor, mock_db):
        """Test consent withdrawal."""
        # Mock user with existing consent
        mock_user = Mock()
        mock_user.gdpr_consents = {
            "authentication": {"status": "given"}
        }
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = processor.withdraw_consent("user123", DataProcessingPurpose.AUTHENTICATION)
        
        assert result is True
        assert mock_user.gdpr_consents["authentication"]["status"] == "withdrawn"
        mock_db.commit.assert_called_once()


class TestDataExporter:
    """Test data export functionality."""
    
    @pytest.fixture
    def mock_db(self):
        return Mock()
    
    @pytest.fixture
    def exporter(self, mock_db):
        return DataExporter(mock_db)
    
    def test_export_user_data(self, exporter, mock_db):
        """Test user data export."""
        # Mock user
        mock_user = Mock()
        mock_user.id = "user123"
        mock_user.email = "test@example.com"
        mock_user.created_at = datetime.utcnow()
        mock_user.email_verified = True
        mock_user.gdpr_consents = {"authentication": {"status": "given"}}
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Mock related data methods
        exporter._export_subscription_data = Mock(return_value={})
        exporter._export_usage_data = Mock(return_value=[])
        exporter._export_watchlist_data = Mock(return_value=[])
        exporter._export_analysis_history = Mock(return_value=[])
        
        result = exporter.export_user_data("user123")
        
        assert "personal_information" in result
        assert "consent_records" in result
        assert "export_metadata" in result
        assert result["personal_information"]["email"] == "test@example.com"


class TestDataEraser:
    """Test data erasure functionality."""
    
    @pytest.fixture
    def mock_db(self):
        return Mock()
    
    @pytest.fixture
    def eraser(self, mock_db):
        return DataEraser(mock_db)
    
    def test_erase_user_data(self, eraser, mock_db):
        """Test user data erasure."""
        # Mock user
        mock_user = Mock()
        mock_user.id = "user123"
        mock_user.email = "test@example.com"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Mock erasure methods
        eraser._erase_watchlist_data = Mock()
        eraser._erase_usage_logs = Mock()
        eraser._anonymize_analysis_history = Mock()
        
        result = eraser.erase_user_data("user123")
        
        assert result is True
        assert mock_user.email.startswith("deleted_user_")
        assert mock_user.password_hash == "DELETED"
        assert mock_user.is_deleted is True
        mock_db.commit.assert_called_once()


class TestGDPRComplianceManager:
    """Test GDPR compliance manager."""
    
    @pytest.fixture
    def mock_db(self):
        return Mock()
    
    @pytest.fixture
    def manager(self, mock_db):
        return GDPRComplianceManager(mock_db)
    
    def test_handle_export_request(self, manager):
        """Test handling data export request."""
        manager.data_exporter.export_user_data = Mock(return_value={"data": "test"})
        
        result = manager.handle_data_subject_request("user123", "export")
        
        assert result["success"] is True
        assert "data" in result
    
    def test_handle_erase_request(self, manager):
        """Test handling data erasure request."""
        manager.data_eraser.erase_user_data = Mock(return_value=True)
        
        result = manager.handle_data_subject_request(
            "user123", 
            "erase", 
            {"keep_legal_basis": True}
        )
        
        assert result["success"] is True
    
    def test_handle_consent_status_request(self, manager):
        """Test handling consent status request."""
        manager.data_processor.check_consent = Mock(return_value=True)
        
        result = manager.handle_data_subject_request("user123", "consent_status")
        
        assert result["success"] is True
        assert "data" in result
        assert "consents" in result["data"]