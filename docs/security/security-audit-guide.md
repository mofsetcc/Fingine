# Security Audit and Penetration Testing Guide

This guide outlines the security audit and penetration testing procedures for Project Kessan.

## Security Audit Checklist

### 1. Authentication and Authorization

#### JWT Token Security
- [ ] JWT tokens use strong signing algorithms (RS256 or HS256 with strong keys)
- [ ] Token expiration times are appropriate (access: 30min, refresh: 7 days)
- [ ] Refresh token rotation implemented
- [ ] Token blacklisting mechanism in place
- [ ] Secure token storage on client side

#### OAuth Integration
- [ ] OAuth flows properly implemented (authorization code flow)
- [ ] State parameter used to prevent CSRF attacks
- [ ] Redirect URIs properly validated
- [ ] OAuth tokens securely stored and transmitted
- [ ] Proper scope validation

#### Password Security
- [ ] Strong password requirements enforced
- [ ] Password hashing using bcrypt with appropriate cost factor
- [ ] Password reset tokens are cryptographically secure
- [ ] Account lockout after failed attempts
- [ ] Password history to prevent reuse

### 2. API Security

#### Input Validation
- [ ] All input parameters validated and sanitized
- [ ] SQL injection protection (parameterized queries)
- [ ] XSS protection (output encoding)
- [ ] File upload restrictions and validation
- [ ] Request size limits enforced

#### Rate Limiting
- [ ] Rate limiting implemented per endpoint
- [ ] Different limits for authenticated vs anonymous users
- [ ] Rate limiting based on IP and user ID
- [ ] Proper error messages for rate limit exceeded
- [ ] Rate limiting bypass protection

#### CORS Configuration
- [ ] CORS origins properly configured
- [ ] Credentials handling secure
- [ ] Preflight requests handled correctly
- [ ] No wildcard origins in production

### 3. Data Protection

#### Encryption
- [ ] Data encrypted at rest (database, S3)
- [ ] Data encrypted in transit (HTTPS/TLS)
- [ ] Strong encryption algorithms used (AES-256)
- [ ] Proper key management (AWS KMS)
- [ ] PII data specifically encrypted

#### Data Access Controls
- [ ] Database access restricted to application
- [ ] Principle of least privilege applied
- [ ] Database credentials rotated regularly
- [ ] Audit logging for data access
- [ ] Data retention policies implemented

### 4. Infrastructure Security

#### Network Security
- [ ] VPC properly configured with private subnets
- [ ] Security groups follow least privilege
- [ ] Network ACLs configured appropriately
- [ ] No direct internet access to databases
- [ ] WAF rules configured and active

#### Container Security
- [ ] Docker images scanned for vulnerabilities
- [ ] Base images regularly updated
- [ ] Non-root user in containers
- [ ] Secrets not embedded in images
- [ ] Resource limits configured

#### AWS Security
- [ ] IAM roles follow least privilege
- [ ] MFA enabled for all admin accounts
- [ ] CloudTrail logging enabled
- [ ] GuardDuty enabled for threat detection
- [ ] Config rules for compliance monitoring

## Automated Security Testing

### 1. SAST (Static Application Security Testing)

```yaml
# .github/workflows/security-scan.yml
name: Security Scan

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Run Bandit Security Scan
      run: |
        pip install bandit
        bandit -r backend/app/ -f json -o bandit-report.json
    
    - name: Run Safety Check
      run: |
        pip install safety
        safety check --json --output safety-report.json
    
    - name: Run Semgrep
      uses: returntocorp/semgrep-action@v1
      with:
        config: >-
          p/security-audit
          p/secrets
          p/owasp-top-ten
    
    - name: Upload Security Reports
      uses: actions/upload-artifact@v3
      with:
        name: security-reports
        path: |
          bandit-report.json
          safety-report.json
```

### 2. DAST (Dynamic Application Security Testing)

```bash
#!/bin/bash
# scripts/run-security-tests.sh

set -e

API_BASE_URL=${1:-"https://staging-api.kessan.ai"}
REPORT_DIR="security-reports/$(date +%Y%m%d-%H%M%S)"

mkdir -p $REPORT_DIR

echo "Running OWASP ZAP security scan against $API_BASE_URL"

# Start ZAP daemon
docker run -d --name zap-daemon \
  -p 8080:8080 \
  -v $(pwd)/$REPORT_DIR:/zap/wrk/:rw \
  owasp/zap2docker-stable zap.sh -daemon -host 0.0.0.0 -port 8080

# Wait for ZAP to start
sleep 30

# Run baseline scan
docker exec zap-daemon zap-baseline.py \
  -t $API_BASE_URL \
  -J zap-baseline-report.json \
  -r zap-baseline-report.html

# Run API scan with OpenAPI spec
docker exec zap-daemon zap-api-scan.py \
  -t $API_BASE_URL/docs/openapi.json \
  -f openapi \
  -J zap-api-report.json \
  -r zap-api-report.html

# Run full scan (takes longer)
docker exec zap-daemon zap-full-scan.py \
  -t $API_BASE_URL \
  -J zap-full-report.json \
  -r zap-full-report.html

# Stop and remove ZAP container
docker stop zap-daemon
docker rm zap-daemon

echo "Security scan completed. Reports saved to $REPORT_DIR"
```

### 3. Container Security Scanning

```bash
#!/bin/bash
# scripts/scan-container-security.sh

IMAGES=("kessan-api:latest" "kessan-frontend:latest")
REPORT_DIR="security-reports/container-scan-$(date +%Y%m%d-%H%M%S)"

mkdir -p $REPORT_DIR

for IMAGE in "${IMAGES[@]}"; do
  echo "Scanning $IMAGE for vulnerabilities..."
  
  # Trivy scan
  docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    -v $(pwd)/$REPORT_DIR:/reports \
    aquasec/trivy image --format json --output /reports/trivy-$IMAGE.json $IMAGE
  
  # Clair scan (if available)
  # docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  #   quay.io/coreos/clair:latest
  
  echo "Scan completed for $IMAGE"
done

echo "Container security scans completed. Reports saved to $REPORT_DIR"
```

## Manual Penetration Testing

### 1. Authentication Testing

```python
# scripts/pentest-auth.py
import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor

class AuthPenTest:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
    
    def test_brute_force_protection(self):
        """Test account lockout after failed login attempts."""
        print("Testing brute force protection...")
        
        login_url = f"{self.base_url}/api/v1/auth/login"
        test_email = "test@example.com"
        
        # Attempt multiple failed logins
        for i in range(10):
            response = self.session.post(login_url, json={
                "email": test_email,
                "password": f"wrongpassword{i}"
            })
            
            print(f"Attempt {i+1}: Status {response.status_code}")
            
            if response.status_code == 429:
                print("✓ Rate limiting activated")
                break
            
            time.sleep(1)
        else:
            print("✗ No rate limiting detected - SECURITY ISSUE")
    
    def test_jwt_token_validation(self):
        """Test JWT token validation."""
        print("Testing JWT token validation...")
        
        # Test with invalid token
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = self.session.get(
            f"{self.base_url}/api/v1/auth/me",
            headers=headers
        )
        
        if response.status_code == 401:
            print("✓ Invalid token properly rejected")
        else:
            print("✗ Invalid token accepted - SECURITY ISSUE")
        
        # Test with expired token (would need to generate one)
        # Test with tampered token
        
    def test_password_requirements(self):
        """Test password strength requirements."""
        print("Testing password requirements...")
        
        weak_passwords = [
            "123456",
            "password",
            "abc123",
            "qwerty",
            "12345678"
        ]
        
        register_url = f"{self.base_url}/api/v1/auth/register"
        
        for password in weak_passwords:
            response = self.session.post(register_url, json={
                "email": f"test{password}@example.com",
                "password": password
            })
            
            if response.status_code == 400:
                print(f"✓ Weak password '{password}' rejected")
            else:
                print(f"✗ Weak password '{password}' accepted - SECURITY ISSUE")
    
    def test_oauth_security(self):
        """Test OAuth implementation security."""
        print("Testing OAuth security...")
        
        # Test state parameter
        oauth_url = f"{self.base_url}/api/v1/auth/oauth/google"
        
        # Test without state parameter
        response = self.session.post(oauth_url, json={
            "access_token": "fake_token"
        })
        
        # Should validate the OAuth token properly
        if response.status_code in [400, 401]:
            print("✓ Invalid OAuth token rejected")
        else:
            print("✗ OAuth validation may be insufficient")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python pentest-auth.py <base_url>")
        sys.exit(1)
    
    base_url = sys.argv[1]
    pentest = AuthPenTest(base_url)
    
    pentest.test_brute_force_protection()
    pentest.test_jwt_token_validation()
    pentest.test_password_requirements()
    pentest.test_oauth_security()
```

### 2. API Security Testing

```python
# scripts/pentest-api.py
import requests
import json
import string
import random

class APIPenTest:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
    
    def test_sql_injection(self):
        """Test for SQL injection vulnerabilities."""
        print("Testing SQL injection protection...")
        
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "1' OR 1=1#",
            "admin'--"
        ]
        
        # Test search endpoint
        search_url = f"{self.base_url}/api/v1/stocks/search"
        
        for payload in sql_payloads:
            response = self.session.get(search_url, params={"query": payload})
            
            # Check for SQL error messages
            if any(error in response.text.lower() for error in 
                   ["sql", "mysql", "postgresql", "syntax error", "database"]):
                print(f"✗ Potential SQL injection vulnerability with payload: {payload}")
            else:
                print(f"✓ SQL injection payload blocked: {payload}")
    
    def test_xss_protection(self):
        """Test for XSS vulnerabilities."""
        print("Testing XSS protection...")
        
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//",
            "<svg onload=alert('xss')>"
        ]
        
        # Test endpoints that might reflect user input
        endpoints = [
            "/api/v1/stocks/search",
            "/api/v1/watchlist"
        ]
        
        for endpoint in endpoints:
            for payload in xss_payloads:
                response = self.session.get(
                    f"{self.base_url}{endpoint}",
                    params={"query": payload}
                )
                
                if payload in response.text:
                    print(f"✗ Potential XSS vulnerability in {endpoint}")
                else:
                    print(f"✓ XSS payload filtered in {endpoint}")
    
    def test_rate_limiting(self):
        """Test API rate limiting."""
        print("Testing rate limiting...")
        
        search_url = f"{self.base_url}/api/v1/stocks/search"
        
        # Make rapid requests
        for i in range(50):
            response = self.session.get(search_url, params={"query": "test"})
            
            if response.status_code == 429:
                print(f"✓ Rate limiting activated after {i+1} requests")
                break
            
            if i == 49:
                print("✗ No rate limiting detected - SECURITY ISSUE")
    
    def test_input_validation(self):
        """Test input validation."""
        print("Testing input validation...")
        
        # Test with oversized input
        large_input = "A" * 10000
        response = self.session.get(
            f"{self.base_url}/api/v1/stocks/search",
            params={"query": large_input}
        )
        
        if response.status_code == 400:
            print("✓ Large input properly rejected")
        else:
            print("✗ Large input accepted - potential DoS vector")
        
        # Test with special characters
        special_chars = "!@#$%^&*()[]{}|;:,.<>?"
        response = self.session.get(
            f"{self.base_url}/api/v1/stocks/search",
            params={"query": special_chars}
        )
        
        # Should handle gracefully without errors
        if response.status_code in [200, 400]:
            print("✓ Special characters handled properly")
        else:
            print("✗ Special characters caused server error")
    
    def test_authorization_bypass(self):
        """Test for authorization bypass vulnerabilities."""
        print("Testing authorization bypass...")
        
        protected_endpoints = [
            "/api/v1/auth/me",
            "/api/v1/watchlist",
            "/api/v1/subscription/my-subscription"
        ]
        
        for endpoint in protected_endpoints:
            # Test without authentication
            response = self.session.get(f"{self.base_url}{endpoint}")
            
            if response.status_code == 401:
                print(f"✓ {endpoint} properly protected")
            else:
                print(f"✗ {endpoint} accessible without auth - SECURITY ISSUE")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python pentest-api.py <base_url>")
        sys.exit(1)
    
    base_url = sys.argv[1]
    pentest = APIPenTest(base_url)
    
    pentest.test_sql_injection()
    pentest.test_xss_protection()
    pentest.test_rate_limiting()
    pentest.test_input_validation()
    pentest.test_authorization_bypass()
```

### 3. Infrastructure Security Testing

```bash
#!/bin/bash
# scripts/pentest-infrastructure.sh

TARGET_DOMAIN=${1:-"kessan.ai"}
REPORT_DIR="security-reports/infrastructure-$(date +%Y%m%d-%H%M%S)"

mkdir -p $REPORT_DIR

echo "Running infrastructure security tests for $TARGET_DOMAIN"

# SSL/TLS Configuration Test
echo "Testing SSL/TLS configuration..."
docker run --rm -v $(pwd)/$REPORT_DIR:/output \
  drwetter/testssl.sh --jsonfile /output/ssl-report.json $TARGET_DOMAIN

# DNS Security Test
echo "Testing DNS configuration..."
dig +short $TARGET_DOMAIN > $REPORT_DIR/dns-records.txt
dig +short TXT $TARGET_DOMAIN >> $REPORT_DIR/dns-records.txt

# Port Scan
echo "Running port scan..."
nmap -sS -O -A $TARGET_DOMAIN > $REPORT_DIR/nmap-scan.txt

# HTTP Security Headers Test
echo "Testing HTTP security headers..."
curl -I https://$TARGET_DOMAIN > $REPORT_DIR/http-headers.txt

# Check for common vulnerabilities
echo "Checking for common web vulnerabilities..."
nikto -h https://$TARGET_DOMAIN -output $REPORT_DIR/nikto-report.txt

echo "Infrastructure security tests completed. Reports saved to $REPORT_DIR"
```

## Security Compliance Checklist

### OWASP Top 10 (2021)
- [ ] A01:2021 – Broken Access Control
- [ ] A02:2021 – Cryptographic Failures
- [ ] A03:2021 – Injection
- [ ] A04:2021 – Insecure Design
- [ ] A05:2021 – Security Misconfiguration
- [ ] A06:2021 – Vulnerable and Outdated Components
- [ ] A07:2021 – Identification and Authentication Failures
- [ ] A08:2021 – Software and Data Integrity Failures
- [ ] A09:2021 – Security Logging and Monitoring Failures
- [ ] A10:2021 – Server-Side Request Forgery (SSRF)

### GDPR Compliance
- [ ] Data processing lawful basis documented
- [ ] Privacy policy updated and accessible
- [ ] Data subject rights implemented (access, rectification, erasure)
- [ ] Data breach notification procedures in place
- [ ] Data protection impact assessment completed
- [ ] Data retention policies implemented
- [ ] Cross-border data transfer safeguards in place

### SOC 2 Type II (if applicable)
- [ ] Security controls documented
- [ ] Availability controls implemented
- [ ] Processing integrity controls in place
- [ ] Confidentiality controls active
- [ ] Privacy controls operational

## Remediation Procedures

### Critical Vulnerabilities (Fix within 24 hours)
1. **Immediate Response**
   - Isolate affected systems
   - Implement temporary mitigations
   - Notify security team and management

2. **Assessment**
   - Determine scope of vulnerability
   - Assess potential impact
   - Document findings

3. **Remediation**
   - Develop and test fix
   - Deploy to production
   - Verify fix effectiveness

4. **Post-Incident**
   - Update security documentation
   - Conduct lessons learned session
   - Implement preventive measures

### High Vulnerabilities (Fix within 7 days)
- Follow similar process with extended timeline
- May require more thorough testing
- Coordinate with development team for fixes

### Medium/Low Vulnerabilities (Fix within 30 days)
- Include in regular development cycle
- Batch similar fixes together
- Document in security backlog

## Reporting and Documentation

### Security Test Report Template
```markdown
# Security Assessment Report

## Executive Summary
- Overall security posture
- Critical findings summary
- Recommendations priority

## Methodology
- Testing approach
- Tools used
- Scope and limitations

## Findings
### Critical Issues
- Issue description
- Impact assessment
- Remediation steps

### High Priority Issues
- [Similar format]

### Medium Priority Issues
- [Similar format]

## Recommendations
- Immediate actions required
- Long-term security improvements
- Process improvements

## Appendices
- Detailed test results
- Tool outputs
- Supporting documentation
```

This comprehensive security audit and penetration testing guide ensures thorough security validation before production deployment.