"""
Performance and load testing scenarios for production readiness.
"""

import pytest
import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from httpx import AsyncClient
from fastapi.testclient import TestClient
import psutil
import threading
from unittest.mock import patch

from app.main import app


class TestPerformanceMetrics:
    """Test performance metrics and benchmarks."""
    
    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)
    
    def test_api_response_times(self, client):
        """Test API response times meet performance requirements."""
        endpoints = [
            "/api/v1/health",
            "/api/v1/stocks/search?query=Toyota",
            "/api/v1/stocks/7203",
            "/api/v1/market/indices"
        ]
        
        response_times = {}
        
        for endpoint in endpoints:
            times = []
            
            # Make 10 requests to each endpoint
            for _ in range(10):
                start_time = time.time()
                response = client.get(endpoint)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                times.append(response_time)
                
                # Verify response is successful
                assert response.status_code in [200, 404]  # 404 is acceptable for test data
            
            response_times[endpoint] = {
                'avg': statistics.mean(times),
                'median': statistics.median(times),
                'p95': sorted(times)[int(0.95 * len(times))],
                'max': max(times)
            }
        
        # Performance requirements
        for endpoint, metrics in response_times.items():
            print(f"\n{endpoint}:")
            print(f"  Average: {metrics['avg']:.2f}ms")
            print(f"  Median: {metrics['median']:.2f}ms")
            print(f"  95th percentile: {metrics['p95']:.2f}ms")
            print(f"  Max: {metrics['max']:.2f}ms")
            
            # Assert performance requirements
            if endpoint == "/api/v1/health":
                assert metrics['p95'] < 100  # Health check should be very fast
            elif "search" in endpoint:
                assert metrics['p95'] < 500  # Search should be under 500ms
            else:
                assert metrics['p95'] < 1000  # Other endpoints under 1s
    
    def test_database_query_performance(self, client):
        """Test database query performance."""
        # Test stock search performance
        search_queries = [
            "Toyota",
            "Sony",
            "7203",
            "電気機器",
            "自動車"
        ]
        
        query_times = []
        
        for query in search_queries:
            start_time = time.time()
            response = client.get(f"/api/v1/stocks/search?query={query}")
            end_time = time.time()
            
            query_time = (end_time - start_time) * 1000
            query_times.append(query_time)
            
            # Should return results quickly
            assert response.status_code == 200
        
        avg_query_time = statistics.mean(query_times)
        print(f"\nAverage database query time: {avg_query_time:.2f}ms")
        
        # Database queries should be fast
        assert avg_query_time < 200  # Under 200ms average
        assert max(query_times) < 500  # No query over 500ms
    
    @patch('app.services.ai_analysis_service.AIAnalysisService.generate_analysis')
    def test_ai_analysis_performance(self, mock_ai_analysis, client):
        """Test AI analysis performance."""
        # Mock AI analysis to avoid actual API calls
        mock_ai_analysis.return_value = {
            "ticker": "7203",
            "rating": "Bullish",
            "confidence": 0.85,
            "key_factors": ["Strong earnings"],
            "price_target_range": {"min": 2600, "max": 2800},
            "risk_factors": ["Market volatility"],
            "reasoning": "Strong performance"
        }
        
        # Test analysis request performance
        start_time = time.time()
        response = client.post("/api/v1/analysis/generate", json={
            "ticker": "7203",
            "analysis_type": "comprehensive"
        })
        end_time = time.time()
        
        analysis_time = (end_time - start_time) * 1000
        print(f"\nAI analysis time: {analysis_time:.2f}ms")
        
        # Should complete quickly (mocked)
        assert response.status_code in [200, 401]  # 401 if auth required
        assert analysis_time < 1000  # Under 1 second for mocked response


class TestConcurrentLoad:
    """Test concurrent load scenarios."""
    
    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)
    
    def test_concurrent_users_search(self, client):
        """Test concurrent users performing searches."""
        def perform_search(query):
            """Perform a search request."""
            start_time = time.time()
            try:
                response = client.get(f"/api/v1/stocks/search?query={query}")
                end_time = time.time()
                return {
                    'status_code': response.status_code,
                    'response_time': (end_time - start_time) * 1000,
                    'success': response.status_code == 200
                }
            except Exception as e:
                end_time = time.time()
                return {
                    'status_code': 500,
                    'response_time': (end_time - start_time) * 1000,
                    'success': False,
                    'error': str(e)
                }
        
        # Simulate 20 concurrent users
        queries = ["Toyota", "Sony", "Honda", "Nintendo", "SoftBank"] * 4
        
        results = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_query = {executor.submit(perform_search, query): query for query in queries}
            
            for future in as_completed(future_to_query):
                query = future_to_query[future]
                try:
                    result = future.result()
                    result['query'] = query
                    results.append(result)
                except Exception as exc:
                    print(f'Query {query} generated an exception: {exc}')
        
        # Analyze results
        successful_requests = [r for r in results if r['success']]
        failed_requests = [r for r in results if not r['success']]
        
        success_rate = len(successful_requests) / len(results) * 100
        avg_response_time = statistics.mean([r['response_time'] for r in successful_requests]) if successful_requests else 0
        
        print(f"\nConcurrent Load Test Results:")
        print(f"Total requests: {len(results)}")
        print(f"Successful requests: {len(successful_requests)}")
        print(f"Failed requests: {len(failed_requests)}")
        print(f"Success rate: {success_rate:.2f}%")
        print(f"Average response time: {avg_response_time:.2f}ms")
        
        # Performance requirements
        assert success_rate >= 95  # At least 95% success rate
        assert avg_response_time < 1000  # Average under 1 second
    
    def test_concurrent_user_registration(self, client):
        """Test concurrent user registrations."""
        def register_user(user_id):
            """Register a user."""
            user_data = {
                "email": f"loadtest{user_id}@example.com",
                "password": "LoadTest123!",
                "display_name": f"Load Test User {user_id}"
            }
            
            start_time = time.time()
            try:
                response = client.post("/api/v1/auth/register", json=user_data)
                end_time = time.time()
                return {
                    'user_id': user_id,
                    'status_code': response.status_code,
                    'response_time': (end_time - start_time) * 1000,
                    'success': response.status_code == 201
                }
            except Exception as e:
                end_time = time.time()
                return {
                    'user_id': user_id,
                    'status_code': 500,
                    'response_time': (end_time - start_time) * 1000,
                    'success': False,
                    'error': str(e)
                }
        
        # Simulate 10 concurrent registrations
        user_ids = range(1, 11)
        
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_user = {executor.submit(register_user, user_id): user_id for user_id in user_ids}
            
            for future in as_completed(future_to_user):
                user_id = future_to_user[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    print(f'User {user_id} registration generated an exception: {exc}')
        
        # Analyze results
        successful_registrations = [r for r in results if r['success']]
        failed_registrations = [r for r in results if not r['success']]
        
        success_rate = len(successful_registrations) / len(results) * 100
        avg_response_time = statistics.mean([r['response_time'] for r in successful_registrations]) if successful_registrations else 0
        
        print(f"\nConcurrent Registration Test Results:")
        print(f"Total registrations: {len(results)}")
        print(f"Successful registrations: {len(successful_registrations)}")
        print(f"Failed registrations: {len(failed_registrations)}")
        print(f"Success rate: {success_rate:.2f}%")
        print(f"Average response time: {avg_response_time:.2f}ms")
        
        # All registrations should succeed (different emails)
        assert success_rate >= 90  # At least 90% success rate
        assert avg_response_time < 2000  # Average under 2 seconds


class TestResourceUtilization:
    """Test resource utilization under load."""
    
    def test_memory_usage_under_load(self):
        """Test memory usage under load."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        client = TestClient(app)
        
        # Perform many requests to test memory usage
        for i in range(100):
            response = client.get("/api/v1/health")
            assert response.status_code == 200
            
            # Check memory every 10 requests
            if i % 10 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory
                
                print(f"Request {i}: Memory usage: {current_memory:.2f}MB (increase: {memory_increase:.2f}MB)")
                
                # Memory shouldn't grow excessively
                assert memory_increase < 100  # Less than 100MB increase
        
        final_memory = process.memory_info().rss / 1024 / 1024
        total_increase = final_memory - initial_memory
        
        print(f"\nMemory Usage Test:")
        print(f"Initial memory: {initial_memory:.2f}MB")
        print(f"Final memory: {final_memory:.2f}MB")
        print(f"Total increase: {total_increase:.2f}MB")
        
        # Total memory increase should be reasonable
        assert total_increase < 50  # Less than 50MB total increase
    
    def test_cpu_usage_monitoring(self):
        """Test CPU usage monitoring."""
        client = TestClient(app)
        
        # Monitor CPU usage during requests
        cpu_percentages = []
        
        def monitor_cpu():
            """Monitor CPU usage in background."""
            for _ in range(10):
                cpu_percent = psutil.cpu_percent(interval=0.1)
                cpu_percentages.append(cpu_percent)
        
        # Start CPU monitoring in background
        monitor_thread = threading.Thread(target=monitor_cpu)
        monitor_thread.start()
        
        # Perform requests
        for _ in range(50):
            response = client.get("/api/v1/stocks/search?query=test")
            # Don't assert status code as test data might not exist
        
        # Wait for monitoring to complete
        monitor_thread.join()
        
        if cpu_percentages:
            avg_cpu = statistics.mean(cpu_percentages)
            max_cpu = max(cpu_percentages)
            
            print(f"\nCPU Usage Test:")
            print(f"Average CPU: {avg_cpu:.2f}%")
            print(f"Max CPU: {max_cpu:.2f}%")
            
            # CPU usage should be reasonable
            assert avg_cpu < 80  # Average CPU under 80%
            assert max_cpu < 95  # Max CPU under 95%


class TestStressScenarios:
    """Test stress scenarios and edge cases."""
    
    def test_large_payload_handling(self):
        """Test handling of large payloads."""
        client = TestClient(app)
        
        # Test large search query
        large_query = "a" * 1000  # 1000 character query
        
        start_time = time.time()
        response = client.get(f"/api/v1/stocks/search?query={large_query}")
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000
        
        # Should handle large query gracefully
        assert response.status_code in [200, 400]  # 400 if query too long
        assert response_time < 5000  # Under 5 seconds
    
    def test_rapid_sequential_requests(self):
        """Test rapid sequential requests from single client."""
        client = TestClient(app)
        
        response_times = []
        
        # Make 50 rapid requests
        for i in range(50):
            start_time = time.time()
            response = client.get("/api/v1/health")
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000
            response_times.append(response_time)
            
            assert response.status_code == 200
        
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        print(f"\nRapid Sequential Requests Test:")
        print(f"Average response time: {avg_response_time:.2f}ms")
        print(f"Max response time: {max_response_time:.2f}ms")
        
        # Performance should remain consistent
        assert avg_response_time < 100  # Average under 100ms
        assert max_response_time < 500  # Max under 500ms
    
    def test_error_rate_under_load(self):
        """Test error rate under load conditions."""
        client = TestClient(app)
        
        # Mix of valid and invalid requests
        requests = [
            ("/api/v1/health", 200),
            ("/api/v1/stocks/INVALID", 404),
            ("/api/v1/stocks/search?query=test", 200),
            ("/api/v1/nonexistent", 404),
        ] * 25  # 100 total requests
        
        results = []
        
        for endpoint, expected_status in requests:
            try:
                response = client.get(endpoint)
                results.append({
                    'endpoint': endpoint,
                    'status_code': response.status_code,
                    'expected': expected_status,
                    'success': response.status_code == expected_status
                })
            except Exception as e:
                results.append({
                    'endpoint': endpoint,
                    'status_code': 500,
                    'expected': expected_status,
                    'success': False,
                    'error': str(e)
                })
        
        # Analyze error rates
        successful_requests = [r for r in results if r['success']]
        error_requests = [r for r in results if not r['success']]
        
        success_rate = len(successful_requests) / len(results) * 100
        
        print(f"\nError Rate Test:")
        print(f"Total requests: {len(results)}")
        print(f"Successful requests: {len(successful_requests)}")
        print(f"Error requests: {len(error_requests)}")
        print(f"Success rate: {success_rate:.2f}%")
        
        # Should handle expected errors correctly
        assert success_rate >= 95  # At least 95% of requests should behave as expected


@pytest.mark.asyncio
class TestAsyncPerformance:
    """Test async performance scenarios."""
    
    async def test_async_concurrent_requests(self):
        """Test async concurrent request handling."""
        async def make_request(session, endpoint):
            """Make async request."""
            start_time = time.time()
            try:
                response = await session.get(f"http://localhost:8000{endpoint}")
                end_time = time.time()
                return {
                    'endpoint': endpoint,
                    'status_code': response.status_code,
                    'response_time': (end_time - start_time) * 1000,
                    'success': response.status_code == 200
                }
            except Exception as e:
                end_time = time.time()
                return {
                    'endpoint': endpoint,
                    'status_code': 500,
                    'response_time': (end_time - start_time) * 1000,
                    'success': False,
                    'error': str(e)
                }
        
        endpoints = ["/api/v1/health"] * 50  # 50 concurrent requests
        
        async with AsyncClient() as session:
            tasks = [make_request(session, endpoint) for endpoint in endpoints]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = [r for r in results if isinstance(r, dict)]
        
        if valid_results:
            successful_requests = [r for r in valid_results if r['success']]
            avg_response_time = statistics.mean([r['response_time'] for r in successful_requests]) if successful_requests else 0
            success_rate = len(successful_requests) / len(valid_results) * 100
            
            print(f"\nAsync Concurrent Requests Test:")
            print(f"Total requests: {len(valid_results)}")
            print(f"Successful requests: {len(successful_requests)}")
            print(f"Success rate: {success_rate:.2f}%")
            print(f"Average response time: {avg_response_time:.2f}ms")
            
            # Performance requirements for async requests
            assert success_rate >= 90  # At least 90% success rate
            assert avg_response_time < 1000  # Average under 1 second


class TestProductionReadiness:
    """Test production readiness scenarios."""
    
    def test_health_check_reliability(self):
        """Test health check endpoint reliability."""
        client = TestClient(app)
        
        # Make 100 health check requests
        results = []
        for _ in range(100):
            start_time = time.time()
            response = client.get("/api/v1/health")
            end_time = time.time()
            
            results.append({
                'status_code': response.status_code,
                'response_time': (end_time - start_time) * 1000,
                'success': response.status_code == 200
            })
        
        # Analyze reliability
        successful_checks = [r for r in results if r['success']]
        success_rate = len(successful_checks) / len(results) * 100
        avg_response_time = statistics.mean([r['response_time'] for r in successful_checks])
        max_response_time = max([r['response_time'] for r in successful_checks])
        
        print(f"\nHealth Check Reliability Test:")
        print(f"Success rate: {success_rate:.2f}%")
        print(f"Average response time: {avg_response_time:.2f}ms")
        print(f"Max response time: {max_response_time:.2f}ms")
        
        # Health checks must be highly reliable
        assert success_rate == 100  # 100% success rate required
        assert avg_response_time < 50  # Average under 50ms
        assert max_response_time < 200  # Max under 200ms
    
    def test_graceful_degradation(self):
        """Test graceful degradation under stress."""
        # This would test how the system behaves when resources are constrained
        # For now, we'll test basic error handling
        client = TestClient(app)
        
        # Test with various invalid inputs
        invalid_requests = [
            "/api/v1/stocks/",  # Empty ticker
            "/api/v1/stocks/search",  # No query parameter
            "/api/v1/stocks/search?query=",  # Empty query
        ]
        
        for endpoint in invalid_requests:
            response = client.get(endpoint)
            
            # Should return proper error codes, not crash
            assert response.status_code in [400, 404, 422]
            
            # Should return JSON error response
            try:
                error_data = response.json()
                assert "detail" in error_data or "message" in error_data
            except:
                # Some endpoints might return HTML error pages
                pass