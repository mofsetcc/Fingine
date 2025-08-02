#!/bin/bash

# Production deployment script for Japanese Stock Analysis Platform
# This script handles blue-green deployment with automated rollback

set -e

# Configuration
PROJECT_NAME="kessan"
ENVIRONMENT="prod"
AWS_REGION="ap-northeast-1"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}-cluster"

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
    log_info "Checking prerequisites..."
    
    # Check required environment variables
    if [[ -z "$AWS_ACCOUNT_ID" ]]; then
        log_error "AWS_ACCOUNT_ID environment variable is not set"
        exit 1
    fi
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured"
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

build_and_push_images() {
    local commit_sha=${1:-$(git rev-parse HEAD)}
    
    log_step "Building and pushing Docker images..."
    
    # Login to ECR
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
    
    # Build and push backend image
    log_info "Building backend image..."
    docker build -t $ECR_REGISTRY/$PROJECT_NAME-backend:prod-$commit_sha ./backend
    docker tag $ECR_REGISTRY/$PROJECT_NAME-backend:prod-$commit_sha $ECR_REGISTRY/$PROJECT_NAME-backend:prod-latest
    
    log_info "Pushing backend image..."
    docker push $ECR_REGISTRY/$PROJECT_NAME-backend:prod-$commit_sha
    docker push $ECR_REGISTRY/$PROJECT_NAME-backend:prod-latest
    
    # Build and push frontend image
    log_info "Building frontend image..."
    docker build -t $ECR_REGISTRY/$PROJECT_NAME-frontend:prod-$commit_sha \
        --build-arg REACT_APP_API_URL=https://api.kessan.example.com \
        ./frontend
    docker tag $ECR_REGISTRY/$PROJECT_NAME-frontend:prod-$commit_sha $ECR_REGISTRY/$PROJECT_NAME-frontend:prod-latest
    
    log_info "Pushing frontend image..."
    docker push $ECR_REGISTRY/$PROJECT_NAME-frontend:prod-$commit_sha
    docker push $ECR_REGISTRY/$PROJECT_NAME-frontend:prod-latest
    
    log_info "Images built and pushed successfully"
}

get_current_task_definitions() {
    log_step "Getting current task definitions..."
    
    # Get current backend task definition
    CURRENT_BACKEND_TASK_DEF=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $PROJECT_NAME-$ENVIRONMENT-backend \
        --query 'services[0].taskDefinition' --output text)
    
    # Get current frontend task definition
    CURRENT_FRONTEND_TASK_DEF=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $PROJECT_NAME-$ENVIRONMENT-frontend \
        --query 'services[0].taskDefinition' --output text)
    
    log_info "Current backend task definition: $CURRENT_BACKEND_TASK_DEF"
    log_info "Current frontend task definition: $CURRENT_FRONTEND_TASK_DEF"
}

create_new_task_definitions() {
    local commit_sha=${1:-$(git rev-parse HEAD)}
    
    log_step "Creating new task definitions..."
    
    # Create new backend task definition
    local backend_task_def_json=$(aws ecs describe-task-definition \
        --task-definition $PROJECT_NAME-$ENVIRONMENT-backend \
        --query 'taskDefinition')
    
    local new_backend_task_def=$(echo $backend_task_def_json | jq \
        --arg IMAGE "$ECR_REGISTRY/$PROJECT_NAME-backend:prod-$commit_sha" \
        '.containerDefinitions[0].image = $IMAGE | del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)')
    
    NEW_BACKEND_TASK_DEF_ARN=$(echo $new_backend_task_def | aws ecs register-task-definition \
        --cli-input-json file:///dev/stdin \
        --query 'taskDefinition.taskDefinitionArn' --output text)
    
    # Create new frontend task definition
    local frontend_task_def_json=$(aws ecs describe-task-definition \
        --task-definition $PROJECT_NAME-$ENVIRONMENT-frontend \
        --query 'taskDefinition')
    
    local new_frontend_task_def=$(echo $frontend_task_def_json | jq \
        --arg IMAGE "$ECR_REGISTRY/$PROJECT_NAME-frontend:prod-$commit_sha" \
        '.containerDefinitions[0].image = $IMAGE | del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)')
    
    NEW_FRONTEND_TASK_DEF_ARN=$(echo $new_frontend_task_def | aws ecs register-task-definition \
        --cli-input-json file:///dev/stdin \
        --query 'taskDefinition.taskDefinitionArn' --output text)
    
    log_info "New backend task definition: $NEW_BACKEND_TASK_DEF_ARN"
    log_info "New frontend task definition: $NEW_FRONTEND_TASK_DEF_ARN"
}

deploy_services() {
    log_step "Deploying services with blue-green strategy..."
    
    # Update backend service
    log_info "Updating backend service..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $PROJECT_NAME-$ENVIRONMENT-backend \
        --task-definition $NEW_BACKEND_TASK_DEF_ARN \
        --deployment-configuration "maximumPercent=200,minimumHealthyPercent=100"
    
    # Update frontend service
    log_info "Updating frontend service..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $PROJECT_NAME-$ENVIRONMENT-frontend \
        --task-definition $NEW_FRONTEND_TASK_DEF_ARN \
        --deployment-configuration "maximumPercent=200,minimumHealthyPercent=100"
}

wait_for_deployment() {
    log_step "Waiting for deployment to stabilize..."
    
    # Wait for backend service
    log_info "Waiting for backend service to stabilize..."
    aws ecs wait services-stable \
        --cluster $CLUSTER_NAME \
        --services $PROJECT_NAME-$ENVIRONMENT-backend
    
    # Wait for frontend service
    log_info "Waiting for frontend service to stabilize..."
    aws ecs wait services-stable \
        --cluster $CLUSTER_NAME \
        --services $PROJECT_NAME-$ENVIRONMENT-frontend
    
    log_info "Services have stabilized"
}

run_health_checks() {
    log_step "Running health checks..."
    
    # Wait for services to be fully ready
    sleep 60
    
    # Test backend health
    log_info "Testing backend health..."
    for i in {1..5}; do
        if curl -f https://api.kessan.example.com/health; then
            log_info "Backend health check passed"
            break
        fi
        log_warn "Backend health check failed, attempt $i/5"
        if [ $i -eq 5 ]; then
            log_error "Backend health checks failed"
            return 1
        fi
        sleep 30
    done
    
    # Test frontend
    log_info "Testing frontend..."
    for i in {1..5}; do
        if curl -f https://kessan.example.com; then
            log_info "Frontend health check passed"
            break
        fi
        log_warn "Frontend health check failed, attempt $i/5"
        if [ $i -eq 5 ]; then
            log_error "Frontend health checks failed"
            return 1
        fi
        sleep 30
    done
    
    # Run smoke tests
    log_info "Running smoke tests..."
    curl -f https://api.kessan.example.com/api/v1/stocks/search?q=toyota || return 1
    
    log_info "All health checks passed"
}

rollback_deployment() {
    log_error "Deployment failed, rolling back..."
    
    # Rollback backend service
    log_info "Rolling back backend service..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $PROJECT_NAME-$ENVIRONMENT-backend \
        --task-definition $CURRENT_BACKEND_TASK_DEF
    
    # Rollback frontend service
    log_info "Rolling back frontend service..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $PROJECT_NAME-$ENVIRONMENT-frontend \
        --task-definition $CURRENT_FRONTEND_TASK_DEF
    
    # Wait for rollback to complete
    log_info "Waiting for rollback to complete..."
    aws ecs wait services-stable \
        --cluster $CLUSTER_NAME \
        --services $PROJECT_NAME-$ENVIRONMENT-backend
    
    aws ecs wait services-stable \
        --cluster $CLUSTER_NAME \
        --services $PROJECT_NAME-$ENVIRONMENT-frontend
    
    log_info "Rollback completed"
}

main() {
    local commit_sha=${1:-$(git rev-parse HEAD)}
    
    log_info "Starting production deployment for commit: $commit_sha"
    
    # Check prerequisites
    check_prerequisites
    
    # Get current state for potential rollback
    get_current_task_definitions
    
    # Build and push new images
    build_and_push_images $commit_sha
    
    # Create new task definitions
    create_new_task_definitions $commit_sha
    
    # Deploy services
    deploy_services
    
    # Wait for deployment
    wait_for_deployment
    
    # Run health checks
    if ! run_health_checks; then
        rollback_deployment
        exit 1
    fi
    
    log_info "Production deployment completed successfully!"
    log_info "Deployed images:"
    log_info "  Backend: $ECR_REGISTRY/$PROJECT_NAME-backend:prod-$commit_sha"
    log_info "  Frontend: $ECR_REGISTRY/$PROJECT_NAME-frontend:prod-$commit_sha"
}

# Handle script arguments
case "${1:-}" in
    "rollback")
        log_warn "Rolling back to previous deployment..."
        get_current_task_definitions
        rollback_deployment
        ;;
    *)
        main $1
        ;;
esac