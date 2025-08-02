#!/bin/bash

# Deploy CDN and static asset optimization infrastructure
# This script deploys the CloudFront CDN configuration

set -e

# Configuration
STACK_NAME="kessan-cdn-stack"
TEMPLATE_FILE="infrastructure/cloudfront-cdn.yml"
ENVIRONMENT=${1:-production}
DOMAIN_NAME=${2:-kessan.example.com}
S3_BUCKET_NAME=${3:-kessan-static-assets}

echo "Deploying CDN infrastructure for environment: $ENVIRONMENT"
echo "Domain: $DOMAIN_NAME"
echo "S3 Bucket: $S3_BUCKET_NAME"

# Validate CloudFormation template
echo "Validating CloudFormation template..."
aws cloudformation validate-template --template-body file://$TEMPLATE_FILE

# Deploy the stack
echo "Deploying CloudFormation stack..."
aws cloudformation deploy \
  --template-file $TEMPLATE_FILE \
  --stack-name $STACK_NAME-$ENVIRONMENT \
  --parameter-overrides \
    Environment=$ENVIRONMENT \
    DomainName=$DOMAIN_NAME \
    S3BucketName=$S3_BUCKET_NAME \
  --capabilities CAPABILITY_IAM \
  --no-fail-on-empty-changeset

# Get stack outputs
echo "Getting stack outputs..."
CLOUDFRONT_DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME-$ENVIRONMENT \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' \
  --output text)

CLOUDFRONT_DOMAIN_NAME=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME-$ENVIRONMENT \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDomainName`].OutputValue' \
  --output text)

S3_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME-$ENVIRONMENT \
  --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' \
  --output text)

echo "Deployment completed successfully!"
echo "CloudFront Distribution ID: $CLOUDFRONT_DISTRIBUTION_ID"
echo "CloudFront Domain Name: $CLOUDFRONT_DOMAIN_NAME"
echo "S3 Bucket Name: $S3_BUCKET"

# Create environment file for frontend build
echo "Creating environment configuration..."
cat > frontend/.env.production << EOF
VITE_CDN_URL=https://$CLOUDFRONT_DOMAIN_NAME
VITE_S3_BUCKET=$S3_BUCKET
VITE_CLOUDFRONT_DISTRIBUTION_ID=$CLOUDFRONT_DISTRIBUTION_ID
EOF

echo "Environment configuration saved to frontend/.env.production"

# Build and deploy frontend assets
echo "Building frontend assets..."
cd frontend
npm run build

echo "Uploading assets to S3..."
aws s3 sync dist/ s3://$S3_BUCKET/ \
  --delete \
  --cache-control "public, max-age=31536000" \
  --exclude "*.html" \
  --exclude "service-worker.js"

# Upload HTML files with shorter cache
aws s3 sync dist/ s3://$S3_BUCKET/ \
  --cache-control "public, max-age=300" \
  --include "*.html" \
  --include "service-worker.js"

echo "Creating CloudFront invalidation..."
aws cloudfront create-invalidation \
  --distribution-id $CLOUDFRONT_DISTRIBUTION_ID \
  --paths "/*"

echo "CDN deployment completed successfully!"
echo "Your application is now available at: https://$CLOUDFRONT_DOMAIN_NAME"