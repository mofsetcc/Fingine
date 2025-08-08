# Production Deployment Guide

This guide provides step-by-step instructions for deploying the Japanese Stock Analysis Platform (Kessan) to production on AWS.

## Prerequisites

Before starting the deployment, ensure you have:

1. **AWS Account** with appropriate permissions
2. **Domain name** registered and ready for configuration
3. **Required tools installed**:
   - AWS CLI v2
   - Terraform >= 1.0
   - Docker
   - jq
   - curl

## Pre-Deployment Setup

### 1. Configure AWS Credentials

```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and region (ap-northeast-1)
```

### 2. Verify Prerequisites

```bash
# Check AWS credentials
aws sts get-caller-identity

# Check Terraform installation
terraform version

# Check Docker installation
docker version
```

### 3. Update Configuration

1. **Update domain configuration** in `infrastructure/terraform/terraform.tfvars`:
   ```hcl
   domain_name = "your-actual-domain.com"
   ```

2. **Review production settings** in `infrastructure/terraform/terraform.tfvars`

## Deployment Process

### Step 1: Execute Infrastructure Deployment

Run the production deployment script:

```bash
cd infrastructure
./deploy-production.sh
```

This script will:
- ✅ Check prerequisites
- ✅ Create Terraform backend (S3 bucket and DynamoDB table)
- ✅ Request and validate SSL certificate
- ✅ Create production secrets in AWS Secrets Manager
- ✅ Deploy infrastructure using Terraform
- ✅ Validate deployment

### Step 2: Configure DNS Records

After infrastructure deployment, configure your DNS:

1. **Get the ALB DNS name** from Terraform outputs:
   ```bash
   cd terraform
   terraform output alb_dns_name
   ```

2. **Create DNS records**:
   - **CNAME Record**: `your-domain.com` → `alb-dns-name`
   - **CNAME Record**: `www.your-domain.com` → `alb-dns-name`

   Or use ALIAS records if your DNS provider supports them.

### Step 3: Update Application Secrets

Update the application secrets with your actual API keys:

```bash
# Get the current secrets
aws secretsmanager get-secret-value --secret-id kessan-prod-app-secrets

# Update with actual values
aws secretsmanager update-secret \
  --secret-id kessan-prod-app-secrets \
  --secret-string '{
    "JWT_SECRET": "your-generated-jwt-secret",
    "ALPHA_VANTAGE_API_KEY": "your-alpha-vantage-key",
    "GOOGLE_GEMINI_API_KEY": "your-gemini-key",
    "NEWS_API_KEY": "your-news-api-key",
    "GOOGLE_CLIENT_ID": "your-google-oauth-client-id",
    "GOOGLE_CLIENT_SECRET": "your-google-oauth-secret",
    "LINE_CLIENT_ID": "your-line-oauth-client-id",
    "LINE_CLIENT_SECRET": "your-line-oauth-secret",
    "SENDGRID_API_KEY": "your-sendgrid-key"
  }'
```

### Step 4: Build and Push Docker Images

1. **Get ECR repository URLs**:
   ```bash
   cd terraform
   BACKEND_ECR=$(terraform output -raw backend_ecr_repository_url)
   FRONTEND_ECR=$(terraform output -raw frontend_ecr_repository_url)
   ```

2. **Login to ECR**:
   ```bash
   aws ecr get-login-password --region ap-northeast-1 | docker login --username AWS --password-stdin $BACKEND_ECR
   ```

3. **Build and push backend image**:
   ```bash
   cd ../backend
   docker build -t kessan-backend .
   docker tag kessan-backend:latest $BACKEND_ECR:latest
   docker push $BACKEND_ECR:latest
   ```

4. **Build and push frontend image**:
   ```bash
   cd ../frontend
   docker build -t kessan-frontend .
   docker tag kessan-frontend:latest $FRONTEND_ECR:latest
   docker push $FRONTEND_ECR:latest
   ```

### Step 5: Deploy ECS Services

1. **Update ECS task definitions** with actual ECR URIs:
   ```bash
   cd ../infrastructure/ecs-task-definitions
   
   # Get AWS account ID
   AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
   
   # Update backend task definition
   sed "s/\${AWS_ACCOUNT_ID}/$AWS_ACCOUNT_ID/g; s|\${BACKEND_ECR_URI}|$BACKEND_ECR|g" \
     backend-task-definition.json > backend-task-definition-final.json
   
   # Update frontend task definition
   sed "s/\${AWS_ACCOUNT_ID}/$AWS_ACCOUNT_ID/g; s|\${FRONTEND_ECR_URI}|$FRONTEND_ECR|g" \
     frontend-task-definition.json > frontend-task-definition-final.json
   ```

2. **Register task definitions**:
   ```bash
   aws ecs register-task-definition --cli-input-json file://backend-task-definition-final.json
   aws ecs register-task-definition --cli-input-json file://frontend-task-definition-final.json
   ```

3. **Update ECS services**:
   ```bash
   # Update backend service
   aws ecs update-service \
     --cluster kessan-prod-cluster \
     --service kessan-prod-backend \
     --task-definition kessan-prod-backend
   
   # Update frontend service
   aws ecs update-service \
     --cluster kessan-prod-cluster \
     --service kessan-prod-frontend \
     --task-definition kessan-prod-frontend
   ```

### Step 6: Validate Deployment

Run the validation script:

```bash
cd ../
./validate-production.sh
```

This will check:
- ✅ Infrastructure components
- ✅ Service health endpoints
- ✅ SSL certificate configuration
- ✅ Monitoring and logging
- ✅ Security configuration

## Post-Deployment Tasks

### 1. Database Migration

Run database migrations:

```bash
# Connect to ECS task and run migrations
aws ecs execute-command \
  --cluster kessan-prod-cluster \
  --task $(aws ecs list-tasks --cluster kessan-prod-cluster --service-name kessan-prod-backend --query 'taskArns[0]' --output text) \
  --container backend \
  --interactive \
  --command "/bin/bash"

# Inside the container
alembic upgrade head
```

### 2. Initial Data Seeding

Seed the database with initial stock data:

```bash
# Inside the ECS container
python scripts/populate_sample_stocks.py
```

### 3. Monitoring Setup

1. **Configure CloudWatch dashboards**:
   ```bash
   aws cloudformation deploy \
     --template-file infrastructure/monitoring/cloudwatch-dashboards.yml \
     --stack-name kessan-prod-monitoring-dashboards
   ```

2. **Set up CloudWatch alarms**:
   ```bash
   aws cloudformation deploy \
     --template-file infrastructure/monitoring/cloudwatch-alarms.yml \
     --stack-name kessan-prod-monitoring-alarms
   ```

### 4. CDN Setup (Optional)

Deploy CloudFront CDN for better performance:

```bash
aws cloudformation deploy \
  --template-file infrastructure/cloudfront-cdn.yml \
  --stack-name kessan-prod-cdn \
  --parameter-overrides \
    DomainName=your-domain.com \
    CertificateArn=your-certificate-arn
```

## Verification Checklist

After deployment, verify the following:

- [ ] **Infrastructure**: All AWS resources are created and healthy
- [ ] **SSL Certificate**: HTTPS works correctly
- [ ] **DNS**: Domain resolves to the correct load balancer
- [ ] **Backend API**: Health endpoint returns 200 OK
- [ ] **Frontend**: Website loads correctly
- [ ] **Database**: Connection works and migrations are applied
- [ ] **Redis**: Cache is accessible and working
- [ ] **Monitoring**: CloudWatch logs are being generated
- [ ] **Security**: All secrets are properly configured
- [ ] **Performance**: Response times are acceptable

## Troubleshooting

### Common Issues

1. **SSL Certificate Validation Fails**:
   - Ensure DNS records for certificate validation are added
   - Wait for DNS propagation (can take up to 48 hours)

2. **ECS Tasks Not Starting**:
   - Check CloudWatch logs for error messages
   - Verify secrets are properly configured
   - Ensure ECR images are pushed correctly

3. **Database Connection Issues**:
   - Verify security group rules allow ECS to RDS communication
   - Check database credentials in secrets manager

4. **High Response Times**:
   - Check ECS task CPU/memory utilization
   - Verify Redis cache is working
   - Review database query performance

### Useful Commands

```bash
# Check ECS service status
aws ecs describe-services --cluster kessan-prod-cluster --services kessan-prod-backend

# View CloudWatch logs
aws logs tail /ecs/kessan-prod-backend --follow

# Check ALB target health
aws elbv2 describe-target-health --target-group-arn $(aws elbv2 describe-target-groups --names kessan-prod-backend-tg --query 'TargetGroups[0].TargetGroupArn' --output text)

# Test API endpoints
curl -f https://your-domain.com/health
curl -f https://your-domain.com/api/v1/stocks/search?q=toyota
```

## Rollback Procedure

If issues occur, you can rollback:

1. **Rollback ECS services** to previous task definition:
   ```bash
   aws ecs update-service \
     --cluster kessan-prod-cluster \
     --service kessan-prod-backend \
     --task-definition kessan-prod-backend:PREVIOUS_REVISION
   ```

2. **Rollback infrastructure** using Terraform:
   ```bash
   cd terraform
   git checkout previous-working-commit
   terraform plan
   terraform apply
   ```

## Maintenance

### Regular Tasks

1. **Update Docker images** with new releases
2. **Monitor CloudWatch metrics** and logs
3. **Review and rotate secrets** periodically
4. **Update SSL certificates** before expiration
5. **Backup database** regularly
6. **Review security groups** and access patterns

### Scaling

To scale the application:

1. **Increase ECS service desired count**:
   ```bash
   aws ecs update-service \
     --cluster kessan-prod-cluster \
     --service kessan-prod-backend \
     --desired-count 5
   ```

2. **Scale RDS** if needed:
   ```bash
   aws rds modify-db-instance \
     --db-instance-identifier kessan-prod-db \
     --db-instance-class db.r5.xlarge \
     --apply-immediately
   ```

3. **Scale Redis** if needed:
   ```bash
   aws elasticache modify-replication-group \
     --replication-group-id kessan-prod-redis \
     --cache-node-type cache.r5.xlarge
   ```

## Support

For deployment issues:

1. Check the validation report generated by `validate-production.sh`
2. Review CloudWatch logs for error messages
3. Verify all configuration values in `terraform.tfvars`
4. Ensure all secrets are properly configured in AWS Secrets Manager

## Security Considerations

- All secrets are stored in AWS Secrets Manager
- Database and Redis are in private subnets
- Security groups follow least privilege principle
- SSL/TLS encryption is enforced
- Regular security updates should be applied