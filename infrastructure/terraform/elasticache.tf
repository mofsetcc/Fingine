# ElastiCache Redis Configuration

# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.name_prefix}-cache-subnet"
  subnet_ids = aws_subnet.private[*].id

  tags = local.common_tags
}

# ElastiCache Parameter Group
resource "aws_elasticache_parameter_group" "main" {
  family = "redis7.x"
  name   = "${local.name_prefix}-cache-params"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  parameter {
    name  = "timeout"
    value = "300"
  }

  tags = local.common_tags
}

# ElastiCache Replication Group (Redis Cluster)
resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = "${local.name_prefix}-redis"
  description                = "Redis cluster for ${local.name_prefix}"

  # Node configuration
  node_type = var.redis_node_type
  port      = 6379

  # Cluster configuration
  num_cache_clusters = var.redis_num_cache_nodes

  # Network configuration
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.elasticache.id]

  # Parameter group
  parameter_group_name = aws_elasticache_parameter_group.main.name

  # Engine configuration
  engine_version = "7.0"

  # Backup configuration
  snapshot_retention_limit = 3
  snapshot_window         = "03:00-05:00"
  maintenance_window      = "sun:05:00-sun:07:00"

  # Security
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                = random_password.redis_auth_token.result

  # Automatic failover
  automatic_failover_enabled = true
  multi_az_enabled          = true

  # Logging
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.elasticache_slow.name
    destination_type = "cloudwatch-logs"
    log_format       = "text"
    log_type         = "slow-log"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-redis"
  })

  depends_on = [aws_cloudwatch_log_group.elasticache_slow]
}

# Random auth token for Redis
resource "random_password" "redis_auth_token" {
  length  = 32
  special = false
}

# Store Redis auth token in AWS Secrets Manager
resource "aws_secretsmanager_secret" "redis_auth_token" {
  name                    = "${local.name_prefix}-redis-auth-token"
  description             = "Redis auth token for ${local.name_prefix}"
  recovery_window_in_days = 7

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "redis_auth_token" {
  secret_id = aws_secretsmanager_secret.redis_auth_token.id
  secret_string = jsonencode({
    auth_token = random_password.redis_auth_token.result
  })
}

# CloudWatch Log Groups for ElastiCache
resource "aws_cloudwatch_log_group" "elasticache_slow" {
  name              = "/aws/elasticache/redis/${local.name_prefix}/slow-log"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}

# ElastiCache Global Datastore for cross-region replication (optional)
resource "aws_elasticache_global_replication_group" "main" {
  count = var.environment == "prod" ? 1 : 0

  global_replication_group_id_suffix = "${local.name_prefix}-global"
  primary_replication_group_id       = aws_elasticache_replication_group.main.id

  description = "Global datastore for ${local.name_prefix}"

  tags = local.common_tags
}