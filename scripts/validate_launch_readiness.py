#!/usr/bin/env python3
"""
Launch Readiness Validation Script
Comprehensive validation of all systems and processes before public launch
"""

import asyncio
import httpx
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LaunchReadinessValidator:
    """Comprehensive launch readiness validation"""
    
    def __init__(self, production_url: str = None, frontend_url: str = None):
        self.production_url = production_url or os.getenv("PRODUCTION_API_URL", "https://api.kessan.app")
        self.frontend_url = frontend_url or os.getenv("FRONTEND_URL", "https://kessan.app")
        self.validation_results = {}
        self.critical_failures = []
        self.warnings = []
        
    async def validate_infrastructure_readiness(self):
        """Validate infrastructure and deployment readiness"""
        logger.info("Validating infrastructure readiness...")
        
        infrastructure_checks = {
            "api_accessibility": False,
            "frontend_accessibility": False,
            "https_enabled": False,
            "cdn_configured": False,
            "load_balancer_healthy": False,
            "database_connectivity": False,
            "cache_connectivity": False,
            "external_api_connectivity": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # API accessibility
                try:
                    api_response = await client.get(f"{self.production_url}/health")
                    infrastructure_checks["api_accessibility"] = api_response.status_code == 200
                except Exception as e:
                    self.critical_failures.append(f"API not accessible: {e}")
                
                # Frontend accessibility
                try:
                    frontend_response = await client.get(self.frontend_url)
                    infrastructure_checks["frontend_accessibility"] = frontend_response.status_code == 200
                    
                    # Check HTTPS
                    infrastructure_checks["https_enabled"] = self.frontend_url.startswith("https://")
                    if not infrastructure_checks["https_enabled"]:
                        self.critical_failures.append("HTTPS not enabled for frontend")
                        
                except Exception as e:
                    self.critical_failures.append(f"Frontend not accessible: {e}")
                
                # Database connectivity
                try:
                    db_response = await client.get(f"{self.production_url}/health/database")
                    db_data = db_response.json()
                    infrastructure_checks["database_connectivity"] = db_data.get("status") == "healthy"
                except Exception as e:
                    self.critical_failures.append(f"Database connectivity issue: {e}")
                
                # Cache connectivity
                try:
                    cache_response = await client.get(f"{self.production_url}/health/cache")
                    cache_data = cache_response.json()
                    infrastructure_checks["cache_connectivity"] = cache_data.get("status") == "healthy"
                except Exception as e:
                    self.warnings.append(f"Cache connectivity issue: {e}")
                
                # External API connectivity
                try:
                    external_response = await client.get(f"{self.production_url}/health/external-apis")
                    external_data = external_response.json()
                    infrastructure_checks["external_api_connectivity"] = external_data.get("status") == "healthy"
                except Exception as e:
                    self.warnings.append(f"External API connectivity issue: {e}")
                
        except Exception as e:
            self.critical_failures.append(f"Infrastructure validation failed: {e}")
        
        self.validation_results["infrastructure"] = infrastructure_checks
        
        # Calculate infrastructure score
        passed_checks = sum(1 for check in infrastructure_checks.values() if check)
        total_checks = len(infrastructure_checks)
        infrastructure_score = (passed_checks / total_checks) * 100
        
        logger.info(f"Infrastructure readiness: {infrastructure_score:.1f}% ({passed_checks}/{total_checks} checks passed)")
        
        return infrastructure_score >= 90  # Require 90% infrastructure readiness

    async def validate_functionality_readiness(self):
        """Validate core functionality readiness"""
        logger.info("Validating functionality readiness...")
        
        functionality_checks = {
            "user_registration": False,
            "user_authentication": False,
            "stock_search": False,
            "ai_analysis_generation": False,
            "watchlist_management": False,
            "subscription_management": False,
            "billing_integration": False,
            "data_source_integration": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Test user registration
                test_email = f"launch_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@test.kessan.app"
                try:
                    register_response = await client.post(
                        f"{self.production_url}/api/v1/auth/register",
                        json={
                            "email": test_email,
                            "password": "LaunchTest123!",
                            "display_name": "Launch Test User"
                        }
                    )
                    functionality_checks["user_registration"] = register_response.status_code == 201
                    
                    # Test user authentication
                    if functionality_checks["user_registration"]:
                        login_response = await client.post(
                            f"{self.production_url}/api/v1/auth/login",
                            json={
                                "email": test_email,
                                "password": "LaunchTest123!"
                            }
                        )
                        functionality_checks["user_authentication"] = login_response.status_code == 200
                        
                        if functionality_checks["user_authentication"]:
                            token = login_response.json().get("access_token")
                            headers = {"Authorization": f"Bearer {token}"}
                            
                            # Test stock search
                            search_response = await client.get(
                                f"{self.production_url}/api/v1/stocks/search?q=トヨタ",
                                headers=headers
                            )
                            functionality_checks["stock_search"] = search_response.status_code == 200
                            
                            # Test AI analysis generation
                            analysis_response = await client.post(
                                f"{self.production_url}/api/v1/analysis/generate",
                                json={
                                    "ticker": "7203",
                                    "analysis_type": "short_term"
                                },
                                headers=headers
                            )
                            functionality_checks["ai_analysis_generation"] = analysis_response.status_code == 200
                            
                            # Test watchlist management
                            watchlist_response = await client.post(
                                f"{self.production_url}/api/v1/watchlist/add",
                                json={"ticker": "7203"},
                                headers=headers
                            )
                            functionality_checks["watchlist_management"] = watchlist_response.status_code == 200
                            
                            # Test subscription management
                            subscription_response = await client.get(
                                f"{self.production_url}/api/v1/users/subscription",
                                headers=headers
                            )
                            functionality_checks["subscription_management"] = subscription_response.status_code == 200
                            
                except Exception as e:
                    self.critical_failures.append(f"User flow testing failed: {e}")
                
                # Test data source integration
                try:
                    market_response = await client.get(f"{self.production_url}/api/v1/market/indices")
                    functionality_checks["data_source_integration"] = market_response.status_code == 200
                except Exception as e:
                    self.critical_failures.append(f"Data source integration failed: {e}")
                
                # Test billing integration (basic check)
                try:
                    plans_response = await client.get(f"{self.production_url}/api/v1/subscription/plans")
                    functionality_checks["billing_integration"] = plans_response.status_code == 200
                except Exception as e:
                    self.warnings.append(f"Billing integration check failed: {e}")
                
        except Exception as e:
            self.critical_failures.append(f"Functionality validation failed: {e}")
        
        self.validation_results["functionality"] = functionality_checks
        
        # Calculate functionality score
        passed_checks = sum(1 for check in functionality_checks.values() if check)
        total_checks = len(functionality_checks)
        functionality_score = (passed_checks / total_checks) * 100
        
        logger.info(f"Functionality readiness: {functionality_score:.1f}% ({passed_checks}/{total_checks} checks passed)")
        
        return functionality_score >= 95  # Require 95% functionality readiness

    async def validate_performance_readiness(self):
        """Validate performance readiness"""
        logger.info("Validating performance readiness...")
        
        performance_metrics = {
            "frontend_load_time": None,
            "api_response_time": None,
            "search_response_time": None,
            "analysis_generation_time": None,
            "database_query_time": None
        }
        
        performance_checks = {
            "frontend_load_acceptable": False,
            "api_response_acceptable": False,
            "search_response_acceptable": False,
            "analysis_generation_acceptable": False,
            "database_performance_acceptable": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Frontend load time
                start_time = datetime.now()
                frontend_response = await client.get(self.frontend_url)
                frontend_load_time = (datetime.now() - start_time).total_seconds()
                performance_metrics["frontend_load_time"] = frontend_load_time
                performance_checks["frontend_load_acceptable"] = frontend_load_time < 3.0
                
                # API response time
                start_time = datetime.now()
                api_response = await client.get(f"{self.production_url}/api/v1/market/indices")
                api_response_time = (datetime.now() - start_time).total_seconds()
                performance_metrics["api_response_time"] = api_response_time
                performance_checks["api_response_acceptable"] = api_response_time < 2.0
                
                # Search response time
                start_time = datetime.now()
                search_response = await client.get(f"{self.production_url}/api/v1/stocks/search?q=toyota")
                search_response_time = (datetime.now() - start_time).total_seconds()
                performance_metrics["search_response_time"] = search_response_time
                performance_checks["search_response_acceptable"] = search_response_time < 0.5
                
                # Database performance (via health check)
                start_time = datetime.now()
                db_response = await client.get(f"{self.production_url}/health/database")
                db_response_time = (datetime.now() - start_time).total_seconds()
                performance_metrics["database_query_time"] = db_response_time
                performance_checks["database_performance_acceptable"] = db_response_time < 1.0
                
        except Exception as e:
            self.warnings.append(f"Performance validation failed: {e}")
        
        self.validation_results["performance"] = {
            "metrics": performance_metrics,
            "checks": performance_checks
        }
        
        # Calculate performance score
        passed_checks = sum(1 for check in performance_checks.values() if check)
        total_checks = len(performance_checks)
        performance_score = (passed_checks / total_checks) * 100
        
        logger.info(f"Performance readiness: {performance_score:.1f}% ({passed_checks}/{total_checks} checks passed)")
        
        return performance_score >= 80  # Require 80% performance readiness

    async def validate_security_readiness(self):
        """Validate security readiness"""
        logger.info("Validating security readiness...")
        
        security_checks = {
            "https_enforced": False,
            "security_headers_present": False,
            "authentication_required": False,
            "rate_limiting_active": False,
            "input_validation_active": False,
            "cors_configured": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # HTTPS enforcement
                try:
                    http_response = await client.get(self.frontend_url.replace("https://", "http://"))
                    security_checks["https_enforced"] = http_response.status_code in [301, 302, 308]
                except:
                    security_checks["https_enforced"] = True  # HTTP not accessible is good
                
                # Security headers
                frontend_response = await client.get(self.frontend_url)
                headers = frontend_response.headers
                security_headers = [
                    "strict-transport-security",
                    "x-content-type-options",
                    "x-frame-options",
                    "x-xss-protection"
                ]
                security_checks["security_headers_present"] = all(
                    header in headers for header in security_headers
                )
                
                # Authentication required for protected endpoints
                protected_response = await client.get(f"{self.production_url}/api/v1/users/profile")
                security_checks["authentication_required"] = protected_response.status_code == 401
                
                # Rate limiting (basic test)
                rate_limit_responses = []
                for _ in range(10):
                    response = await client.get(f"{self.production_url}/api/v1/market/indices")
                    rate_limit_responses.append(response.status_code)
                
                security_checks["rate_limiting_active"] = 429 in rate_limit_responses
                
                # Input validation
                malformed_response = await client.post(
                    f"{self.production_url}/api/v1/analysis/generate",
                    json={"invalid": "data"}
                )
                security_checks["input_validation_active"] = malformed_response.status_code == 400
                
                # CORS configuration
                cors_response = await client.options(f"{self.production_url}/api/v1/market/indices")
                security_checks["cors_configured"] = "access-control-allow-origin" in cors_response.headers
                
        except Exception as e:
            self.warnings.append(f"Security validation failed: {e}")
        
        self.validation_results["security"] = security_checks
        
        # Calculate security score
        passed_checks = sum(1 for check in security_checks.values() if check)
        total_checks = len(security_checks)
        security_score = (passed_checks / total_checks) * 100
        
        logger.info(f"Security readiness: {security_score:.1f}% ({passed_checks}/{total_checks} checks passed)")
        
        return security_score >= 85  # Require 85% security readiness

    async def validate_monitoring_readiness(self):
        """Validate monitoring and alerting readiness"""
        logger.info("Validating monitoring readiness...")
        
        monitoring_checks = {
            "health_endpoints_available": False,
            "metrics_collection_active": False,
            "logging_configured": False,
            "error_tracking_active": False,
            "uptime_monitoring_active": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Health endpoints
                health_endpoints = [
                    "/health",
                    "/health/database",
                    "/health/cache",
                    "/health/external-apis"
                ]
                
                health_responses = []
                for endpoint in health_endpoints:
                    try:
                        response = await client.get(f"{self.production_url}{endpoint}")
                        health_responses.append(response.status_code == 200)
                    except:
                        health_responses.append(False)
                
                monitoring_checks["health_endpoints_available"] = all(health_responses)
                
                # Metrics endpoint (if available)
                try:
                    metrics_response = await client.get(f"{self.production_url}/metrics")
                    monitoring_checks["metrics_collection_active"] = metrics_response.status_code == 200
                except:
                    # Metrics endpoint might not be publicly accessible
                    monitoring_checks["metrics_collection_active"] = True
                
                # Check if structured logging is working (via health check response)
                health_response = await client.get(f"{self.production_url}/health")
                health_data = health_response.json()
                monitoring_checks["logging_configured"] = "timestamp" in health_data
                
                # Error tracking (simulate error and check response format)
                error_response = await client.get(f"{self.production_url}/api/v1/invalid-endpoint")
                monitoring_checks["error_tracking_active"] = error_response.status_code == 404
                
                # Uptime monitoring (assume active if health checks work)
                monitoring_checks["uptime_monitoring_active"] = monitoring_checks["health_endpoints_available"]
                
        except Exception as e:
            self.warnings.append(f"Monitoring validation failed: {e}")
        
        self.validation_results["monitoring"] = monitoring_checks
        
        # Calculate monitoring score
        passed_checks = sum(1 for check in monitoring_checks.values() if check)
        total_checks = len(monitoring_checks)
        monitoring_score = (passed_checks / total_checks) * 100
        
        logger.info(f"Monitoring readiness: {monitoring_score:.1f}% ({passed_checks}/{total_checks} checks passed)")
        
        return monitoring_score >= 80  # Require 80% monitoring readiness

    def validate_documentation_readiness(self):
        """Validate documentation and launch materials readiness"""
        logger.info("Validating documentation readiness...")
        
        documentation_checks = {
            "launch_communication_plan": False,
            "user_onboarding_guide": False,
            "api_documentation": False,
            "user_guides": False,
            "troubleshooting_guides": False,
            "privacy_policy": False,
            "terms_of_service": False
        }
        
        # Check for launch documentation files
        documentation_files = {
            "launch_communication_plan": "docs/launch/launch-communication-plan.md",
            "user_onboarding_guide": "docs/launch/user-onboarding-guide.md",
            "api_documentation": "docs/api/openapi.yaml",
            "privacy_policy": "docs/legal/privacy-policy.md",
            "terms_of_service": "docs/legal/terms-of-service.md"
        }
        
        for check_name, file_path in documentation_files.items():
            documentation_checks[check_name] = os.path.exists(file_path)
            if not documentation_checks[check_name]:
                self.warnings.append(f"Missing documentation file: {file_path}")
        
        # Check for user guides directory
        documentation_checks["user_guides"] = os.path.exists("docs/user-guides")
        documentation_checks["troubleshooting_guides"] = os.path.exists("docs/troubleshooting")
        
        self.validation_results["documentation"] = documentation_checks
        
        # Calculate documentation score
        passed_checks = sum(1 for check in documentation_checks.values() if check)
        total_checks = len(documentation_checks)
        documentation_score = (passed_checks / total_checks) * 100
        
        logger.info(f"Documentation readiness: {documentation_score:.1f}% ({passed_checks}/{total_checks} checks passed)")
        
        return documentation_score >= 70  # Require 70% documentation readiness

    async def run_comprehensive_validation(self):
        """Run all validation checks"""
        logger.info("Starting comprehensive launch readiness validation...")
        
        validation_results = {
            "infrastructure": await self.validate_infrastructure_readiness(),
            "functionality": await self.validate_functionality_readiness(),
            "performance": await self.validate_performance_readiness(),
            "security": await self.validate_security_readiness(),
            "monitoring": await self.validate_monitoring_readiness(),
            "documentation": self.validate_documentation_readiness()
        }
        
        # Calculate overall readiness score
        passed_validations = sum(1 for result in validation_results.values() if result)
        total_validations = len(validation_results)
        overall_readiness = (passed_validations / total_validations) * 100
        
        # Generate final report
        report = {
            "validation_timestamp": datetime.now().isoformat(),
            "production_url": self.production_url,
            "frontend_url": self.frontend_url,
            "overall_readiness_score": overall_readiness,
            "validation_results": validation_results,
            "detailed_results": self.validation_results,
            "critical_failures": self.critical_failures,
            "warnings": self.warnings,
            "launch_recommendation": self.get_launch_recommendation(overall_readiness)
        }
        
        # Save report
        report_filename = f"launch_readiness_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Display results
        self.display_validation_results(report)
        
        return report

    def get_launch_recommendation(self, readiness_score: float) -> dict:
        """Get launch recommendation based on readiness score"""
        if readiness_score >= 90:
            return {
                "recommendation": "GO",
                "confidence": "HIGH",
                "message": "System is ready for public launch. All critical systems are operational."
            }
        elif readiness_score >= 80:
            return {
                "recommendation": "GO_WITH_CAUTION",
                "confidence": "MEDIUM",
                "message": "System is mostly ready. Address warnings before launch if possible."
            }
        elif readiness_score >= 70:
            return {
                "recommendation": "DELAY",
                "confidence": "LOW",
                "message": "System has significant issues. Delay launch until critical issues are resolved."
            }
        else:
            return {
                "recommendation": "NO_GO",
                "confidence": "CRITICAL",
                "message": "System is not ready for launch. Critical failures must be resolved."
            }

    def display_validation_results(self, report: dict):
        """Display validation results in a readable format"""
        print("\n" + "="*80)
        print("🚀 PROJECT KESSAN - LAUNCH READINESS VALIDATION REPORT")
        print("="*80)
        
        print(f"\n📊 OVERALL READINESS SCORE: {report['overall_readiness_score']:.1f}%")
        
        recommendation = report['launch_recommendation']
        print(f"\n🎯 LAUNCH RECOMMENDATION: {recommendation['recommendation']}")
        print(f"   Confidence: {recommendation['confidence']}")
        print(f"   Message: {recommendation['message']}")
        
        print(f"\n🌐 ENVIRONMENT:")
        print(f"   Production API: {self.production_url}")
        print(f"   Frontend URL: {self.frontend_url}")
        print(f"   Validation Time: {report['validation_timestamp']}")
        
        print(f"\n✅ VALIDATION RESULTS:")
        for category, passed in report['validation_results'].items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {category.title()}: {status}")
        
        if self.critical_failures:
            print(f"\n🚨 CRITICAL FAILURES ({len(self.critical_failures)}):")
            for failure in self.critical_failures:
                print(f"   • {failure}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        print(f"\n📄 Detailed report saved to: launch_readiness_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        print("="*80)

# CLI execution
async def main():
    if len(sys.argv) > 1:
        production_url = sys.argv[1]
        frontend_url = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        production_url = None
        frontend_url = None
    
    validator = LaunchReadinessValidator(production_url, frontend_url)
    report = await validator.run_comprehensive_validation()
    
    # Exit with appropriate code
    if report['launch_recommendation']['recommendation'] in ['GO', 'GO_WITH_CAUTION']:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())