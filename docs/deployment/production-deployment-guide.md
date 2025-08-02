# Project Kessan Production Deployment Guide

This guide covers the complete production deployment process for Project Kessan.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Application Deployment](#application-deployment)
4. [Database Migration](#database-migration)
5. [Monitoring Setup](#monitoring-setup)
6. [Security Configuration](#security-configuration)
7. [Performance Optimization](#performance-optimization)
8. [Backup and Recovery](#backup-and-recovery)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools
- AWS CLI v2
- Terraform v1.5+
- Docker
- kubectl (for EKS if used)
- GitHub CLI (optional)

### AWS Account Setup
- Production AWS account with appropriate permissions
- IAM roles configured for deployment
- Route 53 hosted zone for domain
- SSL certificates in ACM

### Environment Variables
```bash
export AWS_PROFILE=kessan-production
export AWS_REGION=ap-northeast-1
export ENVIRONMENT=production
export DOMAIN_NAME=kessan.ai
```

## Infrastructure Setup

### 1. Terraform Infrastructure

```bash
# Navigate to infrastructure directory
cd infrastructure/terraform

# Initialize Terraform
terraform init -backend-config="bucket=kessan-terraform-state-prod"

# Plan infrastructure changes
terraform plan -var-file="production.tfvars"

# Apply infrastructure
terraform apply -var-file="production.tfvars"
```### 2. Cloud
Formation Stack

```bash
# Deploy monitoring stack
aws cloudformation deploy \
  --template-file infrastructure/monitoring/cloudwatch-dashboards.yml \
  --stack-name kessan-monitoring-prod \
  --parameter-overrides Environment=production \
  --capabilities CAPABILITY_IAM
```

## Application Deployment

### 1. Build and Push Docker Images

```bash
# Build backend image
docker build -t kessan-api:latest -f backend/Dockerfile backend/
docker tag kessan-api:latest 123456789012.dkr.ecr.ap-northeast-1.amazonaws.com/kessan-api:latest

# Build frontend image  
docker build -t kessan-frontend:latest -f frontend/Dockerfile frontend/
docker tag kessan-frontend:latest 123456789012.dkr.ecr.ap-northeast-1.amazonaws.com/kessan-frontend:latest

# Push to ECR
aws ecr get-login-password --region ap-northeast-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.ap-northeast-1.amazonaws.com
docker push 123456789012.dkr.ecr.ap-northeast-1.amazonaws.com/kessan-api:latest
docker push 123456789012.dkr.ecr.ap-northeast-1.amazonaws.com/kessan-frontend:latest
```

### 2. Deploy to ECS Fargate

```bash
# Update ECS service
aws ecs update-service \
  --cluster kessan-production \
  --service kessan-api-service \
  --force-new-deployment

aws ecs update-service \
  --cluster kessan-production \
  --service kessan-frontend-service \
  --force-new-deployment
```

## Database Migration

### 1. Backup Production Database

```bash
# Create backup before migration
./scripts/backup-production-db.sh
```

### 2. Run Migrations

```bash
# Set production database URL
export DATABASE_URL="postgresql://user:pass@prod-db.amazonaws.com:5432/kessan"

# Run migrations
cd backend
alembic upgrade head
```## Mo
nitoring Setup

### 1. Datadog Configuration

```bash
# Set Datadog API key
export DD_API_KEY=your-datadog-api-key

# Deploy Datadog agent
kubectl apply -f infrastructure/monitoring/datadog-agent.yaml
```

### 2. CloudWatch Alarms

```bash
# Deploy CloudWatch alarms
aws cloudformation deploy \
  --template-file infrastructure/monitoring/cloudwatch-alarms.yml \
  --stack-name kessan-alarms-prod \
  --parameter-overrides \
    Environment=production \
    SNSTopicArn=arn:aws:sns:ap-northeast-1:123456789012:kessan-alerts
```

## Security Configuration

### 1. WAF Rules

```bash
# Deploy WAF rules
aws cloudformation deploy \
  --template-file infrastructure/security/waf-rules.yml \
  --stack-name kessan-waf-prod
```

### 2. Security Groups

```bash
# Update security groups via Terraform
terraform apply -target=aws_security_group.api_sg -var-file="production.tfvars"
```

## Performance Optimization

### 1. CloudFront CDN

```bash
# Deploy CDN configuration
aws cloudformation deploy \
  --template-file infrastructure/cloudfront-cdn.yml \
  --stack-name kessan-cdn-prod
```

### 2. ElastiCache Redis

```bash
# Verify Redis cluster
aws elasticache describe-cache-clusters \
  --cache-cluster-id kessan-redis-prod
```## Back
up and Recovery

### 1. Database Backups

```bash
# Configure automated backups
aws rds modify-db-instance \
  --db-instance-identifier kessan-db-prod \
  --backup-retention-period 30 \
  --preferred-backup-window "03:00-04:00"
```

### 2. Application Data Backup

```bash
# Backup application data
./scripts/backup-application-data.sh production
```

## Troubleshooting

### Common Issues

1. **ECS Service Won't Start**
   - Check CloudWatch logs
   - Verify environment variables
   - Check security group rules

2. **Database Connection Issues**
   - Verify RDS security groups
   - Check database credentials
   - Test connectivity from ECS tasks

3. **High Response Times**
   - Check Redis cache hit rates
   - Monitor database query performance
   - Review CloudFront cache settings

### Useful Commands

```bash
# Check ECS service status
aws ecs describe-services --cluster kessan-production --services kessan-api-service

# View CloudWatch logs
aws logs tail /aws/ecs/kessan-api --follow

# Check RDS performance
aws rds describe-db-instances --db-instance-identifier kessan-db-prod
```

## Post-Deployment Checklist

- [ ] All services are running and healthy
- [ ] Database migrations completed successfully
- [ ] SSL certificates are valid and configured
- [ ] CDN is serving static assets correctly
- [ ] Monitoring and alerting are active
- [ ] Backup procedures are configured
- [ ] Security scans completed
- [ ] Performance tests passed
- [ ] Documentation updated