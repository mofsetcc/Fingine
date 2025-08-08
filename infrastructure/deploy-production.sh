#!/bin/bash

# Production Deployment Script for Japanese Stock Analysis Platform (Kessan)
# This script handles complete production deployment including SSL certificates and secrets

set -e

# Configuration
PROJECT_NAME="kessan"
ENVIRONMENT="prod"
AWS_REGION="ap-northeast-1"
TERRAFORM_DIR="$(dirname "$0")/terraform"
STATE_BUCKET="${PROJECT_NAME}-terraform-state"
LOCK_TABLE="${PROJECT_NAME}-terraform-locks"
DOMAIN_NAME="kessan.finance"  # Update with your actual domain

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

check_prerequisites() {
    log_step "Checking prerequisites..."
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Terraform is installed
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed. Please install it first."
        exit 1
    fi
    
    # Check if jq is installed
    if ! command -v jq &> /dev/null; then
        log_error "jq is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    # Verify we have the correct AWS account
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    log_info "Deploying to AWS Account: ${ACCOUNT_ID}"
    
    # Check if terraform.tfvars exists
    if [[ ! -f "${TERRAFORM_DIR}/terraform.tfvars" ]]; then
        log_error "terraform.tfvars not found. Please create it from terraform.tfvars.example"
        exit 1
    fi
    
    log_info "Prerequisites check passed."
}

create_terraform_backend() {
    log_step "Setting up Terraform backend..."
    
    # Create S3 bucket for Terraform state
    if ! aws s3 ls "s3://${STATE_BUCKET}" &> /dev/null; then
        log_info "Creating S3 bucket for Terraform state: ${STATE_BUCKET}"
        aws s3 mb "s3://${STATE_BUCKET}" --region "${AWS_REGION}"
        
        # Enable versioning
        aws s3api put-bucket-versioning \
            --bucket "${STATE_BUCKET}" \
            --versioning-configuration Status=Enabled
        
        # Enable server-side encryption
        aws s3api put-bucket-encryption \
            --bucket "${STATE_BUCKET}" \
            --server-side-encryption-configuration '{
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        }
                    }
                ]
            }'
        
        # Block public access
        aws s3api put-public-access-block \
            --bucket "${STATE_BUCKET}" \
            --public-access-block-configuration \
            "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
    else
        log_info "S3 bucket ${STATE_BUCKET} already exists."
    fi
    
    # Create DynamoDB table for state locking
    if ! aws dynamodb describe-table --table-name "${LOCK_TABLE}" --region "${AWS_REGION}" &> /dev/null; then
        log_info "Creating DynamoDB table for Terraform locks: ${LOCK_TABLE}"
        aws dynamodb create-table \
            --table-name "${LOCK_TABLE}" \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
            --region "${AWS_REGION}"
        
        # Wait for table to be active
        log_info "Waiting for DynamoDB table to be active..."
        aws dynamodb wait table-exists --table-name "${LOCK_TABLE}" --region "${AWS_REGION}"
    else
        log_info "DynamoDB table ${LOCK_TABLE} already exists."
    fi
}

create_ssl_certificate() {
    log_step "Setting up SSL certificate..."
    
    # Check if certificate already exists
    CERT_ARN=$(aws acm list-certificates \
        --region "${AWS_REGION}" \
        --query "CertificateSummaryList[?DomainName=='${DOMAIN_NAME}'].CertificateArn" \
        --output text)
    
    if [[ -n "${CERT_ARN}" && "${CERT_ARN}" != "None" ]]; then
        log_info "SSL certificate already exists: ${CERT_ARN}"
    else
        log_info "Requesting SSL certificate for ${DOMAIN_NAME}..."
        CERT_ARN=$(aws acm request-certificate \
            --domain-name "${DOMAIN_NAME}" \
            --subject-alternative-names "*.${DOMAIN_NAME}" \
            --validation-method DNS \
            --region "${AWS_REGION}" \
            --query CertificateArn \
            --output text)
        
        log_info "Certificate requested: ${CERT_ARN}"
        log_warn "IMPORTANT: You need to validate the certificate via DNS before proceeding."
        log_warn "Check your AWS Console ACM section and add the required DNS records."
        
        # Wait for certificate validation
        log_info "Waiting for certificate validation (this may take several minutes)..."
        aws acm wait certificate-validated \
            --certificate-arn "${CERT_ARN}" \
            --region "${AWS_REGION}"
    fi
    
    # Update terraform.tfvars with certificate ARN
    if [[ -n "${CERT_ARN}" ]]; then
        sed -i.bak "s|certificate_arn = \".*\"|certificate_arn = \"${CERT_ARN}\"|" "${TERRAFORM_DIR}/terraform.tfvars"
        log_info "Updated terraform.tfvars with certificate ARN"
    fi
}

create_secrets() {
    log_step "Creating production secrets..."
    
    # Generate secure random passwords
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    REDIS_AUTH_TOKEN=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    JWT_SECRET=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-50)
    
    # Create database password secret
    DB_SECRET_NAME="${PROJECT_NAME}-${ENVIRONMENT}-db-password"
    if ! aws secretsmanager describe-secret --secret-id "${DB_SECRET_NAME}" --region "${AWS_REGION}" &> /dev/null; then
        log_info "Creating database password secret..."
        aws secretsmanager create-secret \
            --name "${DB_SECRET_NAME}" \
            --description "Database password for ${PROJECT_NAME} ${ENVIRONMENT}" \
            --secret-string "${DB_PASSWORD}" \
            --region "${AWS_REGION}"
    else
        log_info "Database password secret already exists."
    fi
    
    # Create Redis auth token secret
    REDIS_SECRET_NAME="${PROJECT_NAME}-${ENVIRONMENT}-redis-auth"
    if ! aws secretsmanager describe-secret --secret-id "${REDIS_SECRET_NAME}" --region "${AWS_REGION}" &> /dev/null; then
        log_info "Creating Redis auth token secret..."
        aws secretsmanager create-secret \
            --name "${REDIS_SECRET_NAME}" \
            --description "Redis auth token for ${PROJECT_NAME} ${ENVIRONMENT}" \
            --secret-string "${REDIS_AUTH_TOKEN}" \
            --region "${AWS_REGION}"
    else
        log_info "Redis auth token secret already exists."
    fi
    
    # Create application secrets
    APP_SECRET_NAME="${PROJECT_NAME}-${ENVIRONMENT}-app-secrets"
    if ! aws secretsmanager describe-secret --secret-id "${APP_SECRET_NAME}" --region "${AWS_REGION}" &> /dev/null; then
        log_info "Creating application secrets..."
        
        # Create JSON with all application secrets
        APP_SECRETS=$(cat <<EOF
{
  "JWT_SECRET": "${JWT_SECRET}",
  "ALPHA_VANTAGE_API_KEY": "REPLACE_WITH_ACTUAL_KEY",
  "GOOGLE_GEMINI_API_KEY": "REPLACE_WITH_ACTUAL_KEY",
  "NEWS_API_KEY": "REPLACE_WITH_ACTUAL_KEY",
  "GOOGLE_CLIENT_ID": "REPLACE_WITH_ACTUAL_ID",
  "GOOGLE_CLIENT_SECRET": "REPLACE_WITH_ACTUAL_SECRET",
  "LINE_CLIENT_ID": "REPLACE_WITH_ACTUAL_ID",
  "LINE_CLIENT_SECRET": "REPLACE_WITH_ACTUAL_SECRET",
  "SENDGRID_API_KEY": "REPLACE_WITH_ACTUAL_KEY"
}
EOF
        )
        
        aws secretsmanager create-secret \
            --name "${APP_SECRET_NAME}" \
            --description "Application secrets for ${PROJECT_NAME} ${ENVIRONMENT}" \
            --secret-string "${APP_SECRETS}" \
            --region "${AWS_REGION}"
        
        log_warn "IMPORTANT: Update the application secrets with actual API keys:"
        log_warn "aws secretsmanager update-secret --secret-id ${APP_SECRET_NAME} --secret-string '{\"JWT_SECRET\":\"${JWT_SECRET}\",\"ALPHA_VANTAGE_API_KEY\":\"your-key\", ...}'"
    else
        log_info "Application secrets already exist."
    fi
}

deploy_infrastructure() {
    log_step "Deploying infrastructure with Terraform..."
    
    cd "${TERRAFORM_DIR}"
    
    # Initialize Terraform
    log_info "Initializing Terraform..."
    terraform init
    
    # Validate configuration
    log_info "Validating Terraform configuration..."
    terraform validate
    
    # Plan deployment
    log_info "Planning Terraform deployment..."
    terraform plan -out=tfplan
    
    # Ask for confirmation
    echo
    read -p "Do you want to apply these changes? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_warn "Deployment cancelled."
        exit 0
    fi
    
    # Apply changes
    log_info "Applying Terraform changes..."
    terraform apply tfplan
    
    # Clean up plan file
    rm -f tfplan
    
    log_info "Infrastructure deployment completed successfully!"
}

validate_deployment() {
    log_step "Validating deployment..."
    
    cd "${TERRAFORM_DIR}"
    
    # Get outputs
    ALB_DNS=$(terraform output -raw alb_dns_name)
    BACKEND_ECR=$(terraform output -raw backend_ecr_repository_url)
    FRONTEND_ECR=$(terraform output -raw frontend_ecr_repository_url)
    ECS_CLUSTER=$(terraform output -raw ecs_cluster_id)
    
    log_info "Deployment validation:"
    log_info "✓ Load Balancer DNS: ${ALB_DNS}"
    log_info "✓ Backend ECR Repository: ${BACKEND_ECR}"
    log_info "✓ Frontend ECR Repository: ${FRONTEND_ECR}"
    log_info "✓ ECS Cluster: ${ECS_CLUSTER}"
    
    # Test ALB health
    log_info "Testing load balancer connectivity..."
    if curl -s --connect-timeout 10 "http://${ALB_DNS}/health" > /dev/null; then
        log_info "✓ Load balancer is accessible"
    else
        log_warn "⚠ Load balancer health check failed (this is expected if services aren't deployed yet)"
    fi
    
    # Check ECS cluster status
    CLUSTER_STATUS=$(aws ecs describe-clusters --clusters "${ECS_CLUSTER}" --query 'clusters[0].status' --output text)
    if [[ "${CLUSTER_STATUS}" == "ACTIVE" ]]; then
        log_info "✓ ECS cluster is active"
    else
        log_error "✗ ECS cluster is not active: ${CLUSTER_STATUS}"
    fi
    
    # Check RDS status
    DB_IDENTIFIER="${PROJECT_NAME}-${ENVIRONMENT}-db"
    DB_STATUS=$(aws rds describe-db-instances --db-instance-identifier "${DB_IDENTIFIER}" --query 'DBInstances[0].DBInstanceStatus' --output text 2>/dev/null || echo "not-found")
    if [[ "${DB_STATUS}" == "available" ]]; then
        log_info "✓ RDS database is available"
    else
        log_warn "⚠ RDS database status: ${DB_STATUS}"
    fi
    
    # Check ElastiCache status
    REDIS_ID="${PROJECT_NAME}-${ENVIRONMENT}-redis"
    REDIS_STATUS=$(aws elasticache describe-replication-groups --replication-group-id "${REDIS_ID}" --query 'ReplicationGroups[0].Status' --output text 2>/dev/null || echo "not-found")
    if [[ "${REDIS_STATUS}" == "available" ]]; then
        log_info "✓ ElastiCache Redis is available"
    else
        log_warn "⚠ ElastiCache Redis status: ${REDIS_STATUS}"
    fi
}

show_next_steps() {
    log_step "Next Steps:"
    
    cd "${TERRAFORM_DIR}"
    ALB_DNS=$(terraform output -raw alb_dns_name)
    ALB_ZONE_ID=$(terraform output -raw alb_zone_id)
    BACKEND_ECR=$(terraform output -raw backend_ecr_repository_url)
    FRONTEND_ECR=$(terraform output -raw frontend_ecr_repository_url)
    
    echo
    log_info "1. DNS Configuration:"
    log_info "   Create a CNAME record for ${DOMAIN_NAME} pointing to ${ALB_DNS}"
    log_info "   Or create an ALIAS record with Zone ID: ${ALB_ZONE_ID}"
    echo
    log_info "2. Build and Push Docker Images:"
    log_info "   Backend ECR: ${BACKEND_ECR}"
    log_info "   Frontend ECR: ${FRONTEND_ECR}"
    echo
    log_info "3. Update Application Secrets:"
    log_info "   aws secretsmanager update-secret --secret-id ${PROJECT_NAME}-${ENVIRONMENT}-app-secrets --secret-string '{...}'"
    echo
    log_info "4. Deploy Application Services:"
    log_info "   Update ECS task definitions with new image URIs"
    log_info "   Deploy services to ECS cluster"
    echo
    log_info "5. Monitoring Setup:"
    log_info "   Configure CloudWatch dashboards and alarms"
    log_info "   Set up log aggregation and alerting"
}

main() {
    log_info "Starting production deployment of ${PROJECT_NAME}..."
    echo
    
    check_prerequisites
    create_terraform_backend
    create_ssl_certificate
    create_secrets
    deploy_infrastructure
    validate_deployment
    show_next_steps
    
    echo
    log_info "Production infrastructure deployment completed successfully!"
    log_warn "Remember to update DNS records and deploy your application containers."
}

# Handle script arguments
case "${1:-}" in
    "destroy")
        log_warn "Destroying production infrastructure..."
        echo "This will destroy ALL production resources. Are you sure?"
        read -p "Type 'destroy-production' to confirm: " -r
        if [[ $REPLY == "destroy-production" ]]; then
            cd "${TERRAFORM_DIR}"
            terraform destroy
        else
            log_info "Destruction cancelled."
        fi
        ;;
    "plan")
        log_info "Planning infrastructure changes..."
        cd "${TERRAFORM_DIR}"
        terraform init
        terraform plan
        ;;
    "validate")
        validate_deployment
        ;;
    "secrets")
        create_secrets
        ;;
    "cert")
        create_ssl_certificate
        ;;
    *)
        main
        ;;
esac