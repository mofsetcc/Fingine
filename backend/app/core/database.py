"""
Database connection and session management with optimization.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseMetrics:
    """Database performance metrics collector."""
    
    def __init__(self):
        self.query_count = 0
        self.total_query_time = 0.0
        self.slow_queries = []
        self.connection_pool_stats = {}
    
    def record_query(self, query_time: float, query: str):
        """Record query execution metrics."""
        self.query_count += 1
        self.total_query_time += query_time
        
        # Track slow queries (>100ms)
        if query_time > 0.1:
            self.slow_queries.append({
                'query': query[:200] + '...' if len(query) > 200 else query,
                'execution_time': query_time,
                'timestamp': time.time()
            })
            
            # Keep only last 100 slow queries
            if len(self.slow_queries) > 100:
                self.slow_queries.pop(0)
    
    def get_stats(self) -> dict:
        """Get current database statistics."""
        avg_query_time = self.total_query_time / self.query_count if self.query_count > 0 else 0
        return {
            'total_queries': self.query_count,
            'average_query_time': avg_query_time,
            'slow_query_count': len(self.slow_queries),
            'connection_pool': self.connection_pool_stats
        }


# Global metrics instance
db_metrics = DatabaseMetrics()


def create_optimized_engine() -> AsyncEngine:
    """Create optimized database engine with connection pooling."""
    
    # Use NullPool for testing, QueuePool for production
    if "test" in settings.DATABASE_URL:
        poolclass = NullPool
        pool_kwargs = {}
    else:
        poolclass = QueuePool
        pool_kwargs = {
            'pool_size': settings.DATABASE_POOL_SIZE,
            'max_overflow': settings.DATABASE_MAX_OVERFLOW,
            'pool_timeout': 30,  # 30 seconds timeout
            'pool_recycle': 3600,  # Recycle connections every hour
            'pool_pre_ping': True,  # Validate connections before use
        }
    
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=settings.DEBUG,
        poolclass=poolclass,
        connect_args={
            "server_settings": {
                "application_name": "kessan_backend",
                "jit": "off",  # Disable JIT for consistent performance
            },
            "command_timeout": 60,  # 60 second query timeout
        },
        **pool_kwargs
    )
    
    # Add connection pool monitoring
    if not isinstance(engine.pool, NullPool):
        @event.listens_for(engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set connection-level optimizations."""
            pass
        
        @event.listens_for(engine.sync_engine.pool, "connect")
        def on_connect(dbapi_conn, connection_record):
            """Track connection events."""
            db_metrics.connection_pool_stats['connections_created'] = \
                db_metrics.connection_pool_stats.get('connections_created', 0) + 1
        
        @event.listens_for(engine.sync_engine.pool, "checkout")
        def on_checkout(dbapi_conn, connection_record, connection_proxy):
            """Track connection checkouts."""
            db_metrics.connection_pool_stats['connections_checked_out'] = \
                db_metrics.connection_pool_stats.get('connections_checked_out', 0) + 1
        
        @event.listens_for(engine.sync_engine.pool, "checkin")
        def on_checkin(dbapi_conn, connection_record):
            """Track connection checkins."""
            db_metrics.connection_pool_stats['connections_checked_in'] = \
                db_metrics.connection_pool_stats.get('connections_checked_in', 0) + 1
    
    return engine


# Create async engine (lazy initialization)
engine = None


def get_engine() -> AsyncEngine:
    """Get or create the database engine."""
    global engine
    if engine is None:
        engine = create_optimized_engine()
    return engine

# Create async session factory with optimization
def get_session_factory():
    """Get session factory with current engine."""
    return sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,  # Manual flush control for better performance
    )


class QueryMonitoringSession(AsyncSession):
    """Session wrapper with query monitoring."""
    
    async def execute(self, statement, parameters=None, execution_options=None, bind_arguments=None, _parent_execute_state=None, _add_event=None):
        """Execute with timing and monitoring."""
        start_time = time.time()
        
        try:
            result = await super().execute(
                statement, parameters, execution_options, 
                bind_arguments, _parent_execute_state, _add_event
            )
            
            execution_time = time.time() - start_time
            query_str = str(statement)
            
            # Record metrics
            db_metrics.record_query(execution_time, query_str)
            
            # Log slow queries
            if execution_time > 0.1:  # 100ms threshold
                logger.warning(
                    f"Slow query detected: {execution_time:.3f}s - {query_str[:200]}..."
                )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Query failed after {execution_time:.3f}s: {str(e)}")
            raise


def create_monitored_session() -> QueryMonitoringSession:
    """Create a session with query monitoring."""
    return QueryMonitoringSession(bind=get_engine(), expire_on_commit=False, autoflush=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session with monitoring."""
    session_factory = get_session_factory()
    
    if settings.DEBUG or settings.ENVIRONMENT == "development":
        # Use monitoring session in development
        session = create_monitored_session()
    else:
        # Use regular session in production for performance
        session = session_factory()
    
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def create_tables():
    """Create all database tables."""
    from app.models.base import Base
    
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all database tables."""
    from app.models.base import Base
    
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def optimize_database():
    """Run database optimization commands."""
    async with get_db_session() as session:
        # Update table statistics for better query planning
        await session.execute(text("ANALYZE"))
        
        # Vacuum analyze for maintenance
        if settings.ENVIRONMENT == "production":
            await session.execute(text("VACUUM ANALYZE"))
        
        logger.info("Database optimization completed")


async def get_database_stats() -> dict:
    """Get comprehensive database statistics."""
    async with get_db_session() as session:
        # Get table sizes
        table_sizes_query = text("""
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        """)
        
        table_sizes_result = await session.execute(table_sizes_query)
        table_sizes = [dict(row._mapping) for row in table_sizes_result]
        
        # Get index usage statistics
        index_usage_query = text("""
            SELECT 
                schemaname,
                tablename,
                indexname,
                idx_scan,
                idx_tup_read,
                idx_tup_fetch
            FROM pg_stat_user_indexes
            ORDER BY idx_scan DESC
            LIMIT 20
        """)
        
        index_usage_result = await session.execute(index_usage_query)
        index_usage = [dict(row._mapping) for row in index_usage_result]
        
        # Get connection statistics
        connection_stats_query = text("""
            SELECT 
                state,
                count(*) as count
            FROM pg_stat_activity 
            WHERE datname = current_database()
            GROUP BY state
        """)
        
        connection_stats_result = await session.execute(connection_stats_query)
        connection_stats = [dict(row._mapping) for row in connection_stats_result]
        
        return {
            'table_sizes': table_sizes,
            'index_usage': index_usage,
            'connection_stats': connection_stats,
            'query_metrics': db_metrics.get_stats()
        }


async def check_database_health() -> dict:
    """Check database health and performance."""
    try:
        async with get_db_session() as session:
            # Test basic connectivity
            start_time = time.time()
            await session.execute(text("SELECT 1"))
            connection_time = time.time() - start_time
            
            # Check for long-running queries
            long_queries_query = text("""
                SELECT 
                    pid,
                    now() - pg_stat_activity.query_start AS duration,
                    query
                FROM pg_stat_activity
                WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
                AND state = 'active'
            """)
            
            long_queries_result = await session.execute(long_queries_query)
            long_queries = [dict(row._mapping) for row in long_queries_result]
            
            # Check connection pool status
            pool_status = {}
            if hasattr(engine.pool, 'size'):
                pool_status = {
                    'pool_size': engine.pool.size(),
                    'checked_in': engine.pool.checkedin(),
                    'checked_out': engine.pool.checkedout(),
                    'overflow': engine.pool.overflow(),
                    'invalid': engine.pool.invalid()
                }
            
            return {
                'status': 'healthy',
                'connection_time': connection_time,
                'long_running_queries': len(long_queries),
                'pool_status': pool_status,
                'metrics': db_metrics.get_stats()
            }
            
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'metrics': db_metrics.get_stats()
        }