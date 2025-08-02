"""
Database monitoring and alerting service.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session, db_metrics
from app.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseMonitor:
    """Database performance monitoring and alerting."""
    
    def __init__(self):
        self.alert_thresholds = {
            'slow_query_count': 10,  # Alert if more than 10 slow queries in 5 minutes
            'connection_pool_usage': 0.8,  # Alert if pool usage > 80%
            'average_query_time': 0.5,  # Alert if average query time > 500ms
            'long_running_queries': 5,  # Alert if queries running > 5 minutes
            'connection_errors': 5,  # Alert if > 5 connection errors in 5 minutes
        }
        self.alert_history = []
        self.last_stats = {}
    
    async def check_performance_metrics(self) -> Dict:
        """Check database performance metrics."""
        try:
            async with get_db_session() as session:
                # Get current database statistics
                stats = await self._get_detailed_stats(session)
                
                # Check for performance issues
                alerts = await self._check_alerts(stats)
                
                # Update last stats
                self.last_stats = stats
                
                return {
                    'timestamp': datetime.utcnow().isoformat(),
                    'stats': stats,
                    'alerts': alerts,
                    'status': 'healthy' if not alerts else 'warning'
                }
                
        except Exception as e:
            logger.error(f"Database monitoring failed: {str(e)}")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'error',
                'error': str(e)
            }
    
    async def _get_detailed_stats(self, session: AsyncSession) -> Dict:
        """Get detailed database statistics."""
        
        # Query performance statistics
        query_stats = text("""
            SELECT 
                schemaname,
                tablename,
                seq_scan,
                seq_tup_read,
                idx_scan,
                idx_tup_fetch,
                n_tup_ins,
                n_tup_upd,
                n_tup_del
            FROM pg_stat_user_tables
            ORDER BY seq_scan DESC
        """)
        
        query_result = await session.execute(query_stats)
        table_stats = [dict(row._mapping) for row in query_result]
        
        # Index usage statistics
        index_stats = text("""
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
            LIMIT 20
        """)
        
        index_result = await session.execute(index_stats)
        index_usage = [dict(row._mapping) for row in index_result]
        
        # Connection statistics
        connection_stats = text("""
            SELECT 
                state,
                count(*) as count,
                max(now() - query_start) as max_duration
            FROM pg_stat_activity 
            WHERE datname = current_database()
            GROUP BY state
        """)
        
        connection_result = await session.execute(connection_stats)
        connections = [dict(row._mapping) for row in connection_result]
        
        # Long running queries
        long_queries = text("""
            SELECT 
                pid,
                usename,
                application_name,
                client_addr,
                now() - query_start AS duration,
                state,
                left(query, 100) as query_preview
            FROM pg_stat_activity
            WHERE (now() - query_start) > interval '1 minute'
            AND state = 'active'
            AND query NOT LIKE '%pg_stat_activity%'
            ORDER BY duration DESC
        """)
        
        long_queries_result = await session.execute(long_queries)
        long_running = [dict(row._mapping) for row in long_queries_result]
        
        # Database size information
        db_size = text("""
            SELECT 
                pg_size_pretty(pg_database_size(current_database())) as database_size,
                pg_database_size(current_database()) as database_size_bytes
        """)
        
        size_result = await session.execute(db_size)
        size_info = dict(size_result.fetchone()._mapping)
        
        # Combine with application metrics
        app_metrics = db_metrics.get_stats()
        
        return {
            'table_stats': table_stats,
            'index_usage': index_usage,
            'connections': connections,
            'long_running_queries': long_running,
            'database_size': size_info,
            'application_metrics': app_metrics
        }
    
    async def _check_alerts(self, stats: Dict) -> List[Dict]:
        """Check for alert conditions."""
        alerts = []
        
        # Check slow query count
        app_metrics = stats.get('application_metrics', {})
        slow_query_count = app_metrics.get('slow_query_count', 0)
        
        if slow_query_count > self.alert_thresholds['slow_query_count']:
            alerts.append({
                'type': 'slow_queries',
                'severity': 'warning',
                'message': f"High number of slow queries: {slow_query_count}",
                'threshold': self.alert_thresholds['slow_query_count'],
                'current_value': slow_query_count
            })
        
        # Check average query time
        avg_query_time = app_metrics.get('average_query_time', 0)
        if avg_query_time > self.alert_thresholds['average_query_time']:
            alerts.append({
                'type': 'query_performance',
                'severity': 'warning',
                'message': f"High average query time: {avg_query_time:.3f}s",
                'threshold': self.alert_thresholds['average_query_time'],
                'current_value': avg_query_time
            })
        
        # Check long running queries
        long_running_count = len(stats.get('long_running_queries', []))
        if long_running_count > 0:
            alerts.append({
                'type': 'long_running_queries',
                'severity': 'warning',
                'message': f"Long running queries detected: {long_running_count}",
                'current_value': long_running_count,
                'queries': stats['long_running_queries']
            })
        
        # Check for tables with high sequential scans
        table_stats = stats.get('table_stats', [])
        for table in table_stats:
            if table['seq_scan'] > 1000 and table['idx_scan'] < table['seq_scan'] * 0.1:
                alerts.append({
                    'type': 'missing_index',
                    'severity': 'info',
                    'message': f"Table {table['tablename']} has high sequential scans",
                    'table': table['tablename'],
                    'seq_scans': table['seq_scan'],
                    'index_scans': table['idx_scan']
                })
        
        return alerts
    
    async def get_optimization_recommendations(self) -> List[Dict]:
        """Get database optimization recommendations."""
        recommendations = []
        
        try:
            async with get_db_session() as session:
                # Check for unused indexes
                unused_indexes = text("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_scan,
                        pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                    FROM pg_stat_user_indexes
                    WHERE idx_scan < 10
                    AND pg_relation_size(indexrelid) > 1024 * 1024  -- > 1MB
                    ORDER BY pg_relation_size(indexrelid) DESC
                """)
                
                unused_result = await session.execute(unused_indexes)
                unused = [dict(row._mapping) for row in unused_result]
                
                for index in unused:
                    recommendations.append({
                        'type': 'unused_index',
                        'priority': 'medium',
                        'description': f"Consider dropping unused index {index['indexname']}",
                        'details': index,
                        'potential_savings': index['index_size']
                    })
                
                # Check for missing indexes on foreign keys
                missing_fk_indexes = text("""
                    SELECT 
                        c.conrelid::regclass AS table_name,
                        string_agg(a.attname, ', ') AS columns
                    FROM pg_constraint c
                    JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
                    WHERE c.contype = 'f'
                    AND NOT EXISTS (
                        SELECT 1 FROM pg_index i
                        WHERE i.indrelid = c.conrelid
                        AND c.conkey <@ i.indkey
                    )
                    GROUP BY c.conrelid, c.conname
                """)
                
                missing_fk_result = await session.execute(missing_fk_indexes)
                missing_fk = [dict(row._mapping) for row in missing_fk_result]
                
                for fk in missing_fk:
                    recommendations.append({
                        'type': 'missing_fk_index',
                        'priority': 'high',
                        'description': f"Add index on foreign key columns in {fk['table_name']}",
                        'details': fk,
                        'suggested_action': f"CREATE INDEX ON {fk['table_name']} ({fk['columns']})"
                    })
                
                return recommendations
                
        except Exception as e:
            logger.error(f"Failed to get optimization recommendations: {str(e)}")
            return []
    
    async def run_maintenance_tasks(self) -> Dict:
        """Run database maintenance tasks."""
        results = {}
        
        try:
            async with get_db_session() as session:
                # Update table statistics
                await session.execute(text("ANALYZE"))
                results['analyze'] = 'completed'
                
                # Get vacuum recommendations
                vacuum_stats = text("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_dead_tup,
                        n_live_tup,
                        CASE 
                            WHEN n_live_tup > 0 
                            THEN round(n_dead_tup::numeric / n_live_tup::numeric, 4)
                            ELSE 0 
                        END as dead_tuple_ratio
                    FROM pg_stat_user_tables
                    WHERE n_dead_tup > 1000
                    ORDER BY dead_tuple_ratio DESC
                """)
                
                vacuum_result = await session.execute(vacuum_stats)
                vacuum_candidates = [dict(row._mapping) for row in vacuum_result]
                
                results['vacuum_candidates'] = vacuum_candidates
                
                # Log maintenance completion
                logger.info("Database maintenance tasks completed")
                
        except Exception as e:
            logger.error(f"Database maintenance failed: {str(e)}")
            results['error'] = str(e)
        
        return results


# Global monitor instance
db_monitor = DatabaseMonitor()


async def start_monitoring():
    """Start database monitoring background task."""
    while True:
        try:
            metrics = await db_monitor.check_performance_metrics()
            
            # Log alerts
            if metrics.get('alerts'):
                for alert in metrics['alerts']:
                    if alert['severity'] == 'warning':
                        logger.warning(f"Database alert: {alert['message']}")
                    else:
                        logger.info(f"Database info: {alert['message']}")
            
            # Wait 5 minutes before next check
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.error(f"Database monitoring error: {str(e)}")
            await asyncio.sleep(60)  # Wait 1 minute on error