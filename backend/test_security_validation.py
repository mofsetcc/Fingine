#!/usr/bin/env python3
"""
Simple test script to validate security validation scripts work correctly.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

async def test_security_audit():
    """Test the security audit functionality."""
    print("Testing security audit...")
    
    try:
        from security_audit import SecurityAuditor
        
        auditor = SecurityAuditor()
        
        # Test a few key security functions
        from app.core.security import get_password_hash, verify_password
        from app.core.encryption import EncryptionManager
        
        # Test password hashing
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        verified = verify_password(password, hashed)
        
        print(f"  ✅ Password hashing: {'PASS' if verified else 'FAIL'}")
        
        # Test encryption
        encryption_manager = EncryptionManager()
        test_data = "sensitive_data_test"
        encrypted = encryption_manager.encrypt(test_data)
        decrypted = encryption_manager.decrypt(encrypted)
        
        encryption_works = decrypted == test_data and encrypted != test_data
        print(f"  ✅ Data encryption: {'PASS' if encryption_works else 'FAIL'}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Security audit test failed: {str(e)}")
        return False

async def test_gdpr_compliance():
    """Test GDPR compliance functionality."""
    print("Testing GDPR compliance...")
    
    try:
        from app.core.encryption import DataAnonymizer
        
        anonymizer = DataAnonymizer()
        
        # Test email anonymization
        email = "test@example.com"
        anonymized_email = anonymizer.anonymize_email(email)
        email_anonymized = anonymized_email != email and "@" in anonymized_email
        
        print(f"  ✅ Email anonymization: {'PASS' if email_anonymized else 'FAIL'}")
        
        # Test IP anonymization
        ip = "192.168.1.100"
        anonymized_ip = anonymizer.anonymize_ip(ip)
        ip_anonymized = anonymized_ip != ip and "*" in anonymized_ip
        
        print(f"  ✅ IP anonymization: {'PASS' if ip_anonymized else 'FAIL'}")
        
        return email_anonymized and ip_anonymized
        
    except Exception as e:
        print(f"  ❌ GDPR compliance test failed: {str(e)}")
        return False

async def test_rate_limiting():
    """Test rate limiting functionality."""
    print("Testing rate limiting...")
    
    try:
        from app.core.rate_limiting import RateLimiter
        
        rate_limiter = RateLimiter()
        
        # Test basic rate limiting
        test_key = "test_user"
        limit = 3
        window = 60
        
        # Make requests up to limit
        allowed_count = 0
        for i in range(limit + 1):
            is_allowed, remaining, reset_time = await rate_limiter.is_allowed(
                test_key, limit, window, "test"
            )
            if is_allowed:
                allowed_count += 1
        
        rate_limiting_works = allowed_count == limit
        print(f"  ✅ Rate limiting enforcement: {'PASS' if rate_limiting_works else 'FAIL'}")
        
        return rate_limiting_works
        
    except Exception as e:
        print(f"  ❌ Rate limiting test failed: {str(e)}")
        return False

async def test_data_encryption():
    """Test data encryption functionality."""
    print("Testing data encryption...")
    
    try:
        from app.core.encryption import EncryptionManager, SecureConfigManager
        
        encryption_manager = EncryptionManager()
        
        # Test string encryption
        test_data = "secret_api_key_12345"
        encrypted = encryption_manager.encrypt(test_data)
        decrypted = encryption_manager.decrypt(encrypted)
        
        string_encryption_works = decrypted == test_data and encrypted != test_data
        print(f"  ✅ String encryption: {'PASS' if string_encryption_works else 'FAIL'}")
        
        # Test dictionary encryption
        test_dict = {"api_key": "secret123", "token": "token456"}
        encrypted_dict = encryption_manager.encrypt_dict(test_dict)
        decrypted_dict = encryption_manager.decrypt_dict(encrypted_dict)
        
        dict_encryption_works = decrypted_dict == test_dict
        print(f"  ✅ Dictionary encryption: {'PASS' if dict_encryption_works else 'FAIL'}")
        
        # Test secure config
        secure_config = SecureConfigManager(encryption_manager)
        test_service = "test_service"
        test_key = "test_api_key_789"
        
        config_set = secure_config.set_api_key(test_service, test_key)
        retrieved_key = secure_config.get_api_key(test_service)
        
        secure_config_works = config_set and retrieved_key == test_key
        print(f"  ✅ Secure config management: {'PASS' if secure_config_works else 'FAIL'}")
        
        return string_encryption_works and dict_encryption_works and secure_config_works
        
    except Exception as e:
        print(f"  ❌ Data encryption test failed: {str(e)}")
        return False

async def main():
    """Run all security validation tests."""
    print("🔒 Running Security Validation Tests")
    print("=" * 50)
    
    tests = [
        ("Security Audit", test_security_audit),
        ("GDPR Compliance", test_gdpr_compliance),
        ("Rate Limiting", test_rate_limiting),
        ("Data Encryption", test_data_encryption)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"  ❌ Test failed with exception: {str(e)}")
            results[test_name] = False
    
    # Summary
    print(f"\n📊 Test Results Summary")
    print("=" * 30)
    
    passed_count = sum(1 for result in results.values() if result)
    total_count = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("🎉 All security validation tests passed!")
        return 0
    else:
        print("⚠️ Some security validation tests failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)