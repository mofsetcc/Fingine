#!/bin/bash

# Production Deployment Validation Script for Japanese Stock Analysis Platform
# This script validates that all production services are running correctly

set -e

# Configuration
PROJECT_NAME="kessan"
ENVIRONMENT="prod"
AWS_REGION="ap-northeast-1"
DOMAIN_NAME="kessan.finance"

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
    
    # Check if required tools are installed
    for tool in aws curl jq; do
        if ! command -v $tool &> /dev/null; then
            log_error "$tool is not installed. Please install it first."
            exit 1
        fi
    done
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured."
        exit 1
    fi
    
    log_info "Prerequisites check passed."
}

validate_infrastructure() {
    log_step "Validating infrastructure components..."
    
    # Check VPC
    VPC_ID=$(aws ec2 describe-vpcs \
        --filters "Name=tag:Name,Values=${PROJECT_NAME}-${ENVIRONMENT}-vpc" \
        --query 'Vpcs[0].VpcId' --output text)
    
    if [[ "${VPC_ID}" != "None" && -n "${VPC_ID}" ]]; then
        log_info "✓ VPC exists: ${VPC_ID}"
    else
        log_error "✗ VPC not found"
        return 1
    fi
    
    # Check Load Balancer
    ALB_ARN=$(aws elbv2 describe-load-balancers \
        --names "${PROJECT_NAME}-${ENVIRONMENT}-alb" \
        --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>/dev/null || echo "None")
    
    if [[ "${ALB_ARN}" != "None" && -n "${ALB_ARN}" ]]; then
        ALB_STATE=$(aws elbv2 describe-load-balancers \
            --load-balancer-arns "${ALB_ARN}" \
            --query 'LoadBalancers[0].State.Code' --output text)
        
        if [[ "${ALB_STATE}" == "active" ]]; then
            log_info "✓ Application Load Balancer is active"
        else
            log_warn "⚠ Application Load Balancer state: ${ALB_STATE}"
        fi
    else
        log_error "✗ Application Load Balancer not found"
        return 1
    fi
    
    # Check ECS Cluster
    ECS_CLUSTER="${PROJECT_NAME}-${ENVIRONMENT}-cluster"
    CLUSTER_STATUS=$(aws ecs describe-clusters --clusters "${ECS_CLUSTER}" \
        --query 'clusters[0].status' --output text 2>/dev/null || echo "None")
    
    if [[ "${CLUSTER_STATUS}" == "ACTIVE" ]]; then
        log_info "✓ ECS cluster is active"
        
        # Check running tasks
        RUNNING_TASKS=$(aws ecs list-tasks --cluster "${ECS_CLUSTER}" \
            --desired-status RUNNING --query 'length(taskArns)' --output text)
        log_info "  Running tasks: ${RUNNING_TASKS}"
    else
        log_error "✗ ECS cluster status: ${CLUSTER_STATUS}"
        return 1
    fi
    
    # Check RDS
    DB_IDENTIFIER="${PROJECT_NAME}-${ENVIRONMENT}-db"
    DB_STATUS=$(aws rds describe-db-instances --db-instance-identifier "${DB_IDENTIFIER}" \
        --query 'DBInstances[0].DBInstanceStatus' --output text 2>/dev/null || echo "None")
    
    if [[ "${DB_STATUS}" == "available" ]]; then
        log_info "✓ RDS database is available"
    else
        log_error "✗ RDS database status: ${DB_STATUS}"
        return 1
    fi
    
    # Check ElastiCache
    REDIS_ID="${PROJECT_NAME}-${ENVIRONMENT}-redis"
    REDIS_STATUS=$(aws elasticache describe-replication-groups --replication-group-id "${REDIS_ID}" \
        --query 'ReplicationGroups[0].Status' --output text 2>/dev/null || echo "None")
    
    if [[ "${REDIS_STATUS}" == "available" ]]; then
        log_info "✓ ElastiCache Redis is available"
    else
        log_error "✗ ElastiCache Redis status: ${REDIS_STATUS}"
        return 1
    fi
}

validate_services() {
    log_step "Validating application services..."
    
    # Get ALB DNS name
    ALB_DNS=$(aws elbv2 describe-load-balancers \
        --names "${PROJECT_NAME}-${ENVIRONMENT}-alb" \
        --query 'LoadBalancers[0].DNSName' --output text)
    
    if [[ -z "${ALB_DNS}" || "${ALB_DNS}" == "None" ]]; then
        log_error "Could not retrieve ALB DNS name"
        return 1
    fi
    
    log_info "Testing services via ALB: ${ALB_DNS}"
    
    # Test backend health endpoint
    log_info "Testing backend health endpoint..."
    if curl -s --connect-timeout 10 --max-time 30 "http://${ALB_DNS}/health" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
        log_info "✓ Backend health check passed"
    else
        log_error "✗ Backend health check failed"
        return 1
    fi
    
    # Test backend API endpoints
    log_info "Testing backend API endpoints..."
    
    # Test stocks endpoint
    if curl -s --connect-timeout 10 --max-time 30 "http://${ALB_DNS}/api/v1/stocks/search?q=toyota" | jq -e 'type == "array"' > /dev/null 2>&1; then
        log_info "✓ Stocks API endpoint working"
    else
        log_warn "⚠ Stocks API endpoint may not be working"
    fi
    
    # Test market indices endpoint
    if curl -s --connect-timeout 10 --max-time 30 "http://${ALB_DNS}/api/v1/market/indices" | jq -e 'type == "array"' > /dev/null 2>&1; then
        log_info "✓ Market indices API endpoint working"
    else
        log_warn "⚠ Market indices API endpoint may not be working"
    fi
    
    # Test frontend
    log_info "Testing frontend..."
    if curl -s --connect-timeout 10 --max-time 30 "http://${ALB_DNS}/" | grep -q "<!DOCTYPE html>" 2>/dev/null; then
        log_info "✓ Frontend is serving content"
    else
        log_error "✗ Frontend is not accessible"
        return 1
    fi
}

validate_ssl_and_domain() {
    log_step "Validating SSL certificate and domain configuration..."
    
    # Check if domain resolves to ALB
    if command -v dig &> /dev/null; then
        DOMAIN_IP=$(dig +short "${DOMAIN_NAME}" | tail -n1)
        ALB_IPS=$(dig +short $(aws elbv2 describe-load-balancers \
            --names "${PROJECT_NAME}-${ENVIRONMENT}-alb" \
            --query 'LoadBalancers[0].DNSName' --output text) | sort)
        
        if [[ -n "${DOMAIN_IP}" ]]; then
            log_info "Domain ${DOMAIN_NAME} resolves to: ${DOMAIN_IP}"
            if echo "${ALB_IPS}" | grep -q "${DOMAIN_IP}"; then
                log_info "✓ Domain correctly points to ALB"
            else
                log_warn "⚠ Domain may not be pointing to ALB"
            fi
        else
            log_warn "⚠ Domain ${DOMAIN_NAME} does not resolve"
        fi
    fi
    
    # Check SSL certificate
    CERT_ARN=$(aws acm list-certificates --region "${AWS_REGION}" \
        --query "CertificateSummaryList[?DomainName=='${DOMAIN_NAME}'].CertificateArn" --output text)
    
    if [[ -n "${CERT_ARN}" && "${CERT_ARN}" != "None" ]]; then
        CERT_STATUS=$(aws acm describe-certificate --certificate-arn "${CERT_ARN}" \
            --query 'Certificate.Status' --output text)
        
        if [[ "${CERT_STATUS}" == "ISSUED" ]]; then
            log_info "✓ SSL certificate is issued and valid"
        else
            log_warn "⚠ SSL certificate status: ${CERT_STATUS}"
        fi
    else
        log_warn "⚠ SSL certificate not found for ${DOMAIN_NAME}"
    fi
    
    # Test HTTPS if domain is configured
    if [[ -n "${DOMAIN_IP}" ]]; then
        log_info "Testing HTTPS connection..."
        if curl -s --connect-timeout 10 --max-time 30 "https://${DOMAIN_NAME}/health" > /dev/null 2>&1; then
            log_info "✓ HTTPS connection successful"
        else
            log_warn "⚠ HTTPS connection failed (may be expected if DNS not fully propagated)"
        fi
    fi
}

validate_monitoring() {
    log_step "Validating monitoring and logging..."
    
    # Check CloudWatch log groups
    BACKEND_LOG_GROUP="/ecs/${PROJECT_NAME}-${ENVIRONMENT}-backend"
    FRONTEND_LOG_GROUP="/ecs/${PROJECT_NAME}-${ENVIRONMENT}-frontend"
    
    for log_group in "${BACKEND_LOG_GROUP}" "${FRONTEND_LOG_GROUP}"; do
        if aws logs describe-log-groups --log-group-name-prefix "${log_group}" \
            --query 'logGroups[0].logGroupName' --output text | grep -q "${log_group}"; then
            log_info "✓ Log group exists: ${log_group}"
        else
            log_warn "⚠ Log group not found: ${log_group}"
        fi
    done
    
    # Check if logs are being generated
    RECENT_LOGS=$(aws logs describe-log-streams \
        --log-group-name "${BACKEND_LOG_GROUP}" \
        --order-by LastEventTime --descending --max-items 1 \
        --query 'logStreams[0].lastEventTime' --output text 2>/dev/null || echo "0")
    
    if [[ "${RECENT_LOGS}" != "0" && "${RECENT_LOGS}" != "None" ]]; then
        LAST_LOG_TIME=$(date -d "@$((RECENT_LOGS / 1000))" 2>/dev/null || echo "unknown")
        log_info "✓ Recent logs found (last: ${LAST_LOG_TIME})"
    else
        log_warn "⚠ No recent logs found in backend log group"
    fi
}

validate_security() {
    log_step "Validating security configuration..."
    
    # Check security groups
    ALB_SG=$(aws ec2 describe-security-groups \
        --filters "Name=tag:Name,Values=${PROJECT_NAME}-${ENVIRONMENT}-alb-sg" \
        --query 'SecurityGroups[0].GroupId' --output text)
    
    if [[ "${ALB_SG}" != "None" && -n "${ALB_SG}" ]]; then
        log_info "✓ ALB security group exists: ${ALB_SG}"
        
        # Check if HTTPS is allowed
        HTTPS_RULE=$(aws ec2 describe-security-groups --group-ids "${ALB_SG}" \
            --query 'SecurityGroups[0].IpPermissions[?FromPort==`443`]' --output text)
        
        if [[ -n "${HTTPS_RULE}" ]]; then
            log_info "✓ HTTPS traffic allowed on ALB"
        else
            log_warn "⚠ HTTPS traffic may not be configured on ALB"
        fi
    else
        log_error "✗ ALB security group not found"
    fi
    
    # Check secrets
    SECRETS=("${PROJECT_NAME}-${ENVIRONMENT}-db-password" 
             "${PROJECT_NAME}-${ENVIRONMENT}-redis-auth" 
             "${PROJECT_NAME}-${ENVIRONMENT}-app-secrets")
    
    for secret in "${SECRETS[@]}"; do
        if aws secretsmanager describe-secret --secret-id "${secret}" > /dev/null 2>&1; then
            log_info "✓ Secret exists: ${secret}"
        else
            log_error "✗ Secret not found: ${secret}"
        fi
    done
}

generate_report() {
    log_step "Generating deployment report..."
    
    REPORT_FILE="production-validation-report-$(date +%Y%m%d-%H%M%S).txt"
    
    {
        echo "Production Deployment Validation Report"
        echo "======================================="
        echo "Generated: $(date)"
        echo "Project: ${PROJECT_NAME}"
        echo "Environment: ${ENVIRONMENT}"
        echo "Region: ${AWS_REGION}"
        echo "Domain: ${DOMAIN_NAME}"
        echo ""
        
        echo "Infrastructure Status:"
        echo "- VPC: $(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=${PROJECT_NAME}-${ENVIRONMENT}-vpc" --query 'Vpcs[0].VpcId' --output text)"
        echo "- ALB: $(aws elbv2 describe-load-balancers --names "${PROJECT_NAME}-${ENVIRONMENT}-alb" --query 'LoadBalancers[0].DNSName' --output text 2>/dev/null || echo 'Not found')"
        echo "- ECS Cluster: $(aws ecs describe-clusters --clusters "${PROJECT_NAME}-${ENVIRONMENT}-cluster" --query 'clusters[0].status' --output text 2>/dev/null || echo 'Not found')"
        echo "- RDS: $(aws rds describe-db-instances --db-instance-identifier "${PROJECT_NAME}-${ENVIRONMENT}-db" --query 'DBInstances[0].DBInstanceStatus' --output text 2>/dev/null || echo 'Not found')"
        echo "- Redis: $(aws elasticache describe-replication-groups --replication-group-id "${PROJECT_NAME}-${ENVIRONMENT}-redis" --query 'ReplicationGroups[0].Status' --output text 2>/dev/null || echo 'Not found')"
        echo ""
        
        echo "Service Endpoints:"
        ALB_DNS=$(aws elbv2 describe-load-balancers --names "${PROJECT_NAME}-${ENVIRONMENT}-alb" --query 'LoadBalancers[0].DNSName' --output text 2>/dev/null || echo 'Not found')
        echo "- Load Balancer: http://${ALB_DNS}"
        echo "- API Health: http://${ALB_DNS}/health"
        echo "- Frontend: http://${ALB_DNS}/"
        echo "- Domain: https://${DOMAIN_NAME} (if configured)"
        
    } > "${REPORT_FILE}"
    
    log_info "Validation report saved to: ${REPORT_FILE}"
}

main() {
    log_info "Starting production deployment validation..."
    echo
    
    check_prerequisites
    
    VALIDATION_PASSED=true
    
    validate_infrastructure || VALIDATION_PASSED=false
    validate_services || VALIDATION_PASSED=false
    validate_ssl_and_domain || VALIDATION_PASSED=false
    validate_monitoring || VALIDATION_PASSED=false
    validate_security || VALIDATION_PASSED=false
    
    generate_report
    
    echo
    if [[ "${VALIDATION_PASSED}" == "true" ]]; then
        log_info "✓ Production deployment validation completed successfully!"
        log_info "All critical services are running and accessible."
    else
        log_warn "⚠ Production deployment validation completed with warnings."
        log_warn "Some services may not be fully operational. Check the logs above."
    fi
}

# Handle script arguments
case "${1:-}" in
    "infrastructure")
        validate_infrastructure
        ;;
    "services")
        validate_services
        ;;
    "ssl")
        validate_ssl_and_domain
        ;;
    "monitoring")
        validate_monitoring
        ;;
    "security")
        validate_security
        ;;
    *)
        main
        ;;
esac