"""
Encryption utilities for secure data storage and API key management.
"""

import os
import base64
import secrets
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class EncryptionManager:
    """Manages encryption and decryption of sensitive data."""
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption manager.
        
        Args:
            master_key: Master encryption key. If None, uses SECRET_KEY from settings.
        """
        self.master_key = master_key or settings.SECRET_KEY
        self._fernet = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize Fernet encryption with derived key."""
        try:
            # Derive a key from the master key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'kessan_salt_2024',  # Static salt for consistency
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
            self._fernet = Fernet(key)
            
        except Exception as e:
            logger.error("Failed to initialize encryption", error=str(e))
            raise
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt a string.
        
        Args:
            data: String to encrypt
            
        Returns:
            Base64 encoded encrypted string
        """
        try:
            if not data:
                return ""
            
            encrypted_data = self._fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
            
        except Exception as e:
            logger.error("Encryption failed", error=str(e))
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt a string.
        
        Args:
            encrypted_data: Base64 encoded encrypted string
            
        Returns:
            Decrypted string
        """
        try:
            if not encrypted_data:
                return ""
            
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self._fernet.decrypt(encrypted_bytes)
            return decrypted_data.decode()
            
        except Exception as e:
            logger.error("Decryption failed", error=str(e))
            raise
    
    def encrypt_dict(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        Encrypt dictionary values.
        
        Args:
            data: Dictionary with string values to encrypt
            
        Returns:
            Dictionary with encrypted values
        """
        encrypted_dict = {}
        for key, value in data.items():
            if isinstance(value, str):
                encrypted_dict[key] = self.encrypt(value)
            else:
                encrypted_dict[key] = self.encrypt(str(value))
        
        return encrypted_dict
    
    def decrypt_dict(self, encrypted_data: Dict[str, str]) -> Dict[str, str]:
        """
        Decrypt dictionary values.
        
        Args:
            encrypted_data: Dictionary with encrypted values
            
        Returns:
            Dictionary with decrypted values
        """
        decrypted_dict = {}
        for key, value in encrypted_data.items():
            decrypted_dict[key] = self.decrypt(value)
        
        return decrypted_dict


class SecureConfigManager:
    """Manages secure storage and retrieval of configuration values."""
    
    def __init__(self, encryption_manager: Optional[EncryptionManager] = None):
        self.encryption = encryption_manager or EncryptionManager()
        self._secure_config: Dict[str, str] = {}
        self._load_secure_config()
    
    def _load_secure_config(self):
        """Load secure configuration from environment or file."""
        # Load encrypted API keys from environment
        encrypted_keys = {
            'ALPHA_VANTAGE_API_KEY': os.getenv('ALPHA_VANTAGE_API_KEY_ENCRYPTED'),
            'GOOGLE_GEMINI_API_KEY': os.getenv('GOOGLE_GEMINI_API_KEY_ENCRYPTED'),
            'NEWS_API_KEY': os.getenv('NEWS_API_KEY_ENCRYPTED'),
            'SENDGRID_API_KEY': os.getenv('SENDGRID_API_KEY_ENCRYPTED'),
            'GOOGLE_CLIENT_SECRET': os.getenv('GOOGLE_CLIENT_SECRET_ENCRYPTED'),
            'LINE_CLIENT_SECRET': os.getenv('LINE_CLIENT_SECRET_ENCRYPTED'),
        }
        
        # Decrypt and store
        for key, encrypted_value in encrypted_keys.items():
            if encrypted_value:
                try:
                    self._secure_config[key] = self.encryption.decrypt(encrypted_value)
                except Exception as e:
                    logger.warning(f"Failed to decrypt {key}", error=str(e))
                    # Fall back to plain text if decryption fails
                    plain_value = os.getenv(key.replace('_ENCRYPTED', ''))
                    if plain_value:
                        self._secure_config[key] = plain_value
    
    def get_api_key(self, service: str) -> Optional[str]:
        """
        Get API key for a service.
        
        Args:
            service: Service name (e.g., 'alpha_vantage', 'google_gemini')
            
        Returns:
            Decrypted API key or None if not found
        """
        key_mapping = {
            'alpha_vantage': 'ALPHA_VANTAGE_API_KEY',
            'google_gemini': 'GOOGLE_GEMINI_API_KEY',
            'news_api': 'NEWS_API_KEY',
            'sendgrid': 'SENDGRID_API_KEY',
            'google_oauth': 'GOOGLE_CLIENT_SECRET',
            'line_oauth': 'LINE_CLIENT_SECRET',
        }
        
        config_key = key_mapping.get(service)
        if not config_key:
            logger.warning(f"Unknown service for API key: {service}")
            return None
        
        return self._secure_config.get(config_key)
    
    def set_api_key(self, service: str, api_key: str) -> bool:
        """
        Set and encrypt API key for a service.
        
        Args:
            service: Service name
            api_key: API key to encrypt and store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            key_mapping = {
                'alpha_vantage': 'ALPHA_VANTAGE_API_KEY',
                'google_gemini': 'GOOGLE_GEMINI_API_KEY',
                'news_api': 'NEWS_API_KEY',
                'sendgrid': 'SENDGRID_API_KEY',
                'google_oauth': 'GOOGLE_CLIENT_SECRET',
                'line_oauth': 'LINE_CLIENT_SECRET',
            }
            
            config_key = key_mapping.get(service)
            if not config_key:
                return False
            
            # Store decrypted version in memory
            self._secure_config[config_key] = api_key
            
            # Log successful update (without the key value)
            logger.info(f"API key updated for service: {service}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set API key for {service}", error=str(e))
            return False
    
    def encrypt_for_storage(self, service: str) -> Optional[str]:
        """
        Get encrypted version of API key for storage.
        
        Args:
            service: Service name
            
        Returns:
            Encrypted API key for storage
        """
        key_mapping = {
            'alpha_vantage': 'ALPHA_VANTAGE_API_KEY',
            'google_gemini': 'GOOGLE_GEMINI_API_KEY',
            'news_api': 'NEWS_API_KEY',
            'sendgrid': 'SENDGRID_API_KEY',
            'google_oauth': 'GOOGLE_CLIENT_SECRET',
            'line_oauth': 'LINE_CLIENT_SECRET',
        }
        
        config_key = key_mapping.get(service)
        if not config_key or config_key not in self._secure_config:
            return None
        
        try:
            return self.encryption.encrypt(self._secure_config[config_key])
        except Exception as e:
            logger.error(f"Failed to encrypt API key for {service}", error=str(e))
            return None


class DataAnonymizer:
    """Utilities for anonymizing sensitive data in logs and analytics."""
    
    @staticmethod
    def anonymize_email(email: str) -> str:
        """
        Anonymize email address for logging.
        
        Args:
            email: Email address to anonymize
            
        Returns:
            Anonymized email (e.g., j***@example.com)
        """
        if not email or '@' not in email:
            return "***@***.***"
        
        local, domain = email.split('@', 1)
        
        if len(local) <= 2:
            anonymized_local = '*' * len(local)
        else:
            anonymized_local = local[0] + '*' * (len(local) - 2) + local[-1]
        
        # Anonymize domain if it's not a common provider
        common_domains = {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com'}
        if domain.lower() not in common_domains:
            domain_parts = domain.split('.')
            if len(domain_parts) > 1:
                domain = '*' * len(domain_parts[0]) + '.' + domain_parts[-1]
        
        return f"{anonymized_local}@{domain}"
    
    @staticmethod
    def anonymize_ip(ip_address: str) -> str:
        """
        Anonymize IP address for logging.
        
        Args:
            ip_address: IP address to anonymize
            
        Returns:
            Anonymized IP address
        """
        if not ip_address:
            return "0.0.0.0"
        
        # IPv4
        if '.' in ip_address:
            parts = ip_address.split('.')
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.*.***"
        
        # IPv6
        if ':' in ip_address:
            parts = ip_address.split(':')
            if len(parts) >= 4:
                return f"{parts[0]}:{parts[1]}:****:****"
        
        return "***.***.***"
    
    @staticmethod
    def anonymize_user_id(user_id: str) -> str:
        """
        Anonymize user ID for logging.
        
        Args:
            user_id: User ID to anonymize
            
        Returns:
            Anonymized user ID
        """
        if not user_id:
            return "***"
        
        if len(user_id) <= 8:
            return '*' * len(user_id)
        
        return user_id[:4] + '*' * (len(user_id) - 8) + user_id[-4:]
    
    @staticmethod
    def anonymize_dict(data: Dict[str, Any], sensitive_keys: set = None) -> Dict[str, Any]:
        """
        Anonymize sensitive fields in a dictionary.
        
        Args:
            data: Dictionary to anonymize
            sensitive_keys: Set of keys to anonymize
            
        Returns:
            Dictionary with anonymized sensitive fields
        """
        if sensitive_keys is None:
            sensitive_keys = {
                'email', 'password', 'token', 'api_key', 'secret',
                'phone', 'address', 'ssn', 'credit_card'
            }
        
        anonymized = {}
        for key, value in data.items():
            key_lower = key.lower()
            
            if any(sensitive_key in key_lower for sensitive_key in sensitive_keys):
                if 'email' in key_lower:
                    anonymized[key] = DataAnonymizer.anonymize_email(str(value))
                elif 'ip' in key_lower:
                    anonymized[key] = DataAnonymizer.anonymize_ip(str(value))
                elif 'user' in key_lower and 'id' in key_lower:
                    anonymized[key] = DataAnonymizer.anonymize_user_id(str(value))
                else:
                    anonymized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                anonymized[key] = DataAnonymizer.anonymize_dict(value, sensitive_keys)
            elif isinstance(value, list):
                anonymized[key] = [
                    DataAnonymizer.anonymize_dict(item, sensitive_keys) 
                    if isinstance(item, dict) else item 
                    for item in value
                ]
            else:
                anonymized[key] = value
        
        return anonymized


# Global instances
encryption_manager = EncryptionManager()
secure_config = SecureConfigManager(encryption_manager)
data_anonymizer = DataAnonymizer()