# Production Terraform variables for Japanese Stock Analysis Platform
# This file contains production-specific configuration

project_name = "kessan"
environment  = "prod"
aws_region   = "ap-northeast-1"

# VPC Configuration
vpc_cidr                = "10.0.0.0/16"
public_subnet_cidrs     = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnet_cidrs    = ["10.0.10.0/24", "10.0.20.0/24"]
database_subnet_cidrs   = ["10.0.30.0/24", "10.0.40.0/24"]

# RDS Configuration - Production sizing
db_instance_class            = "db.r5.large"
db_allocated_storage         = 200
db_max_allocated_storage     = 2000
db_backup_retention_period   = 14

# ElastiCache Configuration - Production sizing
redis_node_type       = "cache.r5.large"
redis_num_cache_nodes = 3

# ECS Configuration - Production sizing
ecs_cpu    = 1024
ecs_memory = 2048

backend_desired_count  = 3
frontend_desired_count = 2

# Domain Configuration - Update with your actual domain
domain_name     = "kessan.finance"
certificate_arn = ""  # Will be populated after SSL certificate creation

# Monitoring Configuration
enable_detailed_monitoring = true
log_retention_days        = 90