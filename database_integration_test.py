#!/usr/bin/env python3
"""
Database Integration Test Suite
Tests database operations, data integrity, performance, and migrations
"""

import os
import sys
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import psycopg2
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
import redis

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from backend.app.core.config import settings
    from backend.app.models.user import User
    from backend.app.models.stock import Stock, WatchlistStock
    from backend.app.models.subscription import Subscription, Plan
    from backend.app.models.news import NewsArticle
    from backend.app.models.analysis import AIAnalysis
    from backend.app.core.database import get_db
except ImportError as e:
    print(f"Warning: Could not import backend modules: {e}")

class DatabaseIntegrationTest:
    """Database integration test suite"""
    
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/kessan_test")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/1")
        self.engine = None
        self.redis_client = None
        self.test_results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": []
        }
        
    def setup_connections(self):
        """Setup database and Redis connections"""
        print("🔧 Setting up database connections...")
        
        try:
            self.engine = create_engine(self.db_url)
            print("✅ PostgreSQL connection established")
        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}")
            raise
            
        try:
            self.redis_client = redis.from_url(self.redis_url)
            self.redis_client.ping()
            print("✅ Redis connection established")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            raise
            
    def run_test(self, test_name: str, test_func):
        """Run a single test with error handling"""
        self.test_results["total_tests"] += 1
        print(f"\n🧪 Testing: {test_name}")
        
        try:
            start_time = time.time()
            result = test_func()
            end_time = time.time()
            
            if result:
                self.test_results["passed"] += 1
                print(f"✅ {test_name} - PASSED ({end_time - start_time:.2f}s)")
                return True
            else:
                self.test_results["failed"] += 1
                print(f"❌ {test_name} - FAILED ({end_time - start_time:.2f}s)")
                return False
                
        except Exception as e:
            self.test_results["failed"] += 1
            error_msg = f"{test_name}: {str(e)}\n{traceback.format_exc()}"
            self.test_results["errors"].append(error_msg)
            print(f"❌ {test_name} - ERROR: {e}")
            return False
            
    def test_database_connectivity(self) -> bool:
        """Test basic database connectivity"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1 as test"))
                return result.fetchone()[0] == 1
        except Exception as e:
            print(f"Database connectivity test failed: {e}")
            return False
            
    def test_table_existence(self) -> bool:
        """Test that all required tables exist"""
        required_tables = [
            'users', 'stocks', 'watchlist_stocks', 'subscriptions', 
            'plans', 'news_articles', 'ai_analyses', 'user_profiles',
            'oauth_identities', 'user_activity_logs'
        ]
        
        try:
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()
            
            missing_tables = [table for table in required_tables if table not in existing_tables]
            
            if missing_tables:
                print(f"Missing tables: {missing_tables}")
                return False
                
            print(f"✅ All {len(required_tables)} required tables exist")
            return True
            
        except Exception as e:
            print(f"Table existence test failed: {e}")
            return False
            
    def test_table_indexes(self) -> bool:
        """Test that critical indexes exist for performance"""
        critical_indexes = {
            'users': ['email', 'created_at'],
            'stocks': ['ticker', 'company_name_jp'],
            'watchlist_stocks': ['user_id', 'ticker'],
            'news_articles': ['published_at', 'ticker'],
            'ai_analyses': ['ticker', 'analysis_type', 'created_at']
        }
        
        try:
            inspector = inspect(self.engine)
            
            for table_name, expected_indexes in critical_indexes.items():
                if table_name not in inspector.get_table_names():
                    continue
                    
                indexes = inspector.get_indexes(table_name)
                index_columns = []
                for index in indexes:
                    index_columns.extend(index['column_names'])
                
                missing_indexes = [col for col in expected_indexes if col not in index_columns]
                if missing_indexes:
                    print(f"Missing indexes on {table_name}: {missing_indexes}")
                    return False
                    
            print("✅ All critical indexes exist")
            return True
            
        except Exception as e:
            print(f"Index test failed: {e}")
            return False
            
    def test_data_integrity_constraints(self) -> bool:
        """Test database constraints and foreign keys"""
        try:
            with self.engine.connect() as conn:
                # Test foreign key constraints
                constraints_query = text("""
                    SELECT 
                        tc.table_name, 
                        tc.constraint_name, 
                        tc.constraint_type
                    FROM information_schema.table_constraints tc
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = 'public'
                """)
                
                result = conn.execute(constraints_query)
                foreign_keys = result.fetchall()
                
                if len(foreign_keys) < 5:  # Expect at least 5 foreign key constraints
                    print(f"Insufficient foreign key constraints: {len(foreign_keys)}")
                    return False
                    
                print(f"✅ Found {len(foreign_keys)} foreign key constraints")
                return True
                
        except Exception as e:
            print(f"Data integrity test failed: {e}")
            return False
            
    def test_crud_operations(self) -> bool:
        """Test basic CRUD operations on key tables"""
        try:
            with self.engine.connect() as conn:
                # Test user CRUD
                test_email = f"test_{int(time.time())}@example.com"
                
                # Create
                insert_query = text("""
                    INSERT INTO users (email, hashed_password, full_name, is_active, created_at)
                    VALUES (:email, :password, :name, :active, :created_at)
                    RETURNING id
                """)
                
                result = conn.execute(insert_query, {
                    'email': test_email,
                    'password': 'hashed_password',
                    'name': 'Test User',
                    'active': True,
                    'created_at': datetime.utcnow()
                })
                
                user_id = result.fetchone()[0]
                
                # Read
                select_query = text("SELECT email FROM users WHERE id = :user_id")
                result = conn.execute(select_query, {'user_id': user_id})
                retrieved_email = result.fetchone()[0]
                
                if retrieved_email != test_email:
                    return False
                    
                # Update
                update_query = text("UPDATE users SET full_name = :name WHERE id = :user_id")
                conn.execute(update_query, {'name': 'Updated Test User', 'user_id': user_id})
                
                # Delete
                delete_query = text("DELETE FROM users WHERE id = :user_id")
                conn.execute(delete_query, {'user_id': user_id})
                
                # Verify deletion
                result = conn.execute(select_query, {'user_id': user_id})
                if result.fetchone() is not None:
                    return False
                    
                conn.commit()
                print("✅ CRUD operations successful")
                return True
                
        except Exception as e:
            print(f"CRUD operations test failed: {e}")
            return False
            
    def test_query_performance(self) -> bool:
        """Test query performance on key operations"""
        try:
            with self.engine.connect() as conn:
                # Test stock search performance
                start_time = time.time()
                search_query = text("""
                    SELECT ticker, company_name_jp 
                    FROM stocks 
                    WHERE company_name_jp ILIKE '%Toyota%' 
                    LIMIT 10
                """)
                
                result = conn.execute(search_query)
                results = result.fetchall()
                end_time = time.time()
                
                search_time = end_time - start_time
                if search_time > 1.0:  # Should complete within 1 second
                    print(f"Stock search too slow: {search_time:.2f}s")
                    return False
                    
                # Test watchlist query performance
                start_time = time.time()
                watchlist_query = text("""
                    SELECT w.ticker, s.company_name_jp, w.notes
                    FROM watchlist_stocks w
                    JOIN stocks s ON w.ticker = s.ticker
                    WHERE w.user_id = 1
                    LIMIT 50
                """)
                
                result = conn.execute(watchlist_query)
                results = result.fetchall()
                end_time = time.time()
                
                watchlist_time = end_time - start_time
                if watchlist_time > 0.5:  # Should complete within 0.5 seconds
                    print(f"Watchlist query too slow: {watchlist_time:.2f}s")
                    return False
                    
                print(f"✅ Query performance acceptable (search: {search_time:.3f}s, watchlist: {watchlist_time:.3f}s)")
                return True
                
        except Exception as e:
            print(f"Query performance test failed: {e}")
            return False
            
    def test_data_consistency(self) -> bool:
        """Test data consistency across related tables"""
        try:
            with self.engine.connect() as conn:
                # Check for orphaned watchlist entries
                orphaned_watchlist_query = text("""
                    SELECT COUNT(*) FROM watchlist_stocks w
                    LEFT JOIN users u ON w.user_id = u.id
                    WHERE u.id IS NULL
                """)
                
                result = conn.execute(orphaned_watchlist_query)
                orphaned_count = result.fetchone()[0]
                
                if orphaned_count > 0:
                    print(f"Found {orphaned_count} orphaned watchlist entries")
                    return False
                    
                # Check for invalid stock references
                invalid_stocks_query = text("""
                    SELECT COUNT(*) FROM watchlist_stocks w
                    LEFT JOIN stocks s ON w.ticker = s.ticker
                    WHERE s.ticker IS NULL
                """)
                
                result = conn.execute(invalid_stocks_query)
                invalid_count = result.fetchone()[0]
                
                if invalid_count > 0:
                    print(f"Found {invalid_count} invalid stock references")
                    return False
                    
                print("✅ Data consistency checks passed")
                return True
                
        except Exception as e:
            print(f"Data consistency test failed: {e}")
            return False
            
    def test_redis_operations(self) -> bool:
        """Test Redis cache operations"""
        try:
            test_key = f"test_key_{int(time.time())}"
            test_data = {"ticker": "7203", "price": 2500.0, "timestamp": time.time()}
            
            # Test string operations
            self.redis_client.set(test_key, str(test_data), ex=60)
            retrieved_data = self.redis_client.get(test_key)
            
            if not retrieved_data:
                return False
                
            # Test hash operations
            hash_key = f"hash_{test_key}"
            self.redis_client.hset(hash_key, mapping=test_data)
            retrieved_hash = self.redis_client.hgetall(hash_key)
            
            if not retrieved_hash:
                return False
                
            # Test list operations
            list_key = f"list_{test_key}"
            self.redis_client.lpush(list_key, "item1", "item2", "item3")
            list_length = self.redis_client.llen(list_key)
            
            if list_length != 3:
                return False
                
            # Cleanup
            self.redis_client.delete(test_key, hash_key, list_key)
            
            print("✅ Redis operations successful")
            return True
            
        except Exception as e:
            print(f"Redis operations test failed: {e}")
            return False
            
    def test_cache_performance(self) -> bool:
        """Test Redis cache performance"""
        try:
            # Test write performance
            start_time = time.time()
            for i in range(100):
                self.redis_client.set(f"perf_test_{i}", f"value_{i}", ex=60)
            write_time = time.time() - start_time
            
            # Test read performance
            start_time = time.time()
            for i in range(100):
                self.redis_client.get(f"perf_test_{i}")
            read_time = time.time() - start_time
            
            # Cleanup
            keys_to_delete = [f"perf_test_{i}" for i in range(100)]
            self.redis_client.delete(*keys_to_delete)
            
            if write_time > 1.0 or read_time > 0.5:
                print(f"Cache performance too slow (write: {write_time:.2f}s, read: {read_time:.2f}s)")
                return False
                
            print(f"✅ Cache performance acceptable (write: {write_time:.3f}s, read: {read_time:.3f}s)")
            return True
            
        except Exception as e:
            print(f"Cache performance test failed: {e}")
            return False
            
    def test_database_size_and_limits(self) -> bool:
        """Test database size and connection limits"""
        try:
            with self.engine.connect() as conn:
                # Check database size
                size_query = text("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as size
                """)
                
                result = conn.execute(size_query)
                db_size = result.fetchone()[0]
                
                # Check active connections
                connections_query = text("""
                    SELECT count(*) FROM pg_stat_activity 
                    WHERE state = 'active'
                """)
                
                result = conn.execute(connections_query)
                active_connections = result.fetchone()[0]
                
                print(f"✅ Database size: {db_size}, Active connections: {active_connections}")
                return True
                
        except Exception as e:
            print(f"Database size test failed: {e}")
            return False
            
    def run_all_tests(self):
        """Run all database integration tests"""
        print("🚀 Starting Database Integration Test Suite")
        print("=" * 60)
        
        # Setup
        self.setup_connections()
        
        # Test suite
        test_suite = [
            # Basic Database Tests
            ("Database Connectivity", self.test_database_connectivity),
            ("Table Existence", self.test_table_existence),
            ("Table Indexes", self.test_table_indexes),
            ("Data Integrity Constraints", self.test_data_integrity_constraints),
            
            # CRUD and Transaction Tests
            ("CRUD Operations", self.test_crud_operations),
            ("Database Transactions", self.test_database_transactions),
            ("Database Constraints Enforcement", self.test_database_constraints_enforcement),
            
            # Performance Tests
            ("Query Performance", self.test_query_performance),
            ("Advanced Query Performance", self.test_advanced_query_performance),
            ("Connection Pooling", self.test_connection_pooling),
            
            # Data Consistency and Integrity
            ("Data Consistency", self.test_data_consistency),
            
            # Redis Cache Tests
            ("Redis Operations", self.test_redis_operations),
            ("Redis Advanced Operations", self.test_redis_advanced_operations),
            ("Cache Performance", self.test_cache_performance),
            ("Cache Eviction Policies", self.test_cache_eviction_policies),
            
            # Database Administration
            ("Database Size and Limits", self.test_database_size_and_limits),
            ("Database Backup Readiness", self.test_database_backup_readiness),
            ("Database Monitoring Queries", self.test_database_monitoring_queries),
        ]
        
        # Run all tests
        for test_name, test_func in test_suite:
            self.run_test(test_name, test_func)
            
        # Print results
        self.print_results()
        
        return self.test_results["failed"] == 0
        
    def test_advanced_query_performance(self) -> bool:
        """Test advanced query performance scenarios"""
        try:
            with self.engine.connect() as conn:
                # Test complex join query performance
                start_time = time.time()
                complex_query = text("""
                    SELECT 
                        w.ticker, 
                        s.company_name_jp, 
                        u.email,
                        COUNT(n.id) as news_count
                    FROM watchlist_stocks w
                    JOIN stocks s ON w.ticker = s.ticker
                    JOIN users u ON w.user_id = u.id
                    LEFT JOIN news_articles n ON n.ticker = w.ticker
                    WHERE w.created_at > NOW() - INTERVAL '30 days'
                    GROUP BY w.ticker, s.company_name_jp, u.email
                    LIMIT 100
                """)
                
                result = conn.execute(complex_query)
                results = result.fetchall()
                end_time = time.time()
                
                complex_query_time = end_time - start_time
                if complex_query_time > 2.0:  # Should complete within 2 seconds
                    print(f"Complex query too slow: {complex_query_time:.2f}s")
                    return False
                    
                # Test aggregation query performance
                start_time = time.time()
                agg_query = text("""
                    SELECT 
                        DATE_TRUNC('day', created_at) as date,
                        COUNT(*) as daily_count,
                        COUNT(DISTINCT user_id) as unique_users
                    FROM watchlist_stocks
                    WHERE created_at > NOW() - INTERVAL '90 days'
                    GROUP BY DATE_TRUNC('day', created_at)
                    ORDER BY date DESC
                """)
                
                result = conn.execute(agg_query)
                results = result.fetchall()
                end_time = time.time()
                
                agg_query_time = end_time - start_time
                if agg_query_time > 1.5:  # Should complete within 1.5 seconds
                    print(f"Aggregation query too slow: {agg_query_time:.2f}s")
                    return False
                    
                print(f"✅ Advanced query performance acceptable (complex: {complex_query_time:.3f}s, agg: {agg_query_time:.3f}s)")
                return True
                
        except Exception as e:
            print(f"Advanced query performance test failed: {e}")
            return False
            
    def test_database_transactions(self) -> bool:
        """Test database transaction handling"""
        try:
            with self.engine.connect() as conn:
                # Test successful transaction
                trans = conn.begin()
                try:
                    test_email = f"transaction_test_{int(time.time())}@example.com"
                    
                    # Insert user
                    insert_user = text("""
                        INSERT INTO users (email, hashed_password, full_name, is_active, created_at)
                        VALUES (:email, :password, :name, :active, :created_at)
                        RETURNING id
                    """)
                    
                    result = conn.execute(insert_user, {
                        'email': test_email,
                        'password': 'hashed_password',
                        'name': 'Transaction Test User',
                        'active': True,
                        'created_at': datetime.utcnow()
                    })
                    
                    user_id = result.fetchone()[0]
                    
                    # Insert watchlist entry
                    insert_watchlist = text("""
                        INSERT INTO watchlist_stocks (user_id, ticker, notes, created_at)
                        VALUES (:user_id, :ticker, :notes, :created_at)
                    """)
                    
                    conn.execute(insert_watchlist, {
                        'user_id': user_id,
                        'ticker': '7203',
                        'notes': 'Transaction test',
                        'created_at': datetime.utcnow()
                    })
                    
                    trans.commit()
                    
                    # Verify data exists
                    verify_query = text("SELECT COUNT(*) FROM users WHERE email = :email")
                    result = conn.execute(verify_query, {'email': test_email})
                    if result.fetchone()[0] != 1:
                        return False
                        
                    # Cleanup
                    cleanup_watchlist = text("DELETE FROM watchlist_stocks WHERE user_id = :user_id")
                    conn.execute(cleanup_watchlist, {'user_id': user_id})
                    
                    cleanup_user = text("DELETE FROM users WHERE id = :user_id")
                    conn.execute(cleanup_user, {'user_id': user_id})
                    conn.commit()
                    
                except Exception as e:
                    trans.rollback()
                    raise e
                    
                print("✅ Database transactions working correctly")
                return True
                
        except Exception as e:
            print(f"Database transaction test failed: {e}")
            return False
            
    def test_database_constraints_enforcement(self) -> bool:
        """Test database constraint enforcement"""
        try:
            with self.engine.connect() as conn:
                # Test unique constraint on email
                test_email = f"constraint_test_{int(time.time())}@example.com"
                
                # Insert first user
                insert_query = text("""
                    INSERT INTO users (email, hashed_password, full_name, is_active, created_at)
                    VALUES (:email, :password, :name, :active, :created_at)
                    RETURNING id
                """)
                
                result = conn.execute(insert_query, {
                    'email': test_email,
                    'password': 'hashed_password',
                    'name': 'Constraint Test User',
                    'active': True,
                    'created_at': datetime.utcnow()
                })
                
                user_id = result.fetchone()[0]
                conn.commit()
                
                # Try to insert duplicate email (should fail)
                try:
                    conn.execute(insert_query, {
                        'email': test_email,  # Same email
                        'password': 'hashed_password',
                        'name': 'Duplicate User',
                        'active': True,
                        'created_at': datetime.utcnow()
                    })
                    conn.commit()
                    
                    # If we get here, constraint wasn't enforced
                    print("Email uniqueness constraint not enforced")
                    return False
                    
                except Exception:
                    # Expected to fail due to constraint
                    conn.rollback()
                    
                # Cleanup
                cleanup_query = text("DELETE FROM users WHERE id = :user_id")
                conn.execute(cleanup_query, {'user_id': user_id})
                conn.commit()
                
                print("✅ Database constraints properly enforced")
                return True
                
        except Exception as e:
            print(f"Database constraint test failed: {e}")
            return False
            
    def test_database_backup_readiness(self) -> bool:
        """Test database backup readiness"""
        try:
            with self.engine.connect() as conn:
                # Check if WAL archiving is enabled (for PostgreSQL)
                wal_query = text("SHOW wal_level")
                result = conn.execute(wal_query)
                wal_level = result.fetchone()[0]
                
                # Check database size for backup planning
                size_query = text("""
                    SELECT 
                        pg_size_pretty(pg_database_size(current_database())) as db_size,
                        pg_database_size(current_database()) as db_size_bytes
                """)
                
                result = conn.execute(size_query)
                size_info = result.fetchone()
                
                print(f"✅ Database backup readiness: WAL level: {wal_level}, Size: {size_info[0]}")
                return True
                
        except Exception as e:
            print(f"Database backup readiness test failed: {e}")
            return False
            
    def test_connection_pooling(self) -> bool:
        """Test database connection pooling behavior"""
        try:
            # Test multiple concurrent connections
            import concurrent.futures
            import threading
            
            def test_connection():
                try:
                    with self.engine.connect() as conn:
                        result = conn.execute(text("SELECT 1"))
                        return result.fetchone()[0] == 1
                except Exception:
                    return False
                    
            # Test 20 concurrent connections
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                futures = [executor.submit(test_connection) for _ in range(20)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
                
            success_rate = sum(results) / len(results)
            if success_rate < 0.95:  # 95% success rate minimum
                print(f"Connection pooling test failed: {success_rate*100}% success rate")
                return False
                
            print(f"✅ Connection pooling working: {success_rate*100}% success rate")
            return True
            
        except Exception as e:
            print(f"Connection pooling test failed: {e}")
            return False
            
    def test_redis_advanced_operations(self) -> bool:
        """Test advanced Redis operations"""
        try:
            # Test Redis pub/sub
            pubsub = self.redis_client.pubsub()
            test_channel = f"test_channel_{int(time.time())}"
            
            pubsub.subscribe(test_channel)
            
            # Publish a message
            self.redis_client.publish(test_channel, "test_message")
            
            # Check if message was received (with timeout)
            message = pubsub.get_message(timeout=1.0)
            if message and message['type'] == 'subscribe':
                message = pubsub.get_message(timeout=1.0)  # Get actual message
                
            pubsub.unsubscribe(test_channel)
            pubsub.close()
            
            # Test Redis sorted sets
            sorted_set_key = f"test_sorted_set_{int(time.time())}"
            
            # Add members with scores
            self.redis_client.zadd(sorted_set_key, {"member1": 1, "member2": 2, "member3": 3})
            
            # Get range
            members = self.redis_client.zrange(sorted_set_key, 0, -1, withscores=True)
            
            if len(members) != 3:
                return False
                
            # Cleanup
            self.redis_client.delete(sorted_set_key)
            
            # Test Redis transactions
            pipe = self.redis_client.pipeline()
            test_key = f"transaction_test_{int(time.time())}"
            
            pipe.multi()
            pipe.set(test_key, "value1")
            pipe.incr(f"{test_key}_counter")
            pipe.expire(test_key, 60)
            results = pipe.execute()
            
            # Cleanup
            self.redis_client.delete(test_key, f"{test_key}_counter")
            
            print("✅ Advanced Redis operations successful")
            return True
            
        except Exception as e:
            print(f"Advanced Redis operations test failed: {e}")
            return False
            
    def test_cache_eviction_policies(self) -> bool:
        """Test Redis cache eviction policies"""
        try:
            # Get Redis memory info
            memory_info = self.redis_client.info('memory')
            max_memory = memory_info.get('maxmemory', 0)
            
            if max_memory > 0:
                # Test cache eviction by filling memory
                test_keys = []
                for i in range(1000):
                    key = f"eviction_test_{i}"
                    self.redis_client.set(key, "x" * 1000, ex=300)  # 1KB per key
                    test_keys.append(key)
                    
                # Check how many keys remain
                remaining_keys = sum(1 for key in test_keys if self.redis_client.exists(key))
                
                # Cleanup remaining keys
                if remaining_keys > 0:
                    self.redis_client.delete(*[key for key in test_keys if self.redis_client.exists(key)])
                    
                print(f"✅ Cache eviction test: {remaining_keys}/{len(test_keys)} keys remained")
            else:
                print("⚠️ No memory limit set for Redis, skipping eviction test")
                
            return True
            
        except Exception as e:
            print(f"Cache eviction test failed: {e}")
            return False
            
    def test_database_monitoring_queries(self) -> bool:
        """Test database monitoring and diagnostic queries"""
        try:
            with self.engine.connect() as conn:
                # Test slow query detection
                slow_queries = text("""
                    SELECT query, calls, total_time, mean_time
                    FROM pg_stat_statements
                    WHERE mean_time > 100
                    ORDER BY mean_time DESC
                    LIMIT 10
                """)
                
                try:
                    result = conn.execute(slow_queries)
                    slow_query_results = result.fetchall()
                    print(f"✅ Found {len(slow_query_results)} potentially slow queries")
                except Exception:
                    print("⚠️ pg_stat_statements extension not available")
                    
                # Test table statistics
                table_stats = text("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_tup_ins as inserts,
                        n_tup_upd as updates,
                        n_tup_del as deletes,
                        n_live_tup as live_tuples
                    FROM pg_stat_user_tables
                    ORDER BY n_live_tup DESC
                    LIMIT 10
                """)
                
                result = conn.execute(table_stats)
                table_results = result.fetchall()
                
                print(f"✅ Retrieved statistics for {len(table_results)} tables")
                
                # Test index usage
                index_usage = text("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_scan,
                        idx_tup_read,
                        idx_tup_fetch
                    FROM pg_stat_user_indexes
                    WHERE idx_scan > 0
                    ORDER BY idx_scan DESC
                    LIMIT 10
                """)
                
                result = conn.execute(index_usage)
                index_results = result.fetchall()
                
                print(f"✅ Found {len(index_results)} actively used indexes")
                return True
                
        except Exception as e:
            print(f"Database monitoring queries test failed: {e}")
            return False
            
    def print_results(self):
        """Print test results"""
        print("\n" + "=" * 60)
        print("🏁 DATABASE INTEGRATION TEST RESULTS")
        print("=" * 60)
        
        total = self.test_results["total_tests"]
        passed = self.test_results["passed"]
        failed = self.test_results["failed"]
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if self.test_results["errors"]:
            print("\n🔍 ERROR DETAILS:")
            print("-" * 40)
            for error in self.test_results["errors"]:
                print(error)
                print("-" * 40)
                
        # Overall status
        if failed == 0:
            print("\n🎉 ALL DATABASE TESTS PASSED!")
        elif failed <= 2:
            print("\n⚠️ MOSTLY PASSING - Minor database issues detected.")
        else:
            print("\n🚨 MULTIPLE DATABASE FAILURES - Needs attention.")

def main():
    """Main function"""
    test_runner = DatabaseIntegrationTest()
    
    try:
        success = test_runner.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Database test suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Database test suite crashed: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()