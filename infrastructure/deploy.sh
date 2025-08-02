#!/bin/bash

# Deployment script for Japanese Stock Analysis Platform (Kessan)
# This script deploys the infrastructure using Terraform

set -e

# Configuration
PROJECT_NAME="kessan"
AWS_REGION="ap-northeast-1"
TERRAFORM_DIR="$(dirname "$0")/terraform"
STATE_BUCKET="${PROJECT_NAME}-terraform-state"
LOCK_TABLE="${PROJECT_NAME}-terraform-locks"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

check_prerequisites() {
    log_info "Checking prerequisites..."
    
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
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    log_info "Prerequisites check passed."
}

create_terraform_backend() {
    log_info "Setting up Terraform backend..."
    
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
        aws dynamodb wait table-exists --table-name "${LOCK_TABLE}" --region "${AWS_REGION}"
    else
        log_info "DynamoDB table ${LOCK_TABLE} already exists."
    fi
}

deploy_infrastructure() {
    log_info "Deploying infrastructure with Terraform..."
    
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

show_outputs() {
    log_info "Terraform outputs:"
    cd "${TERRAFORM_DIR}"
    terraform output
}

main() {
    log_info "Starting deployment of ${PROJECT_NAME} infrastructure..."
    
    check_prerequisites
    create_terraform_backend
    deploy_infrastructure
    show_outputs
    
    log_info "Deployment completed successfully!"
    log_info "Next steps:"
    log_info "1. Update your DNS records to point to the ALB"
    log_info "2. Build and push Docker images to ECR"
    log_info "3. Deploy your application services"
}

# Handle script arguments
case "${1:-}" in
    "destroy")
        log_warn "Destroying infrastructure..."
        cd "${TERRAFORM_DIR}"
        terraform destroy
        ;;
    "plan")
        log_info "Planning infrastructure changes..."
        cd "${TERRAFORM_DIR}"
        terraform init
        terraform plan
        ;;
    "output")
        show_outputs
        ;;
    *)
        main
        ;;
esac