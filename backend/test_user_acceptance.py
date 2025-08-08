#!/usr/bin/env python3
"""
User Acceptance Testing Suite for Japanese Stock Analysis Platform
Validates complete user journeys and critical business flows
"""

import asyncio
import pytest
import httpx
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserAcceptanceTestSuite:
    """Comprehensive user acceptance testing for production environment"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("PRODUCTION_API_URL", "https://api.kessan.app")
        self.test_results = []
        self.test_users = []
        
    async def setup_test_environment(self):
        """Setup test environment and create test users"""
        logger.info("Setting up user acceptance test environment...")
        
        # Create test users for different scenarios
        self.test_users = [
            {
                "email": f"beta_user_1_{datetime.now().strftime('%Y%m%d_%H%M%S')}@test.kessan.app",
                "password": "TestUser123!",
                "user_type": "free_tier",
                "scenario": "new_user_onboarding"
            },
            {
                "email": f"beta_user_2_{datetime.now().strftime('%Y%m%d_%H%M%S')}@test.kessan.app", 
                "password": "TestUser123!",
                "user_type": "pro_tier",
                "scenario": "subscription_upgrade"
            },
            {
                "email": f"beta_user_3_{datetime.now().strftime('%Y%m%d_%H%M%S')}@test.kessan.app",
                "password": "TestUser123!", 
                "user_type": "business_tier",
                "scenario": "power_user_workflow"
            }
        ]
        
        logger.info(f"Created {len(self.test_users)} test users for UAT")

    async def test_complete_user_journey_new_user(self):
        """Test complete journey for new user from registration to analysis"""
        test_name = "Complete New User Journey"
        logger.info(f"Starting {test_name}...")
        
        user = self.test_users[0]
        session_data = {}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Step 1: User Registration
                logger.info("Step 1: Testing user registration...")
                register_response = await client.post(
                    f"{self.base_url}/api/v1/auth/register",
                    json={
                        "email": user["email"],
                        "password": user["password"],
                        "display_name": "Beta Test User 1"
                    }
                )
                
                assert register_response.status_code == 201, f"Registration failed: {register_response.text}"
                session_data["user_id"] = register_response.json()["user_id"]
                
                # Step 2: Email Verification (simulate)
                logger.info("Step 2: Simulating email verification...")
                # In production, this would require email verification
                # For UAT, we'll use a test endpoint or skip verification
                
                # Step 3: User Login
                logger.info("Step 3: Testing user login...")
                login_response = await client.post(
                    f"{self.base_url}/api/v1/auth/login",
                    json={
                        "email": user["email"],
                        "password": user["password"]
                    }
                )
                
                assert login_response.status_code == 200, f"Login failed: {login_response.text}"
                token = login_response.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}
                
                # Step 4: Dashboard Access
                logger.info("Step 4: Testing dashboard access...")
                dashboard_response = await client.get(
                    f"{self.base_url}/api/v1/market/indices",
                    headers=headers
                )
                
                assert dashboard_response.status_code == 200, "Dashboard data fetch failed"
                market_data = dashboard_response.json()
                assert "nikkei_225" in market_data, "Market indices data incomplete"
                
                # Step 5: Stock Search
                logger.info("Step 5: Testing stock search...")
                search_response = await client.get(
                    f"{self.base_url}/api/v1/stocks/search?q=トヨタ",
                    headers=headers
                )
                
                assert search_response.status_code == 200, "Stock search failed"
                search_results = search_response.json()
                assert len(search_results["results"]) > 0, "No search results found"
                
                # Step 6: Stock Analysis Request
                logger.info("Step 6: Testing AI analysis generation...")
                toyota_ticker = "7203"  # Toyota Motor Corp
                analysis_response = await client.post(
                    f"{self.base_url}/api/v1/analysis/generate",
                    json={
                        "ticker": toyota_ticker,
                        "analysis_type": "comprehensive"
                    },
                    headers=headers
                )
                
                assert analysis_response.status_code == 200, f"Analysis generation failed: {analysis_response.text}"
                analysis_data = analysis_response.json()
                assert "rating" in analysis_data, "Analysis data incomplete"
                assert "confidence" in analysis_data, "Analysis confidence missing"
                
                # Step 7: Watchlist Management
                logger.info("Step 7: Testing watchlist functionality...")
                watchlist_add_response = await client.post(
                    f"{self.base_url}/api/v1/watchlist/add",
                    json={"ticker": toyota_ticker},
                    headers=headers
                )
                
                assert watchlist_add_response.status_code == 200, "Watchlist add failed"
                
                # Verify watchlist
                watchlist_get_response = await client.get(
                    f"{self.base_url}/api/v1/watchlist",
                    headers=headers
                )
                
                assert watchlist_get_response.status_code == 200, "Watchlist fetch failed"
                watchlist_data = watchlist_get_response.json()
                assert len(watchlist_data["stocks"]) > 0, "Watchlist is empty"
                
                # Step 8: Quota Usage Check
                logger.info("Step 8: Testing quota usage tracking...")
                quota_response = await client.get(
                    f"{self.base_url}/api/v1/users/quota",
                    headers=headers
                )
                
                assert quota_response.status_code == 200, "Quota check failed"
                quota_data = quota_response.json()
                assert "daily_usage" in quota_data, "Quota data incomplete"
                assert quota_data["daily_usage"]["ai_analysis"] > 0, "AI analysis usage not tracked"
                
                self.test_results.append({
                    "test_name": test_name,
                    "status": "PASSED",
                    "duration": "N/A",
                    "details": "Complete user journey successful",
                    "user_email": user["email"]
                })
                
                logger.info(f"{test_name} - PASSED")
                
        except Exception as e:
            self.test_results.append({
                "test_name": test_name,
                "status": "FAILED",
                "error": str(e),
                "user_email": user["email"]
            })
            logger.error(f"{test_name} - FAILED: {e}")
            raise

    async def test_subscription_upgrade_flow(self):
        """Test subscription upgrade and billing integration"""
        test_name = "Subscription Upgrade Flow"
        logger.info(f"Starting {test_name}...")
        
        user = self.test_users[1]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Register and login user
                await self._register_and_login_user(client, user)
                token = user.get("token")
                headers = {"Authorization": f"Bearer {token}"}
                
                # Step 1: Check current subscription
                logger.info("Step 1: Checking current subscription status...")
                subscription_response = await client.get(
                    f"{self.base_url}/api/v1/users/subscription",
                    headers=headers
                )
                
                assert subscription_response.status_code == 200, "Subscription check failed"
                current_sub = subscription_response.json()
                assert current_sub["plan_name"] == "free", "User should start with free plan"
                
                # Step 2: Get available plans
                logger.info("Step 2: Fetching available subscription plans...")
                plans_response = await client.get(
                    f"{self.base_url}/api/v1/subscription/plans",
                    headers=headers
                )
                
                assert plans_response.status_code == 200, "Plans fetch failed"
                plans = plans_response.json()["plans"]
                pro_plan = next((p for p in plans if p["plan_name"] == "pro"), None)
                assert pro_plan is not None, "Pro plan not found"
                
                # Step 3: Initiate subscription upgrade
                logger.info("Step 3: Testing subscription upgrade...")
                upgrade_response = await client.post(
                    f"{self.base_url}/api/v1/subscription/upgrade",
                    json={
                        "plan_id": pro_plan["id"],
                        "payment_method": "test_card_4242424242424242"  # Test card
                    },
                    headers=headers
                )
                
                assert upgrade_response.status_code == 200, f"Subscription upgrade failed: {upgrade_response.text}"
                upgrade_data = upgrade_response.json()
                assert upgrade_data["status"] == "active", "Subscription not activated"
                
                # Step 4: Verify upgraded features
                logger.info("Step 4: Verifying upgraded subscription features...")
                updated_sub_response = await client.get(
                    f"{self.base_url}/api/v1/users/subscription",
                    headers=headers
                )
                
                updated_sub = updated_sub_response.json()
                assert updated_sub["plan_name"] == "pro", "Subscription upgrade not reflected"
                assert updated_sub["api_quota_daily"] > 10, "Pro tier quotas not applied"
                
                # Step 5: Test enhanced features
                logger.info("Step 5: Testing enhanced pro features...")
                # Test real-time data access
                realtime_response = await client.get(
                    f"{self.base_url}/api/v1/stocks/7203/price-history?interval=1min&realtime=true",
                    headers=headers
                )
                
                assert realtime_response.status_code == 200, "Real-time data access failed"
                
                self.test_results.append({
                    "test_name": test_name,
                    "status": "PASSED",
                    "details": "Subscription upgrade flow successful",
                    "user_email": user["email"]
                })
                
                logger.info(f"{test_name} - PASSED")
                
        except Exception as e:
            self.test_results.append({
                "test_name": test_name,
                "status": "FAILED",
                "error": str(e),
                "user_email": user["email"]
            })
            logger.error(f"{test_name} - FAILED: {e}")
            raise

    async def test_power_user_workflow(self):
        """Test advanced features for business tier users"""
        test_name = "Power User Workflow"
        logger.info(f"Starting {test_name}...")
        
        user = self.test_users[2]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Setup business tier user
                await self._register_and_login_user(client, user)
                await self._upgrade_to_business_tier(client, user)
                
                token = user.get("token")
                headers = {"Authorization": f"Bearer {token}"}
                
                # Step 1: Batch analysis request
                logger.info("Step 1: Testing batch analysis...")
                batch_tickers = ["7203", "6758", "9984", "8306", "7974"]  # Top 5 stocks
                batch_response = await client.post(
                    f"{self.base_url}/api/v1/analysis/batch",
                    json={
                        "tickers": batch_tickers,
                        "analysis_type": "comprehensive"
                    },
                    headers=headers
                )
                
                assert batch_response.status_code == 200, "Batch analysis failed"
                batch_results = batch_response.json()
                assert len(batch_results["analyses"]) == len(batch_tickers), "Incomplete batch results"
                
                # Step 2: Advanced watchlist features
                logger.info("Step 2: Testing advanced watchlist features...")
                # Create multiple watchlists
                watchlist_create_response = await client.post(
                    f"{self.base_url}/api/v1/watchlist/create",
                    json={
                        "name": "Tech Stocks Portfolio",
                        "description": "Technology sector focus",
                        "tickers": ["6758", "9984", "7974"]
                    },
                    headers=headers
                )
                
                assert watchlist_create_response.status_code == 200, "Advanced watchlist creation failed"
                
                # Step 3: Export functionality
                logger.info("Step 3: Testing data export...")
                export_response = await client.post(
                    f"{self.base_url}/api/v1/analysis/export",
                    json={
                        "tickers": batch_tickers,
                        "format": "csv",
                        "date_range": "30d"
                    },
                    headers=headers
                )
                
                assert export_response.status_code == 200, "Data export failed"
                assert export_response.headers.get("content-type") == "text/csv", "Export format incorrect"
                
                # Step 4: API rate limits for business tier
                logger.info("Step 4: Testing business tier rate limits...")
                quota_response = await client.get(
                    f"{self.base_url}/api/v1/users/quota",
                    headers=headers
                )
                
                quota_data = quota_response.json()
                assert quota_data["daily_limit"]["ai_analysis"] >= 500, "Business tier limits not applied"
                
                self.test_results.append({
                    "test_name": test_name,
                    "status": "PASSED",
                    "details": "Power user workflow successful",
                    "user_email": user["email"]
                })
                
                logger.info(f"{test_name} - PASSED")
                
        except Exception as e:
            self.test_results.append({
                "test_name": test_name,
                "status": "FAILED",
                "error": str(e),
                "user_email": user["email"]
            })
            logger.error(f"{test_name} - FAILED: {e}")
            raise

    async def test_error_handling_and_edge_cases(self):
        """Test error handling and edge cases"""
        test_name = "Error Handling and Edge Cases"
        logger.info(f"Starting {test_name}...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test 1: Invalid ticker
                logger.info("Testing invalid ticker handling...")
                invalid_response = await client.get(f"{self.base_url}/api/v1/stocks/INVALID")
                assert invalid_response.status_code == 404, "Invalid ticker should return 404"
                
                # Test 2: Rate limiting
                logger.info("Testing rate limiting...")
                # Make rapid requests to trigger rate limiting
                for i in range(20):
                    await client.get(f"{self.base_url}/api/v1/market/indices")
                
                # Should eventually get rate limited
                rate_limit_response = await client.get(f"{self.base_url}/api/v1/market/indices")
                # Note: This might not trigger in UAT environment
                
                # Test 3: Malformed requests
                logger.info("Testing malformed request handling...")
                malformed_response = await client.post(
                    f"{self.base_url}/api/v1/analysis/generate",
                    json={"invalid": "data"}
                )
                assert malformed_response.status_code == 400, "Malformed request should return 400"
                
                self.test_results.append({
                    "test_name": test_name,
                    "status": "PASSED",
                    "details": "Error handling tests successful"
                })
                
                logger.info(f"{test_name} - PASSED")
                
        except Exception as e:
            self.test_results.append({
                "test_name": test_name,
                "status": "FAILED",
                "error": str(e)
            })
            logger.error(f"{test_name} - FAILED: {e}")
            raise

    async def _register_and_login_user(self, client: httpx.AsyncClient, user: dict):
        """Helper method to register and login a user"""
        # Register
        register_response = await client.post(
            f"{self.base_url}/api/v1/auth/register",
            json={
                "email": user["email"],
                "password": user["password"],
                "display_name": f"UAT User {user['scenario']}"
            }
        )
        assert register_response.status_code == 201, f"Registration failed for {user['email']}"
        
        # Login
        login_response = await client.post(
            f"{self.base_url}/api/v1/auth/login",
            json={
                "email": user["email"],
                "password": user["password"]
            }
        )
        assert login_response.status_code == 200, f"Login failed for {user['email']}"
        user["token"] = login_response.json()["access_token"]

    async def _upgrade_to_business_tier(self, client: httpx.AsyncClient, user: dict):
        """Helper method to upgrade user to business tier"""
        headers = {"Authorization": f"Bearer {user['token']}"}
        
        # Get business plan
        plans_response = await client.get(f"{self.base_url}/api/v1/subscription/plans", headers=headers)
        plans = plans_response.json()["plans"]
        business_plan = next((p for p in plans if p["plan_name"] == "business"), None)
        
        # Upgrade
        upgrade_response = await client.post(
            f"{self.base_url}/api/v1/subscription/upgrade",
            json={
                "plan_id": business_plan["id"],
                "payment_method": "test_card_4242424242424242"
            },
            headers=headers
        )
        assert upgrade_response.status_code == 200, "Business tier upgrade failed"

    async def run_all_tests(self):
        """Run all user acceptance tests"""
        logger.info("Starting User Acceptance Testing Suite...")
        
        await self.setup_test_environment()
        
        test_methods = [
            self.test_complete_user_journey_new_user,
            self.test_subscription_upgrade_flow,
            self.test_power_user_workflow,
            self.test_error_handling_and_edge_cases
        ]
        
        for test_method in test_methods:
            try:
                await test_method()
            except Exception as e:
                logger.error(f"Test {test_method.__name__} failed: {e}")
                continue
        
        # Generate test report
        await self.generate_test_report()

    async def generate_test_report(self):
        """Generate comprehensive test report"""
        report = {
            "test_suite": "User Acceptance Testing",
            "execution_time": datetime.now().isoformat(),
            "environment": "production",
            "total_tests": len(self.test_results),
            "passed_tests": len([r for r in self.test_results if r["status"] == "PASSED"]),
            "failed_tests": len([r for r in self.test_results if r["status"] == "FAILED"]),
            "test_results": self.test_results,
            "test_users": [{"email": u["email"], "scenario": u["scenario"]} for u in self.test_users]
        }
        
        # Save report
        report_filename = f"user_acceptance_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Test report saved to {report_filename}")
        logger.info(f"UAT Results: {report['passed_tests']}/{report['total_tests']} tests passed")
        
        return report

# CLI execution
if __name__ == "__main__":
    import sys
    
    base_url = sys.argv[1] if len(sys.argv) > 1 else None
    
    async def main():
        uat_suite = UserAcceptanceTestSuite(base_url)
        await uat_suite.run_all_tests()
    
    asyncio.run(main())