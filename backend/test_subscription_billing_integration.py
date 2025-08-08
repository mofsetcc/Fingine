#!/usr/bin/env python3
"""
Subscription and Billing Integration Testing
Tests complete subscription flows, billing integration, and payment processing
"""

import asyncio
import pytest
import httpx
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import stripe

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SubscriptionBillingTestSuite:
    """Comprehensive subscription and billing testing"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("PRODUCTION_API_URL", "https://api.kessan.app")
        self.stripe_test_key = os.getenv("STRIPE_TEST_SECRET_KEY")
        self.test_results = []
        
        # Initialize Stripe with test key
        if self.stripe_test_key:
            stripe.api_key = self.stripe_test_key
        
    async def test_subscription_plan_management(self):
        """Test subscription plan creation and management"""
        test_name = "Subscription Plan Management"
        logger.info(f"Starting {test_name}...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test 1: Get available plans
                logger.info("Testing plan retrieval...")
                plans_response = await client.get(f"{self.base_url}/api/v1/subscription/plans")
                
                assert plans_response.status_code == 200, "Plans retrieval failed"
                plans_data = plans_response.json()
                
                assert "plans" in plans_data, "Plans data structure invalid"
                plans = plans_data["plans"]
                assert len(plans) >= 3, "Should have at least 3 plans (Free, Pro, Business)"
                
                # Verify plan structure
                required_fields = ["id", "plan_name", "price_monthly", "features", "api_quota_daily"]
                for plan in plans:
                    for field in required_fields:
                        assert field in plan, f"Plan missing required field: {field}"
                
                # Test 2: Verify plan pricing and features
                free_plan = next((p for p in plans if p["plan_name"] == "free"), None)
                pro_plan = next((p for p in plans if p["plan_name"] == "pro"), None)
                business_plan = next((p for p in plans if p["plan_name"] == "business"), None)
                
                assert free_plan is not None, "Free plan not found"
                assert pro_plan is not None, "Pro plan not found"
                assert business_plan is not None, "Business plan not found"
                
                # Verify pricing progression
                assert free_plan["price_monthly"] == 0, "Free plan should be 0 yen"
                assert pro_plan["price_monthly"] > free_plan["price_monthly"], "Pro plan should cost more than free"
                assert business_plan["price_monthly"] > pro_plan["price_monthly"], "Business plan should cost more than pro"
                
                # Verify quota progression
                assert pro_plan["api_quota_daily"] > free_plan["api_quota_daily"], "Pro should have higher quota"
                assert business_plan["api_quota_daily"] > pro_plan["api_quota_daily"], "Business should have highest quota"
                
                self.test_results.append({
                    "test_name": test_name,
                    "status": "PASSED",
                    "details": "Plan management tests successful"
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

    async def test_subscription_upgrade_flow(self):
        """Test complete subscription upgrade flow with payment processing"""
        test_name = "Subscription Upgrade Flow"
        logger.info(f"Starting {test_name}...")
        
        # Create test user
        test_user = await self._create_test_user("subscription_upgrade_test")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Login user
                token = await self._login_user(client, test_user)
                headers = {"Authorization": f"Bearer {token}"}
                
                # Step 1: Verify initial free subscription
                logger.info("Step 1: Verifying initial free subscription...")
                subscription_response = await client.get(
                    f"{self.base_url}/api/v1/users/subscription",
                    headers=headers
                )
                
                assert subscription_response.status_code == 200, "Subscription check failed"
                current_sub = subscription_response.json()
                assert current_sub["plan_name"] == "free", "User should start with free plan"
                assert current_sub["status"] == "active", "Free subscription should be active"
                
                # Step 2: Get Pro plan details
                logger.info("Step 2: Getting Pro plan details...")
                plans_response = await client.get(f"{self.base_url}/api/v1/subscription/plans")
                plans = plans_response.json()["plans"]
                pro_plan = next((p for p in plans if p["plan_name"] == "pro"), None)
                
                # Step 3: Create payment method (test card)
                logger.info("Step 3: Creating test payment method...")
                payment_method_response = await client.post(
                    f"{self.base_url}/api/v1/subscription/payment-methods",
                    json={
                        "type": "card",
                        "card": {
                            "number": "4242424242424242",  # Stripe test card
                            "exp_month": 12,
                            "exp_year": 2025,
                            "cvc": "123"
                        },
                        "billing_details": {
                            "name": "Test User",
                            "email": test_user["email"]
                        }
                    },
                    headers=headers
                )
                
                assert payment_method_response.status_code == 200, "Payment method creation failed"
                payment_method = payment_method_response.json()
                
                # Step 4: Initiate subscription upgrade
                logger.info("Step 4: Initiating subscription upgrade...")
                upgrade_response = await client.post(
                    f"{self.base_url}/api/v1/subscription/upgrade",
                    json={
                        "plan_id": pro_plan["id"],
                        "payment_method_id": payment_method["id"]
                    },
                    headers=headers
                )
                
                assert upgrade_response.status_code == 200, f"Subscription upgrade failed: {upgrade_response.text}"
                upgrade_data = upgrade_response.json()
                
                # Step 5: Verify subscription upgrade
                logger.info("Step 5: Verifying subscription upgrade...")
                updated_sub_response = await client.get(
                    f"{self.base_url}/api/v1/users/subscription",
                    headers=headers
                )
                
                updated_sub = updated_sub_response.json()
                assert updated_sub["plan_name"] == "pro", "Subscription upgrade not reflected"
                assert updated_sub["status"] == "active", "Upgraded subscription should be active"
                assert updated_sub["api_quota_daily"] == pro_plan["api_quota_daily"], "Pro quotas not applied"
                
                # Step 6: Verify billing record
                logger.info("Step 6: Verifying billing record...")
                billing_response = await client.get(
                    f"{self.base_url}/api/v1/subscription/billing-history",
                    headers=headers
                )
                
                assert billing_response.status_code == 200, "Billing history retrieval failed"
                billing_history = billing_response.json()
                assert len(billing_history["invoices"]) > 0, "No billing records found"
                
                latest_invoice = billing_history["invoices"][0]
                assert latest_invoice["amount"] == pro_plan["price_monthly"], "Invoice amount incorrect"
                assert latest_invoice["status"] == "paid", "Invoice should be paid"
                
                self.test_results.append({
                    "test_name": test_name,
                    "status": "PASSED",
                    "details": "Subscription upgrade flow successful",
                    "user_email": test_user["email"]
                })
                
                logger.info(f"{test_name} - PASSED")
                
        except Exception as e:
            self.test_results.append({
                "test_name": test_name,
                "status": "FAILED",
                "error": str(e),
                "user_email": test_user["email"]
            })
            logger.error(f"{test_name} - FAILED: {e}")
            raise

    async def test_subscription_downgrade_flow(self):
        """Test subscription downgrade and prorated billing"""
        test_name = "Subscription Downgrade Flow"
        logger.info(f"Starting {test_name}...")
        
        # Create test user with Pro subscription
        test_user = await self._create_test_user("subscription_downgrade_test")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                token = await self._login_user(client, test_user)
                headers = {"Authorization": f"Bearer {token}"}
                
                # Setup: Upgrade to Pro first
                await self._upgrade_user_to_pro(client, headers)
                
                # Step 1: Verify Pro subscription
                logger.info("Step 1: Verifying Pro subscription...")
                subscription_response = await client.get(
                    f"{self.base_url}/api/v1/users/subscription",
                    headers=headers
                )
                
                current_sub = subscription_response.json()
                assert current_sub["plan_name"] == "pro", "User should have Pro subscription"
                
                # Step 2: Initiate downgrade to Free
                logger.info("Step 2: Initiating downgrade to Free...")
                plans_response = await client.get(f"{self.base_url}/api/v1/subscription/plans")
                plans = plans_response.json()["plans"]
                free_plan = next((p for p in plans if p["plan_name"] == "free"), None)
                
                downgrade_response = await client.post(
                    f"{self.base_url}/api/v1/subscription/downgrade",
                    json={
                        "plan_id": free_plan["id"],
                        "effective_date": "end_of_period"  # Downgrade at end of billing period
                    },
                    headers=headers
                )
                
                assert downgrade_response.status_code == 200, "Subscription downgrade failed"
                downgrade_data = downgrade_response.json()
                
                # Step 3: Verify downgrade scheduling
                logger.info("Step 3: Verifying downgrade scheduling...")
                updated_sub_response = await client.get(
                    f"{self.base_url}/api/v1/users/subscription",
                    headers=headers
                )
                
                updated_sub = updated_sub_response.json()
                assert updated_sub["plan_name"] == "pro", "Should still be Pro until period end"
                assert "scheduled_downgrade" in updated_sub, "Downgrade should be scheduled"
                assert updated_sub["scheduled_downgrade"]["target_plan"] == "free", "Should downgrade to free"
                
                # Step 4: Test immediate downgrade
                logger.info("Step 4: Testing immediate downgrade...")
                immediate_downgrade_response = await client.post(
                    f"{self.base_url}/api/v1/subscription/downgrade",
                    json={
                        "plan_id": free_plan["id"],
                        "effective_date": "immediate"
                    },
                    headers=headers
                )
                
                assert immediate_downgrade_response.status_code == 200, "Immediate downgrade failed"
                
                # Verify immediate downgrade
                final_sub_response = await client.get(
                    f"{self.base_url}/api/v1/users/subscription",
                    headers=headers
                )
                
                final_sub = final_sub_response.json()
                assert final_sub["plan_name"] == "free", "Should be downgraded to free immediately"
                assert final_sub["api_quota_daily"] == free_plan["api_quota_daily"], "Free quotas should be applied"
                
                self.test_results.append({
                    "test_name": test_name,
                    "status": "PASSED",
                    "details": "Subscription downgrade flow successful",
                    "user_email": test_user["email"]
                })
                
                logger.info(f"{test_name} - PASSED")
                
        except Exception as e:
            self.test_results.append({
                "test_name": test_name,
                "status": "FAILED",
                "error": str(e),
                "user_email": test_user["email"]
            })
            logger.error(f"{test_name} - FAILED: {e}")
            raise

    async def test_payment_failure_handling(self):
        """Test payment failure scenarios and retry logic"""
        test_name = "Payment Failure Handling"
        logger.info(f"Starting {test_name}...")
        
        test_user = await self._create_test_user("payment_failure_test")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                token = await self._login_user(client, test_user)
                headers = {"Authorization": f"Bearer {token}"}
                
                # Step 1: Attempt upgrade with declined card
                logger.info("Step 1: Testing payment decline handling...")
                plans_response = await client.get(f"{self.base_url}/api/v1/subscription/plans")
                plans = plans_response.json()["plans"]
                pro_plan = next((p for p in plans if p["plan_name"] == "pro"), None)
                
                # Create payment method with declined test card
                declined_payment_response = await client.post(
                    f"{self.base_url}/api/v1/subscription/payment-methods",
                    json={
                        "type": "card",
                        "card": {
                            "number": "4000000000000002",  # Stripe declined test card
                            "exp_month": 12,
                            "exp_year": 2025,
                            "cvc": "123"
                        },
                        "billing_details": {
                            "name": "Test User",
                            "email": test_user["email"]
                        }
                    },
                    headers=headers
                )
                
                declined_payment_method = declined_payment_response.json()
                
                # Attempt upgrade with declined card
                upgrade_response = await client.post(
                    f"{self.base_url}/api/v1/subscription/upgrade",
                    json={
                        "plan_id": pro_plan["id"],
                        "payment_method_id": declined_payment_method["id"]
                    },
                    headers=headers
                )
                
                # Should return payment error
                assert upgrade_response.status_code == 400, "Should return payment error"
                error_data = upgrade_response.json()
                assert "payment_failed" in error_data["error"].lower(), "Should indicate payment failure"
                
                # Step 2: Verify subscription remains unchanged
                logger.info("Step 2: Verifying subscription unchanged after payment failure...")
                subscription_response = await client.get(
                    f"{self.base_url}/api/v1/users/subscription",
                    headers=headers
                )
                
                current_sub = subscription_response.json()
                assert current_sub["plan_name"] == "free", "Should remain on free plan after payment failure"
                
                # Step 3: Test successful retry with valid card
                logger.info("Step 3: Testing successful payment retry...")
                valid_payment_response = await client.post(
                    f"{self.base_url}/api/v1/subscription/payment-methods",
                    json={
                        "type": "card",
                        "card": {
                            "number": "4242424242424242",  # Valid test card
                            "exp_month": 12,
                            "exp_year": 2025,
                            "cvc": "123"
                        },
                        "billing_details": {
                            "name": "Test User",
                            "email": test_user["email"]
                        }
                    },
                    headers=headers
                )
                
                valid_payment_method = valid_payment_response.json()
                
                # Retry upgrade with valid card
                retry_upgrade_response = await client.post(
                    f"{self.base_url}/api/v1/subscription/upgrade",
                    json={
                        "plan_id": pro_plan["id"],
                        "payment_method_id": valid_payment_method["id"]
                    },
                    headers=headers
                )
                
                assert retry_upgrade_response.status_code == 200, "Retry upgrade should succeed"
                
                # Verify successful upgrade
                final_sub_response = await client.get(
                    f"{self.base_url}/api/v1/users/subscription",
                    headers=headers
                )
                
                final_sub = final_sub_response.json()
                assert final_sub["plan_name"] == "pro", "Should be upgraded to pro after successful payment"
                
                self.test_results.append({
                    "test_name": test_name,
                    "status": "PASSED",
                    "details": "Payment failure handling successful",
                    "user_email": test_user["email"]
                })
                
                logger.info(f"{test_name} - PASSED")
                
        except Exception as e:
            self.test_results.append({
                "test_name": test_name,
                "status": "FAILED",
                "error": str(e),
                "user_email": test_user["email"]
            })
            logger.error(f"{test_name} - FAILED: {e}")
            raise

    async def test_billing_history_and_invoices(self):
        """Test billing history, invoice generation, and tax handling"""
        test_name = "Billing History and Invoices"
        logger.info(f"Starting {test_name}...")
        
        test_user = await self._create_test_user("billing_history_test")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                token = await self._login_user(client, test_user)
                headers = {"Authorization": f"Bearer {token}"}
                
                # Setup: Upgrade to Pro to generate billing history
                await self._upgrade_user_to_pro(client, headers)
                
                # Step 1: Retrieve billing history
                logger.info("Step 1: Testing billing history retrieval...")
                billing_response = await client.get(
                    f"{self.base_url}/api/v1/subscription/billing-history",
                    headers=headers
                )
                
                assert billing_response.status_code == 200, "Billing history retrieval failed"
                billing_data = billing_response.json()
                
                assert "invoices" in billing_data, "Billing data should contain invoices"
                assert len(billing_data["invoices"]) > 0, "Should have at least one invoice"
                
                # Step 2: Verify invoice structure
                logger.info("Step 2: Verifying invoice structure...")
                latest_invoice = billing_data["invoices"][0]
                
                required_invoice_fields = [
                    "id", "amount", "currency", "status", "created_at",
                    "period_start", "period_end", "description"
                ]
                
                for field in required_invoice_fields:
                    assert field in latest_invoice, f"Invoice missing required field: {field}"
                
                assert latest_invoice["currency"] == "jpy", "Currency should be JPY"
                assert latest_invoice["status"] == "paid", "Invoice should be paid"
                
                # Step 3: Test invoice download
                logger.info("Step 3: Testing invoice download...")
                invoice_download_response = await client.get(
                    f"{self.base_url}/api/v1/subscription/invoices/{latest_invoice['id']}/download",
                    headers=headers
                )
                
                assert invoice_download_response.status_code == 200, "Invoice download failed"
                assert invoice_download_response.headers.get("content-type") == "application/pdf", "Invoice should be PDF"
                
                # Step 4: Test usage-based billing (if applicable)
                logger.info("Step 4: Testing usage tracking...")
                usage_response = await client.get(
                    f"{self.base_url}/api/v1/subscription/usage",
                    headers=headers
                )
                
                assert usage_response.status_code == 200, "Usage retrieval failed"
                usage_data = usage_response.json()
                
                assert "current_period" in usage_data, "Usage data should include current period"
                assert "api_calls" in usage_data["current_period"], "Should track API calls"
                assert "ai_analysis" in usage_data["current_period"], "Should track AI analysis usage"
                
                self.test_results.append({
                    "test_name": test_name,
                    "status": "PASSED",
                    "details": "Billing history and invoices test successful",
                    "user_email": test_user["email"]
                })
                
                logger.info(f"{test_name} - PASSED")
                
        except Exception as e:
            self.test_results.append({
                "test_name": test_name,
                "status": "FAILED",
                "error": str(e),
                "user_email": test_user["email"]
            })
            logger.error(f"{test_name} - FAILED: {e}")
            raise

    # Helper methods
    async def _create_test_user(self, scenario: str) -> dict:
        """Create a test user for billing tests"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return {
            "email": f"billing_test_{scenario}_{timestamp}@test.kessan.app",
            "password": "TestUser123!",
            "scenario": scenario
        }

    async def _login_user(self, client: httpx.AsyncClient, user: dict) -> str:
        """Register and login a user, return access token"""
        # Register
        register_response = await client.post(
            f"{self.base_url}/api/v1/auth/register",
            json={
                "email": user["email"],
                "password": user["password"],
                "display_name": f"Billing Test User {user['scenario']}"
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
        return login_response.json()["access_token"]

    async def _upgrade_user_to_pro(self, client: httpx.AsyncClient, headers: dict):
        """Helper to upgrade user to Pro plan"""
        # Get Pro plan
        plans_response = await client.get(f"{self.base_url}/api/v1/subscription/plans")
        plans = plans_response.json()["plans"]
        pro_plan = next((p for p in plans if p["plan_name"] == "pro"), None)
        
        # Create payment method
        payment_method_response = await client.post(
            f"{self.base_url}/api/v1/subscription/payment-methods",
            json={
                "type": "card",
                "card": {
                    "number": "4242424242424242",
                    "exp_month": 12,
                    "exp_year": 2025,
                    "cvc": "123"
                },
                "billing_details": {
                    "name": "Test User"
                }
            },
            headers=headers
        )
        payment_method = payment_method_response.json()
        
        # Upgrade
        upgrade_response = await client.post(
            f"{self.base_url}/api/v1/subscription/upgrade",
            json={
                "plan_id": pro_plan["id"],
                "payment_method_id": payment_method["id"]
            },
            headers=headers
        )
        assert upgrade_response.status_code == 200, "Pro upgrade failed"

    async def run_all_tests(self):
        """Run all subscription and billing tests"""
        logger.info("Starting Subscription and Billing Integration Testing...")
        
        test_methods = [
            self.test_subscription_plan_management,
            self.test_subscription_upgrade_flow,
            self.test_subscription_downgrade_flow,
            self.test_payment_failure_handling,
            self.test_billing_history_and_invoices
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
            "test_suite": "Subscription and Billing Integration Testing",
            "execution_time": datetime.now().isoformat(),
            "environment": "production",
            "total_tests": len(self.test_results),
            "passed_tests": len([r for r in self.test_results if r["status"] == "PASSED"]),
            "failed_tests": len([r for r in self.test_results if r["status"] == "FAILED"]),
            "test_results": self.test_results
        }
        
        # Save report
        report_filename = f"subscription_billing_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Test report saved to {report_filename}")
        logger.info(f"Billing Tests Results: {report['passed_tests']}/{report['total_tests']} tests passed")
        
        return report

# CLI execution
if __name__ == "__main__":
    import sys
    
    base_url = sys.argv[1] if len(sys.argv) > 1 else None
    
    async def main():
        billing_suite = SubscriptionBillingTestSuite(base_url)
        await billing_suite.run_all_tests()
    
    asyncio.run(main())