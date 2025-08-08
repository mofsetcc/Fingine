#!/usr/bin/env python3
"""
Data Encryption and Secure Storage Validation Script

This script validates that all sensitive data is properly encrypted and stored securely
in the production environment, including API keys, user data, and database connections.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import structlog
import psycopg2
from cryptography.fernet import Fernet
import base64

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings
from app.core.encryption import EncryptionManager, SecureConfigManager, DataAnonymizer
from app.core.database import get_db

logger = structlog.get_logger(__name__)


class EncryptionTestResult:
    """Container for encryption test results."""
    
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.security_issues = []
        self.test_results = {}
    
    def add_test_result(self, test_name: str, passed: bool, details: Dict[str, Any]):
        """Add a test result."""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
        else:
            self.tests_failed += 1
        
        self.test_results[test_name] = {
            "passed": passed,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def add_security_issue(self, issue: str):
        """Add a security issue."""
        self.security_issues.append(issue)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test summary."""
        return {
            "test_timestamp": datetime.utcnow().isoformat(),
            "tests_run": self.tests_run,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "success_rate": (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0,
            "security_issues_count": len(self.security_issues),
            "overall_status": "PASS" if self.tests_failed == 0 and len(self.security_issues) == 0 else "FAIL"
        }


class EncryptionValidator:
    """Data encryption and secure storage validator."""
    
    def __init__(self):
        self.result = EncryptionTestResult()
        
    async def run_all_tests(self) -> EncryptionTestResult:
        """Run all encryption validation tests."""
        logger.info("Starting data encryption validation tests")
        
        # 1. Test encryption manager functionality
        await self._test_encryption_manager()
        
        # 2. Test secure configuration management
        await self._test_secure_config_management()
        
        # 3. Test data anonymization
        await self._test_data_anonymization()
        
        # 4. Test database connection security
        await self._test_database_connection_security()
        
        # 5. Test environment variable security
        await self._test_environment_variable_security()
        
        # 6. Test API key encryption
        await self._test_api_key_encryption()
        
        # 7. Test password hashing
        await self._test_password_hashing()
        
        # 8. Test JWT token security
        await self._test_jwt_token_security()
        
        # 9. Test data at rest encryption
        await self._test_data_at_rest_encryption()
        
        # 10. Test encryption key management
        await self._test_encryption_key_management()
        
        logger.info("Encryption validation tests completed", summary=self.result.get_summary())
        return self.result
    
    async def _test_encryption_manager(self):
        """Test the encryption manager functionality."""
        logger.info("Testing encryption manager")
        
        try:
            encryption_manager = EncryptionManager()
            
            # Test string encryption/decryption
            test_data = "sensitive_data_12345!@#$%"
            encrypted = encryption_manager.encrypt(test_data)
            decrypted = encryption_manager.decrypt(encrypted)
            
            # Verify encryption works
            encryption_works = (
                decrypted == test_data and
                encrypted != test_data and
                len(encrypted) > len(test_data)
            )
            
            # Test with empty string
            empty_encrypted = encryption_manager.encrypt("")
            empty_decrypted = encryption_manager.decrypt(empty_encrypted)
            empty_handling = empty_decrypted == ""
            
            # Test with special characters
            special_data = "特殊文字テスト!@#$%^&*()_+-=[]{}|;:,.<>?"
            special_encrypted = encryption_manager.encrypt(special_data)
            special_decrypted = encryption_manager.decrypt(special_encrypted)
            special_handling = special_decrypted == special_data
            
            # Test dictionary encryption
            test_dict = {
                "api_key": "secret_key_123",
                "password": "user_password_456",
                "token": "auth_token_789"
            }
            
            encrypted_dict = encryption_manager.encrypt_dict(test_dict)
            decrypted_dict = encryption_manager.decrypt_dict(encrypted_dict)
            dict_encryption_works = decrypted_dict == test_dict
            
            # Test that encrypted values are different
            values_encrypted = all(
                encrypted_dict[key] != test_dict[key] 
                for key in test_dict.keys()
            )
            
            all_tests_pass = (
                encryption_works and
                empty_handling and
                special_handling and
                dict_encryption_works and
                values_encrypted
            )
            
            self.result.add_test_result(
                "encryption_manager",
                all_tests_pass,
                {
                    "string_encryption": encryption_works,
                    "empty_string_handling": empty_handling,
                    "special_characters": special_handling,
                    "dictionary_encryption": dict_encryption_works,
                    "values_properly_encrypted": values_encrypted,
                    "encrypted_length": len(encrypted),
                    "original_length": len(test_data)
                }
            )
            
        except Exception as e:
            self.result.add_test_result(
                "encryption_manager",
                False,
                {"error": str(e)}
            )
            self.result.add_security_issue(f"Encryption manager failed: {str(e)}")
    
    async def _test_secure_config_management(self):
        """Test secure configuration management."""
        logger.info("Testing secure configuration management")
        
        try:
            encryption_manager = EncryptionManager()
            secure_config = SecureConfigManager(encryption_manager)
            
            # Test setting and getting API keys
            test_services = [
                ("test_service_1", "test_api_key_12345"),
                ("test_service_2", "another_secret_key_67890"),
                ("alpha_vantage", "AV_test_key_abcdef")
            ]
            
            set_results = {}
            get_results = {}
            
            for service, api_key in test_services:
                # Test setting API key
                set_success = secure_config.set_api_key(service, api_key)
                set_results[service] = set_success
                
                # Test getting API key
                retrieved_key = secure_config.get_api_key(service)
                get_results[service] = retrieved_key == api_key
            
            # Test encryption for storage
            encryption_results = {}
            for service, _ in test_services:
                encrypted_for_storage = secure_config.encrypt_for_storage(service)
                encryption_results[service] = bool(encrypted_for_storage)
            
            # Test unknown service
            unknown_key = secure_config.get_api_key("unknown_service")
            unknown_handling = unknown_key is None
            
            all_sets_successful = all(set_results.values())
            all_gets_successful = all(get_results.values())
            all_encryptions_successful = all(encryption_results.values())
            
            secure_config_works = (
                all_sets_successful and
                all_gets_successful and
                all_encryptions_successful and
                unknown_handling
            )
            
            self.result.add_test_result(
                "secure_config_management",
                secure_config_works,
                {
                    "set_results": set_results,
                    "get_results": get_results,
                    "encryption_results": encryption_results,
                    "unknown_service_handling": unknown_handling,
                    "all_operations_successful": secure_config_works
                }
            )
            
        except Exception as e:
            self.result.add_test_result(
                "secure_config_management",
                False,
                {"error": str(e)}
            )
            self.result.add_security_issue(f"Secure config management failed: {str(e)}")
    
    async def _test_data_anonymization(self):
        """Test data anonymization functionality."""
        logger.info("Testing data anonymization")
        
        try:
            anonymizer = DataAnonymizer()
            
            # Test email anonymization
            test_emails = [
                "user@example.com",
                "john.doe@company.co.jp",
                "a@b.com",
                "very.long.email.address@subdomain.example.org"
            ]
            
            email_results = {}
            for email in test_emails:
                anonymized = anonymizer.anonymize_email(email)
                email_results[email] = {
                    "anonymized": anonymized,
                    "is_different": anonymized != email,
                    "has_at_symbol": "@" in anonymized,
                    "length_reasonable": len(anonymized) >= 5
                }
            
            # Test IP anonymization
            test_ips = [
                "192.168.1.100",
                "10.0.0.1",
                "172.16.254.1",
                "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
            ]
            
            ip_results = {}
            for ip in test_ips:
                anonymized = anonymizer.anonymize_ip(ip)
                ip_results[ip] = {
                    "anonymized": anonymized,
                    "is_different": anonymized != ip,
                    "has_asterisks": "*" in anonymized
                }
            
            # Test user ID anonymization
            test_user_ids = [
                "user-12345678-abcdef",
                "short",
                "very-long-user-identifier-with-many-characters"
            ]
            
            user_id_results = {}
            for user_id in test_user_ids:
                anonymized = anonymizer.anonymize_user_id(user_id)
                user_id_results[user_id] = {
                    "anonymized": anonymized,
                    "is_different": anonymized != user_id,
                    "same_length": len(anonymized) == len(user_id)
                }
            
            # Test dictionary anonymization
            sensitive_dict = {
                "email": "user@example.com",
                "password": "secret123",
                "api_key": "key_12345",
                "user_id": "user-123",
                "ip_address": "192.168.1.1",
                "normal_field": "normal_value",
                "count": 42
            }
            
            anonymized_dict = anonymizer.anonymize_dict(sensitive_dict)
            
            dict_anonymization_correct = (
                anonymized_dict["email"] != sensitive_dict["email"] and
                anonymized_dict["password"] == "***REDACTED***" and
                anonymized_dict["api_key"] == "***REDACTED***" and
                anonymized_dict["normal_field"] == sensitive_dict["normal_field"] and
                anonymized_dict["count"] == sensitive_dict["count"]
            )
            
            # Check all email anonymizations work
            all_emails_anonymized = all(
                result["is_different"] and result["has_at_symbol"]
                for result in email_results.values()
            )
            
            # Check all IP anonymizations work
            all_ips_anonymized = all(
                result["is_different"] and result["has_asterisks"]
                for result in ip_results.values()
            )
            
            # Check all user ID anonymizations work
            all_user_ids_anonymized = all(
                result["is_different"]
                for result in user_id_results.values()
            )
            
            anonymization_works = (
                all_emails_anonymized and
                all_ips_anonymized and
                all_user_ids_anonymized and
                dict_anonymization_correct
            )
            
            self.result.add_test_result(
                "data_anonymization",
                anonymization_works,
                {
                    "email_results": email_results,
                    "ip_results": ip_results,
                    "user_id_results": user_id_results,
                    "dict_anonymization": dict_anonymization_correct,
                    "all_anonymizations_work": anonymization_works
                }
            )
            
        except Exception as e:
            self.result.add_test_result(
                "data_anonymization",
                False,
                {"error": str(e)}
            )
            self.result.add_security_issue(f"Data anonymization failed: {str(e)}")
    
    async def _test_database_connection_security(self):
        """Test database connection security."""
        logger.info("Testing database connection security")
        
        try:
            db_url = settings.DATABASE_URL
            
            # Check SSL configuration
            ssl_configured = any(ssl_param in db_url.lower() for ssl_param in [
                "sslmode=require",
                "sslmode=prefer", 
                "ssl=true",
                "sslmode=verify-full"
            ])
            
            # Check that password is not in plain text in logs
            # (This is a basic check - in production, ensure DATABASE_URL is not logged)
            password_not_exposed = "password=" not in db_url or len(db_url.split("password=")[1].split("@")[0]) > 8
            
            # Parse connection string to validate components
            import urllib.parse as urlparse
            try:
                parsed = urlparse.urlparse(db_url)
                connection_components_valid = all([
                    parsed.scheme in ["postgresql", "postgres"],
                    parsed.hostname,
                    parsed.username,
                    parsed.password,
                    parsed.path.lstrip('/')
                ])
            except Exception:
                connection_components_valid = False
            
            # Check for connection pooling configuration
            pooling_configured = any(pool_param in db_url.lower() for pool_param in [
                "pool_size",
                "max_connections",
                "pool_timeout"
            ])
            
            database_security_good = (
                ssl_configured and
                password_not_exposed and
                connection_components_valid
            )
            
            self.result.add_test_result(
                "database_connection_security",
                database_security_good,
                {
                    "ssl_configured": ssl_configured,
                    "password_not_exposed": password_not_exposed,
                    "connection_components_valid": connection_components_valid,
                    "pooling_configured": pooling_configured,
                    "overall_security": database_security_good
                }
            )
            
            if not ssl_configured:
                self.result.add_security_issue("Database connection does not use SSL")
            
            if not password_not_exposed:
                self.result.add_security_issue("Database password may be exposed")
            
        except Exception as e:
            self.result.add_test_result(
                "database_connection_security",
                False,
                {"error": str(e)}
            )
            self.result.add_security_issue(f"Database connection security check failed: {str(e)}")
    
    async def _test_environment_variable_security(self):
        """Test environment variable security."""
        logger.info("Testing environment variable security")
        
        try:
            # Check critical environment variables
            critical_env_vars = [
                "SECRET_KEY",
                "DATABASE_URL",
                "REDIS_URL"
            ]
            
            sensitive_env_vars = [
                "ALPHA_VANTAGE_API_KEY",
                "GOOGLE_GEMINI_API_KEY",
                "NEWS_API_KEY",
                "SENDGRID_API_KEY"
            ]
            
            env_var_results = {}
            
            # Check critical variables
            for var in critical_env_vars:
                value = os.getenv(var)
                env_var_results[var] = {
                    "is_set": bool(value),
                    "is_not_default": value not in ["changeme", "default", "secret", "password"] if value else False,
                    "sufficient_length": len(value) >= 16 if value else False
                }
            
            # Check sensitive variables (may be encrypted)
            for var in sensitive_env_vars:
                value = os.getenv(var)
                encrypted_value = os.getenv(f"{var}_ENCRYPTED")
                
                env_var_results[var] = {
                    "is_set": bool(value or encrypted_value),
                    "is_encrypted": bool(encrypted_value),
                    "plain_text_secure": len(value) >= 16 if value else True
                }
            
            # Check SECRET_KEY specifically
            secret_key = os.getenv("SECRET_KEY", "")
            secret_key_secure = (
                len(secret_key) >= 32 and
                not secret_key.isalnum() and  # Should contain special characters
                secret_key not in ["changeme", "default", "your-secret-key"]
            )
            
            # Check for development/test values in production
            dev_values_present = any(
                dev_val in os.getenv(var, "").lower()
                for var in critical_env_vars + sensitive_env_vars
                for dev_val in ["test", "dev", "localhost", "example", "changeme"]
                if os.getenv(var)
            )
            
            all_critical_set = all(
                env_var_results[var]["is_set"] and env_var_results[var]["is_not_default"]
                for var in critical_env_vars
            )
            
            all_sensitive_secure = all(
                env_var_results[var]["is_set"]
                for var in sensitive_env_vars
            )
            
            env_security_good = (
                all_critical_set and
                all_sensitive_secure and
                secret_key_secure and
                not dev_values_present
            )
            
            self.result.add_test_result(
                "environment_variable_security",
                env_security_good,
                {
                    "env_var_results": env_var_results,
                    "secret_key_secure": secret_key_secure,
                    "dev_values_present": dev_values_present,
                    "all_critical_set": all_critical_set,
                    "all_sensitive_secure": all_sensitive_secure,
                    "overall_security": env_security_good
                }
            )
            
            if not secret_key_secure:
                self.result.add_security_issue("SECRET_KEY is not sufficiently secure")
            
            if dev_values_present:
                self.result.add_security_issue("Development/test values found in environment variables")
            
        except Exception as e:
            self.result.add_test_result(
                "environment_variable_security",
                False,
                {"error": str(e)}
            )
    
    async def _test_api_key_encryption(self):
        """Test API key encryption and storage."""
        logger.info("Testing API key encryption")
        
        try:
            # Test that API keys can be encrypted and decrypted
            test_api_keys = {
                "alpha_vantage": "AV_TEST_KEY_12345ABCDEF",
                "google_gemini": "GEMINI_TEST_KEY_67890GHIJKL",
                "news_api": "NEWS_TEST_KEY_MNOPQR123456"
            }
            
            encryption_manager = EncryptionManager()
            secure_config = SecureConfigManager(encryption_manager)
            
            encryption_results = {}
            
            for service, api_key in test_api_keys.items():
                # Set the API key
                set_success = secure_config.set_api_key(service, api_key)
                
                # Retrieve the API key
                retrieved_key = secure_config.get_api_key(service)
                
                # Get encrypted version for storage
                encrypted_for_storage = secure_config.encrypt_for_storage(service)
                
                # Verify encryption
                encryption_results[service] = {
                    "set_success": set_success,
                    "retrieval_success": retrieved_key == api_key,
                    "encryption_for_storage": bool(encrypted_for_storage),
                    "encrypted_different": encrypted_for_storage != api_key if encrypted_for_storage else False
                }
            
            # Test that encrypted keys are actually encrypted
            all_encrypted_properly = all(
                result["encrypted_different"] for result in encryption_results.values()
            )
            
            # Test that all operations succeeded
            all_operations_successful = all(
                result["set_success"] and result["retrieval_success"] and result["encryption_for_storage"]
                for result in encryption_results.values()
            )
            
            api_key_encryption_works = all_encrypted_properly and all_operations_successful
            
            self.result.add_test_result(
                "api_key_encryption",
                api_key_encryption_works,
                {
                    "encryption_results": encryption_results,
                    "all_encrypted_properly": all_encrypted_properly,
                    "all_operations_successful": all_operations_successful
                }
            )
            
        except Exception as e:
            self.result.add_test_result(
                "api_key_encryption",
                False,
                {"error": str(e)}
            )
            self.result.add_security_issue(f"API key encryption failed: {str(e)}")
    
    async def _test_password_hashing(self):
        """Test password hashing security."""
        logger.info("Testing password hashing")
        
        try:
            from app.core.security import get_password_hash, verify_password
            
            # Test password hashing
            test_passwords = [
                "SimplePassword123!",
                "ComplexP@ssw0rd!@#$%",
                "日本語パスワード123!",
                "VeryLongPasswordWithManyCharactersAndSymbols!@#$%^&*()"
            ]
            
            hashing_results = {}
            
            for password in test_passwords:
                # Hash the password
                hashed = get_password_hash(password)
                
                # Verify the password
                verification_success = verify_password(password, hashed)
                
                # Verify wrong password fails
                wrong_password_fails = not verify_password(password + "wrong", hashed)
                
                # Check hash properties
                hash_different = hashed != password
                hash_long_enough = len(hashed) >= 60  # bcrypt hashes are typically 60 chars
                hash_has_salt = "$" in hashed  # bcrypt format includes $ separators
                
                hashing_results[password[:10] + "..."] = {
                    "hash_different": hash_different,
                    "hash_long_enough": hash_long_enough,
                    "hash_has_salt": hash_has_salt,
                    "verification_success": verification_success,
                    "wrong_password_fails": wrong_password_fails,
                    "hash_length": len(hashed)
                }
            
            # Test that same password produces different hashes (salt working)
            password = "TestPassword123!"
            hash1 = get_password_hash(password)
            hash2 = get_password_hash(password)
            salt_working = hash1 != hash2
            
            # Check all hashing operations work correctly
            all_hashing_correct = all(
                result["hash_different"] and
                result["hash_long_enough"] and
                result["verification_success"] and
                result["wrong_password_fails"]
                for result in hashing_results.values()
            )
            
            password_hashing_secure = all_hashing_correct and salt_working
            
            self.result.add_test_result(
                "password_hashing",
                password_hashing_secure,
                {
                    "hashing_results": hashing_results,
                    "salt_working": salt_working,
                    "all_hashing_correct": all_hashing_correct
                }
            )
            
        except Exception as e:
            self.result.add_test_result(
                "password_hashing",
                False,
                {"error": str(e)}
            )
            self.result.add_security_issue(f"Password hashing failed: {str(e)}")
    
    async def _test_jwt_token_security(self):
        """Test JWT token security."""
        logger.info("Testing JWT token security")
        
        try:
            from app.core.security import create_access_token, verify_token
            import jwt
            
            test_user_id = "test_user_12345"
            
            # Create token
            token = create_access_token(test_user_id)
            
            # Verify token
            verified_user_id = verify_token(token)
            token_verification_works = verified_user_id == test_user_id
            
            # Test token structure
            try:
                unverified_payload = jwt.decode(token, options={"verify_signature": False})
                token_has_expiration = "exp" in unverified_payload
                token_has_subject = "sub" in unverified_payload
                token_has_type = "type" in unverified_payload
                token_structure_valid = token_has_expiration and token_has_subject and token_has_type
            except Exception:
                token_structure_valid = False
            
            # Test token tampering protection
            tampered_token = token[:-5] + "XXXXX"
            tampered_verification = verify_token(tampered_token)
            tampering_protection_works = tampered_verification is None
            
            # Test token signing
            token_parts = token.split('.')
            token_has_signature = len(token_parts) == 3 and len(token_parts[2]) > 0
            
            # Test that tokens are different for different users
            token2 = create_access_token("different_user")
            tokens_different = token != token2
            
            jwt_security_good = (
                token_verification_works and
                token_structure_valid and
                tampering_protection_works and
                token_has_signature and
                tokens_different
            )
            
            self.result.add_test_result(
                "jwt_token_security",
                jwt_security_good,
                {
                    "token_verification_works": token_verification_works,
                    "token_structure_valid": token_structure_valid,
                    "tampering_protection_works": tampering_protection_works,
                    "token_has_signature": token_has_signature,
                    "tokens_different": tokens_different,
                    "token_length": len(token)
                }
            )
            
        except Exception as e:
            self.result.add_test_result(
                "jwt_token_security",
                False,
                {"error": str(e)}
            )
            self.result.add_security_issue(f"JWT token security failed: {str(e)}")
    
    async def _test_data_at_rest_encryption(self):
        """Test data at rest encryption capabilities."""
        logger.info("Testing data at rest encryption")
        
        try:
            encryption_manager = EncryptionManager()
            
            # Test encryption of various data types that would be stored
            test_data_types = {
                "user_personal_data": {
                    "email": "user@example.com",
                    "phone": "+81-90-1234-5678",
                    "address": "Tokyo, Japan"
                },
                "api_credentials": {
                    "service": "alpha_vantage",
                    "api_key": "AV_SECRET_KEY_12345",
                    "secret": "SECRET_VALUE_67890"
                },
                "financial_data": {
                    "account_number": "1234567890",
                    "routing_number": "987654321",
                    "balance": "10000.50"
                }
            }
            
            encryption_test_results = {}
            
            for data_type, data in test_data_types.items():
                # Encrypt the data
                encrypted_data = encryption_manager.encrypt_dict(data)
                
                # Decrypt the data
                decrypted_data = encryption_manager.decrypt_dict(encrypted_data)
                
                # Verify encryption/decryption works
                decryption_successful = decrypted_data == data
                
                # Verify data is actually encrypted
                data_actually_encrypted = all(
                    encrypted_data[key] != data[key] 
                    for key in data.keys()
                )
                
                encryption_test_results[data_type] = {
                    "decryption_successful": decryption_successful,
                    "data_actually_encrypted": data_actually_encrypted,
                    "encrypted_fields_count": len(encrypted_data)
                }
            
            # Test large data encryption
            large_data = "A" * 10000  # 10KB of data
            large_encrypted = encryption_manager.encrypt(large_data)
            large_decrypted = encryption_manager.decrypt(large_encrypted)
            large_data_handling = large_decrypted == large_data
            
            all_encryption_tests_pass = (
                all(
                    result["decryption_successful"] and result["data_actually_encrypted"]
                    for result in encryption_test_results.values()
                ) and
                large_data_handling
            )
            
            self.result.add_test_result(
                "data_at_rest_encryption",
                all_encryption_tests_pass,
                {
                    "encryption_test_results": encryption_test_results,
                    "large_data_handling": large_data_handling,
                    "all_tests_pass": all_encryption_tests_pass
                }
            )
            
        except Exception as e:
            self.result.add_test_result(
                "data_at_rest_encryption",
                False,
                {"error": str(e)}
            )
            self.result.add_security_issue(f"Data at rest encryption failed: {str(e)}")
    
    async def _test_encryption_key_management(self):
        """Test encryption key management security."""
        logger.info("Testing encryption key management")
        
        try:
            # Test that encryption keys are properly derived
            encryption_manager1 = EncryptionManager()
            encryption_manager2 = EncryptionManager()
            
            test_data = "test_encryption_consistency"
            
            # Test that same data encrypts to different values (due to IV/nonce)
            encrypted1 = encryption_manager1.encrypt(test_data)
            encrypted2 = encryption_manager1.encrypt(test_data)
            different_encryptions = encrypted1 != encrypted2
            
            # Test that both can decrypt each other's data (same key)
            decrypted1 = encryption_manager1.decrypt(encrypted2)
            decrypted2 = encryption_manager2.decrypt(encrypted1)
            cross_decryption_works = decrypted1 == test_data and decrypted2 == test_data
            
            # Test key derivation consistency
            key_derivation_consistent = cross_decryption_works
            
            # Test that master key is not exposed
            master_key_not_exposed = not hasattr(encryption_manager1, 'master_key') or \
                                   encryption_manager1.master_key != settings.SECRET_KEY
            
            # Test encryption strength (encrypted data should be significantly different)
            encryption_strength_good = (
                len(encrypted1) > len(test_data) and
                not any(char in encrypted1 for char in test_data)
            )
            
            key_management_secure = (
                different_encryptions and
                cross_decryption_works and
                key_derivation_consistent and
                encryption_strength_good
            )
            
            self.result.add_test_result(
                "encryption_key_management",
                key_management_secure,
                {
                    "different_encryptions": different_encryptions,
                    "cross_decryption_works": cross_decryption_works,
                    "key_derivation_consistent": key_derivation_consistent,
                    "master_key_not_exposed": master_key_not_exposed,
                    "encryption_strength_good": encryption_strength_good
                }
            )
            
        except Exception as e:
            self.result.add_test_result(
                "encryption_key_management",
                False,
                {"error": str(e)}
            )
            self.result.add_security_issue(f"Encryption key management failed: {str(e)}")
    
    def generate_report(self) -> str:
        """Generate a comprehensive encryption validation report."""
        summary = self.result.get_summary()
        
        report = f"""
# Data Encryption and Secure Storage Validation Report
Generated: {summary['test_timestamp']}

## Executive Summary
- **Overall Status**: {summary['overall_status']}
- **Tests Run**: {summary['tests_run']}
- **Tests Passed**: {summary['tests_passed']}
- **Tests Failed**: {summary['tests_failed']}
- **Success Rate**: {summary['success_rate']:.1f}%
- **Security Issues**: {summary['security_issues_count']}

## Security Issues
"""
        
        if self.result.security_issues:
            for issue in self.result.security_issues:
                report += f"- ❌ {issue}\n"
        else:
            report += "- ✅ No security issues found\n"
        
        report += "\n## Detailed Test Results\n"
        for test_name, result in self.result.test_results.items():
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            report += f"### {test_name} - {status}\n"
            report += f"- Timestamp: {result['timestamp']}\n"
            
            if isinstance(result["details"], dict):
                for key, value in result["details"].items():
                    if isinstance(value, (dict, list)):
                        report += f"- {key}: {json.dumps(value, indent=2)}\n"
                    else:
                        report += f"- {key}: {value}\n"
            else:
                report += f"- Details: {result['details']}\n"
            report += "\n"
        
        return report


async def main():
    """Main function to run encryption validation tests."""
    print("🔐 Starting Data Encryption and Secure Storage Validation")
    print("=" * 65)
    
    validator = EncryptionValidator()
    result = await validator.run_all_tests()
    
    # Generate and save report
    report = validator.generate_report()
    
    # Save report to file
    report_filename = f"encryption_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_filename, 'w') as f:
        f.write(report)
    
    # Save detailed results as JSON
    json_filename = f"encryption_validation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_filename, 'w') as f:
        json.dump({
            "summary": result.get_summary(),
            "test_results": result.test_results,
            "security_issues": result.security_issues
        }, f, indent=2)
    
    print(f"\n📊 Encryption Validation Results:")
    print(f"- Tests Run: {result.tests_run}")
    print(f"- Tests Passed: {result.tests_passed}")
    print(f"- Tests Failed: {result.tests_failed}")
    print(f"- Success Rate: {(result.tests_passed / result.tests_run * 100):.1f}%")
    print(f"- Security Issues: {len(result.security_issues)}")
    
    print(f"\n📄 Reports saved:")
    print(f"- Markdown Report: {report_filename}")
    print(f"- JSON Results: {json_filename}")
    
    # Print summary
    if result.security_issues:
        print(f"\n❌ VALIDATION FAILED - {len(result.security_issues)} security issues found")
        for issue in result.security_issues:
            print(f"  - {issue}")
        return 1
    elif result.tests_failed > 0:
        print(f"\n⚠️ VALIDATION COMPLETED WITH ISSUES - {result.tests_failed} tests failed")
        return 1
    else:
        print(f"\n✅ VALIDATION PASSED - All encryption tests passed")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)