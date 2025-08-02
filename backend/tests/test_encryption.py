"""
Tests for encryption and data anonymization utilities.
"""

import pytest
from unittest.mock import Mock, patch

from app.core.encryption import (
    EncryptionManager,
    SecureConfigManager,
    DataAnonymizer
)


class TestEncryptionManager:
    """Test encryption manager functionality."""
    
    @pytest.fixture
    def encryption_manager(self):
        return EncryptionManager("test_master_key_12345")
    
    def test_encrypt_decrypt_string(self, encryption_manager):
        """Test string encryption and decryption."""
        original_text = "sensitive_api_key_12345"
        
        # Encrypt
        encrypted = encryption_manager.encrypt(original_text)
        assert encrypted != original_text
        assert len(encrypted) > 0
        
        # Decrypt
        decrypted = encryption_manager.decrypt(encrypted)
        assert decrypted == original_text
    
    def test_encrypt_empty_string(self, encryption_manager):
        """Test encryption of empty string."""
        encrypted = encryption_manager.encrypt("")
        assert encrypted == ""
        
        decrypted = encryption_manager.decrypt("")
        assert decrypted == ""
    
    def test_encrypt_decrypt_dict(self, encryption_manager):
        """Test dictionary encryption and decryption."""
        original_dict = {
            "api_key": "secret_key_123",
            "password": "super_secret_password",
            "number": "12345"
        }
        
        # Encrypt
        encrypted_dict = encryption_manager.encrypt_dict(original_dict)
        
        # Verify all values are encrypted
        for key, value in encrypted_dict.items():
            assert value != original_dict[key]
        
        # Decrypt
        decrypted_dict = encryption_manager.decrypt_dict(encrypted_dict)
        
        # Verify all values are correctly decrypted
        assert decrypted_dict == original_dict
    
    def test_encryption_consistency(self, encryption_manager):
        """Test that same input produces different encrypted outputs (due to IV)."""
        text = "test_string"
        
        encrypted1 = encryption_manager.encrypt(text)
        encrypted2 = encryption_manager.encrypt(text)
        
        # Should be different due to random IV
        assert encrypted1 != encrypted2
        
        # But both should decrypt to same value
        assert encryption_manager.decrypt(encrypted1) == text
        assert encryption_manager.decrypt(encrypted2) == text


class TestSecureConfigManager:
    """Test secure configuration manager."""
    
    @pytest.fixture
    def config_manager(self):
        with patch.dict('os.environ', {
            'ALPHA_VANTAGE_API_KEY_ENCRYPTED': 'encrypted_key_data',
            'ALPHA_VANTAGE_API_KEY': 'fallback_plain_key'
        }):
            return SecureConfigManager()
    
    def test_get_api_key_known_service(self, config_manager):
        """Test getting API key for known service."""
        # Mock the decryption to return a test key
        config_manager._secure_config['ALPHA_VANTAGE_API_KEY'] = 'test_api_key'
        
        api_key = config_manager.get_api_key('alpha_vantage')
        assert api_key == 'test_api_key'
    
    def test_get_api_key_unknown_service(self, config_manager):
        """Test getting API key for unknown service."""
        api_key = config_manager.get_api_key('unknown_service')
        assert api_key is None
    
    def test_set_api_key(self, config_manager):
        """Test setting API key."""
        result = config_manager.set_api_key('alpha_vantage', 'new_test_key')
        assert result is True
        
        # Verify it was stored
        stored_key = config_manager.get_api_key('alpha_vantage')
        assert stored_key == 'new_test_key'
    
    def test_encrypt_for_storage(self, config_manager):
        """Test encrypting API key for storage."""
        config_manager.set_api_key('alpha_vantage', 'test_key_for_storage')
        
        encrypted = config_manager.encrypt_for_storage('alpha_vantage')
        assert encrypted is not None
        assert encrypted != 'test_key_for_storage'


class TestDataAnonymizer:
    """Test data anonymization utilities."""
    
    def test_anonymize_email(self):
        """Test email anonymization."""
        # Regular email
        anonymized = DataAnonymizer.anonymize_email("john.doe@example.com")
        assert anonymized == "j******e@*******.com"
        
        # Short email
        anonymized = DataAnonymizer.anonymize_email("a@b.com")
        assert anonymized == "*@*.com"
        
        # Gmail (common domain)
        anonymized = DataAnonymizer.anonymize_email("user@gmail.com")
        assert anonymized == "u**r@gmail.com"
        
        # Invalid email
        anonymized = DataAnonymizer.anonymize_email("invalid_email")
        assert anonymized == "***@***.***"
    
    def test_anonymize_ip(self):
        """Test IP address anonymization."""
        # IPv4
        anonymized = DataAnonymizer.anonymize_ip("192.168.1.100")
        assert anonymized == "192.168.*.***"
        
        # IPv6
        anonymized = DataAnonymizer.anonymize_ip("2001:0db8:85a3:0000:0000:8a2e:0370:7334")
        assert anonymized == "2001:0db8:****:****"
        
        # Invalid IP
        anonymized = DataAnonymizer.anonymize_ip("invalid_ip")
        assert anonymized == "***.***.***"
        
        # Empty IP
        anonymized = DataAnonymizer.anonymize_ip("")
        assert anonymized == "0.0.0.0"
    
    def test_anonymize_user_id(self):
        """Test user ID anonymization."""
        # Long user ID
        user_id = "user_12345678901234567890"
        anonymized = DataAnonymizer.anonymize_user_id(user_id)
        assert anonymized == "user*****************7890"
        
        # Short user ID
        short_id = "user123"
        anonymized = DataAnonymizer.anonymize_user_id(short_id)
        assert anonymized == "*******"
        
        # Empty user ID
        anonymized = DataAnonymizer.anonymize_user_id("")
        assert anonymized == "***"
    
    def test_anonymize_dict(self):
        """Test dictionary anonymization."""
        sensitive_data = {
            "email": "user@example.com",
            "password": "secret123",
            "api_key": "sk_test_12345",
            "user_id": "user_12345678",
            "ip_address": "192.168.1.1",
            "normal_field": "normal_value",
            "nested": {
                "email": "nested@example.com",
                "token": "secret_token"
            }
        }
        
        anonymized = DataAnonymizer.anonymize_dict(sensitive_data)
        
        # Check that sensitive fields are anonymized
        assert anonymized["email"] == "u**r@*******.com"
        assert anonymized["password"] == "***REDACTED***"
        assert anonymized["api_key"] == "***REDACTED***"
        assert anonymized["user_id"] == "user_12345678"
        assert anonymized["ip_address"] == "192.168.*.***"
        
        # Check that normal fields are preserved
        assert anonymized["normal_field"] == "normal_value"
        
        # Check nested anonymization
        assert anonymized["nested"]["email"] == "n****d@*******.com"
        assert anonymized["nested"]["token"] == "***REDACTED***"
    
    def test_anonymize_dict_with_custom_keys(self):
        """Test dictionary anonymization with custom sensitive keys."""
        data = {
            "custom_secret": "secret_value",
            "normal_field": "normal_value"
        }
        
        anonymized = DataAnonymizer.anonymize_dict(
            data, 
            sensitive_keys={"custom_secret"}
        )
        
        assert anonymized["custom_secret"] == "***REDACTED***"
        assert anonymized["normal_field"] == "normal_value"