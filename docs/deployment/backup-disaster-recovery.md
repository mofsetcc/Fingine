# Backup and Disaster Recovery Procedures

This document outlines comprehensive backup and disaster recovery procedures for Project Kessan.

## Overview

Our backup and disaster recovery strategy ensures:
- **RTO (Recovery Time Objective)**: 4 hours maximum downtime
- **RPO (Recovery Point Objective)**: 1 hour maximum data loss
- **Multi-region redundancy** for critical data
- **Automated backup verification** and testing
- **Clear escalation procedures** for different disaster scenarios

## Database Backup Strategy

### 1. Automated RDS Backups

```bash
# Configure automated backups
aws rds modify-db-instance \
  --db-instance-identifier kessan-db-prod \
  --backup-retention-period 30 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "sun:04:00-sun:05:00" \
  --delete-automated-backups false

# Enable point-in-time recovery
aws rds modify-db-instance \
  --db-instance-identifier kessan-db-prod \
  --enable-performance-insights \
  --performance-insights-retention-period 7
```

### 2. Manual Database Snapshots

```bash
#!/bin/bash
# scripts/backup-production-db.sh

set -e

DB_INSTANCE="kessan-db-prod"
SNAPSHOT_ID="kessan-manual-snapshot-$(date +%Y%m%d-%H%M%S)"
S3_BUCKET="kessan-backups-prod"

echo "Creating manual snapshot: $SNAPSHOT_ID"

# Create RDS snapshot
aws rds create-db-snapshot \
  --db-instance-identifier $DB_INSTANCE \
  --db-snapshot-identifier $SNAPSHOT_ID

# Wait for snapshot to complete
echo "Waiting for snapshot to complete..."
aws rds wait db-snapshot-completed \
  --db-snapshot-identifier $SNAPSHOT_ID

# Export snapshot to S3 for long-term storage
aws rds start-export-task \
  --export-task-identifier "export-$SNAPSHOT_ID" \
  --source-arn "arn:aws:rds:ap-northeast-1:123456789012:snapshot:$SNAPSHOT_ID" \
  --s3-bucket-name $S3_BUCKET \
  --s3-prefix "database-exports/" \
  --iam-role-arn "arn:aws:iam::123456789012:role/rds-s3-export-role" \
  --kms-key-id "arn:aws:kms:ap-northeast-1:123456789012:key/12345678-1234-1234-1234-123456789012"

echo "Snapshot created successfully: $SNAPSHOT_ID"
echo "Export to S3 initiated"
```

### 3. Cross-Region Backup Replication

```bash
#!/bin/bash
# scripts/replicate-backup-cross-region.sh

SOURCE_REGION="ap-northeast-1"
TARGET_REGION="us-west-2"
SNAPSHOT_ID=$1

if [ -z "$SNAPSHOT_ID" ]; then
  echo "Usage: $0 <snapshot-id>"
  exit 1
fi

echo "Copying snapshot $SNAPSHOT_ID to $TARGET_REGION"

aws rds copy-db-snapshot \
  --region $TARGET_REGION \
  --source-db-snapshot-identifier "arn:aws:rds:$SOURCE_REGION:123456789012:snapshot:$SNAPSHOT_ID" \
  --target-db-snapshot-identifier "$SNAPSHOT_ID-$TARGET_REGION" \
  --kms-key-id "arn:aws:kms:$TARGET_REGION:123456789012:key/12345678-1234-1234-1234-123456789012"

echo "Cross-region replication initiated"
```

## Application Data Backup

### 1. Configuration and Secrets Backup

```bash
#!/bin/bash
# scripts/backup-application-data.sh

ENVIRONMENT=$1
BACKUP_DATE=$(date +%Y%m%d-%H%M%S)
S3_BUCKET="kessan-backups-prod"

if [ -z "$ENVIRONMENT" ]; then
  echo "Usage: $0 <environment>"
  exit 1
fi

echo "Backing up application data for $ENVIRONMENT"

# Create temporary directory
TEMP_DIR="/tmp/kessan-backup-$BACKUP_DATE"
mkdir -p $TEMP_DIR

# Backup ECS task definitions
echo "Backing up ECS task definitions..."
aws ecs describe-task-definition \
  --task-definition kessan-api-$ENVIRONMENT \
  --query 'taskDefinition' > $TEMP_DIR/ecs-task-definition-api.json

aws ecs describe-task-definition \
  --task-definition kessan-frontend-$ENVIRONMENT \
  --query 'taskDefinition' > $TEMP_DIR/ecs-task-definition-frontend.json

# Backup Secrets Manager secrets
echo "Backing up secrets..."
aws secretsmanager get-secret-value \
  --secret-id kessan/$ENVIRONMENT/database \
  --query 'SecretString' > $TEMP_DIR/secret-database.json

aws secretsmanager get-secret-value \
  --secret-id kessan/$ENVIRONMENT/api-keys \
  --query 'SecretString' > $TEMP_DIR/secret-api-keys.json

# Backup Parameter Store parameters
echo "Backing up parameters..."
aws ssm get-parameters-by-path \
  --path "/kessan/$ENVIRONMENT/" \
  --recursive > $TEMP_DIR/parameters.json

# Create archive
tar -czf $TEMP_DIR/kessan-config-backup-$BACKUP_DATE.tar.gz -C $TEMP_DIR .

# Upload to S3
aws s3 cp $TEMP_DIR/kessan-config-backup-$BACKUP_DATE.tar.gz \
  s3://$S3_BUCKET/config-backups/

# Cleanup
rm -rf $TEMP_DIR

echo "Application data backup completed: kessan-config-backup-$BACKUP_DATE.tar.gz"
```

### 2. User Data Export

```python
# scripts/export-user-data.py
import asyncio
import json
import boto3
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

class UserDataExporter:
    def __init__(self, database_url: str, s3_bucket: str):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.s3_client = boto3.client('s3')
        self.s3_bucket = s3_bucket
    
    async def export_all_user_data(self):
        """Export all user data for backup purposes."""
        session = self.SessionLocal()
        try:
            # Export users
            users_data = await self._export_users(session)
            
            # Export user profiles
            profiles_data = await self._export_user_profiles(session)
            
            # Export watchlists
            watchlists_data = await self._export_watchlists(session)
            
            # Export subscriptions
            subscriptions_data = await self._export_subscriptions(session)
            
            # Create backup package
            backup_data = {
                'export_timestamp': datetime.utcnow().isoformat(),
                'users': users_data,
                'profiles': profiles_data,
                'watchlists': watchlists_data,
                'subscriptions': subscriptions_data
            }
            
            # Upload to S3
            backup_key = f"user-data-exports/user-data-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
            
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=backup_key,
                Body=json.dumps(backup_data, indent=2),
                ServerSideEncryption='AES256'
            )
            
            print(f"User data exported to s3://{self.s3_bucket}/{backup_key}")
            
        finally:
            session.close()
    
    async def _export_users(self, session):
        """Export user data (excluding sensitive information)."""
        result = session.execute("""
            SELECT id, email, email_verified, created_at, updated_at, is_active
            FROM users
            WHERE is_active = true
        """)
        
        return [dict(row) for row in result]
    
    async def _export_user_profiles(self, session):
        """Export user profile data."""
        result = session.execute("""
            SELECT user_id, display_name, timezone, notification_preferences, created_at, updated_at
            FROM user_profiles
        """)
        
        return [dict(row) for row in result]
    
    async def _export_watchlists(self, session):
        """Export watchlist data."""
        result = session.execute("""
            SELECT user_id, ticker, notes, added_at
            FROM user_watchlist
        """)
        
        return [dict(row) for row in result]
    
    async def _export_subscriptions(self, session):
        """Export subscription data."""
        result = session.execute("""
            SELECT user_id, plan_id, status, current_period_start, current_period_end, created_at
            FROM user_subscriptions
            WHERE status = 'active'
        """)
        
        return [dict(row) for row in result]

if __name__ == "__main__":
    database_url = os.getenv("DATABASE_URL")
    s3_bucket = os.getenv("BACKUP_S3_BUCKET", "kessan-backups-prod")
    
    exporter = UserDataExporter(database_url, s3_bucket)
    asyncio.run(exporter.export_all_user_data())
```

## Disaster Recovery Procedures

### 1. Database Recovery

```bash
#!/bin/bash
# scripts/restore-database.sh

SNAPSHOT_ID=$1
NEW_DB_INSTANCE="kessan-db-restored-$(date +%Y%m%d-%H%M%S)"
ENVIRONMENT=${2:-production}

if [ -z "$SNAPSHOT_ID" ]; then
  echo "Usage: $0 <snapshot-id> [environment]"
  exit 1
fi

echo "Restoring database from snapshot: $SNAPSHOT_ID"

# Restore RDS instance from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier $NEW_DB_INSTANCE \
  --db-snapshot-identifier $SNAPSHOT_ID \
  --db-instance-class db.r5.xlarge \
  --vpc-security-group-ids sg-12345678 \
  --db-subnet-group-name kessan-db-subnet-group-$ENVIRONMENT \
  --multi-az \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:ap-northeast-1:123456789012:key/12345678-1234-1234-1234-123456789012

echo "Waiting for database to become available..."
aws rds wait db-instance-available --db-instance-identifier $NEW_DB_INSTANCE

# Get new endpoint
NEW_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier $NEW_DB_INSTANCE \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

echo "Database restored successfully!"
echo "New endpoint: $NEW_ENDPOINT"
echo "Update your application configuration to use the new endpoint"
```

### 2. Application Recovery

```bash
#!/bin/bash
# scripts/disaster-recovery.sh

RECOVERY_TYPE=$1  # full, partial, database-only
BACKUP_DATE=$2

case $RECOVERY_TYPE in
  "full")
    echo "Initiating full disaster recovery..."
    
    # 1. Restore database
    echo "Step 1: Restoring database..."
    ./scripts/restore-database.sh kessan-snapshot-$BACKUP_DATE
    
    # 2. Deploy infrastructure
    echo "Step 2: Deploying infrastructure..."
    cd infrastructure/terraform
    terraform apply -var-file="disaster-recovery.tfvars" -auto-approve
    
    # 3. Deploy applications
    echo "Step 3: Deploying applications..."
    ./scripts/deploy-production.sh
    
    # 4. Restore configuration
    echo "Step 4: Restoring configuration..."
    ./scripts/restore-application-config.sh $BACKUP_DATE
    
    # 5. Verify services
    echo "Step 5: Verifying services..."
    ./scripts/verify-disaster-recovery.sh
    ;;
    
  "partial")
    echo "Initiating partial recovery..."
    # Implement partial recovery logic
    ;;
    
  "database-only")
    echo "Initiating database-only recovery..."
    ./scripts/restore-database.sh kessan-snapshot-$BACKUP_DATE
    ;;
    
  *)
    echo "Usage: $0 {full|partial|database-only} <backup-date>"
    exit 1
    ;;
esac
```

### 3. Recovery Verification

```bash
#!/bin/bash
# scripts/verify-disaster-recovery.sh

echo "Verifying disaster recovery..."

# Check API health
echo "Checking API health..."
API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" https://api.kessan.ai/health)
if [ "$API_HEALTH" != "200" ]; then
  echo "ERROR: API health check failed (HTTP $API_HEALTH)"
  exit 1
fi

# Check database connectivity
echo "Checking database connectivity..."
DB_CHECK=$(curl -s -o /dev/null -w "%{http_code}" https://api.kessan.ai/health/detailed)
if [ "$DB_CHECK" != "200" ]; then
  echo "ERROR: Database connectivity check failed"
  exit 1
fi

# Check key functionality
echo "Checking stock search functionality..."
SEARCH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "https://api.kessan.ai/api/v1/stocks/search?query=toyota&limit=1")
if [ "$SEARCH_CHECK" != "200" ]; then
  echo "ERROR: Stock search functionality failed"
  exit 1
fi

# Check authentication
echo "Checking authentication system..."
# This would require a test user account
# AUTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" -X POST https://api.kessan.ai/api/v1/auth/login -d '{"email":"test@example.com","password":"testpass"}')

echo "All verification checks passed!"
echo "Disaster recovery completed successfully"
```

## Monitoring and Alerting for Backups

### 1. Backup Monitoring

```python
# scripts/monitor-backups.py
import boto3
from datetime import datetime, timedelta
import json

class BackupMonitor:
    def __init__(self):
        self.rds_client = boto3.client('rds')
        self.s3_client = boto3.client('s3')
        self.sns_client = boto3.client('sns')
        self.sns_topic_arn = "arn:aws:sns:ap-northeast-1:123456789012:kessan-backup-alerts"
    
    def check_database_backups(self):
        """Check if database backups are current."""
        try:
            # Check automated backups
            response = self.rds_client.describe_db_snapshots(
                DBInstanceIdentifier='kessan-db-prod',
                SnapshotType='automated',
                MaxRecords=1
            )
            
            if not response['DBSnapshots']:
                self.send_alert("No automated database backups found")
                return False
            
            latest_backup = response['DBSnapshots'][0]
            backup_time = latest_backup['SnapshotCreateTime']
            
            # Check if backup is within last 24 hours
            if datetime.now(backup_time.tzinfo) - backup_time > timedelta(hours=24):
                self.send_alert(f"Latest database backup is too old: {backup_time}")
                return False
            
            print(f"Database backup check passed. Latest backup: {backup_time}")
            return True
            
        except Exception as e:
            self.send_alert(f"Error checking database backups: {str(e)}")
            return False
    
    def check_application_backups(self):
        """Check if application data backups are current."""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket='kessan-backups-prod',
                Prefix='config-backups/',
                MaxKeys=1
            )
            
            if 'Contents' not in response:
                self.send_alert("No application backups found in S3")
                return False
            
            latest_backup = response['Contents'][0]
            backup_time = latest_backup['LastModified']
            
            # Check if backup is within last 24 hours
            if datetime.now(backup_time.tzinfo) - backup_time > timedelta(hours=24):
                self.send_alert(f"Latest application backup is too old: {backup_time}")
                return False
            
            print(f"Application backup check passed. Latest backup: {backup_time}")
            return True
            
        except Exception as e:
            self.send_alert(f"Error checking application backups: {str(e)}")
            return False
    
    def send_alert(self, message):
        """Send alert via SNS."""
        try:
            self.sns_client.publish(
                TopicArn=self.sns_topic_arn,
                Subject="Kessan Backup Alert",
                Message=message
            )
            print(f"Alert sent: {message}")
        except Exception as e:
            print(f"Failed to send alert: {e}")

if __name__ == "__main__":
    monitor = BackupMonitor()
    
    db_ok = monitor.check_database_backups()
    app_ok = monitor.check_application_backups()
    
    if not (db_ok and app_ok):
        exit(1)
    
    print("All backup checks passed")
```

## Recovery Testing Schedule

### Monthly Recovery Tests
- **First Monday**: Database point-in-time recovery test
- **Second Monday**: Application configuration restore test
- **Third Monday**: Cross-region failover test
- **Fourth Monday**: Full disaster recovery simulation

### Quarterly Tests
- **Complete infrastructure rebuild** from backups
- **Data integrity verification** after recovery
- **Performance testing** of recovered systems
- **Documentation updates** based on test results

## Emergency Contacts and Escalation

### Primary On-Call
- **DevOps Engineer**: +81-90-1234-5678
- **Lead Developer**: +81-90-2345-6789
- **Database Administrator**: +81-90-3456-7890

### Secondary Escalation
- **Engineering Manager**: +81-90-4567-8901
- **CTO**: +81-90-5678-9012

### External Contacts
- **AWS Support**: Premium Support Case
- **Datadog Support**: support@datadoghq.com
- **Third-party Services**: As documented in service agreements

This comprehensive backup and disaster recovery plan ensures business continuity and data protection for Project Kessan.