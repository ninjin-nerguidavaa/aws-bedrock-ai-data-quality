# This file configures the main infrastructure for the AWS Data Quality Bots with Bedrock integration

# Configure the AWS provider with the specified region
provider "aws" {
  region = var.aws_region
  
  # Default tags for all resources
  default_tags {
    tags = local.common_tags
  }
}

# Local variables
locals {
  # Generate a unique name for resources
  name_prefix = "${var.project_name}-${var.environment}"
  
  # Common tags for all resources
  common_tags = merge(
    {
      "Project"     = var.project_name
      "Environment" = var.environment
      "ManagedBy"   = "terraform"
      "Terraform"   = "true"
    },
    var.tags
  )
  
  # S3 bucket name for storing data quality results and configurations
  s3_bucket_name = "${local.name_prefix}-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
}

# Data source for current AWS account ID and region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# S3 Bucket for data quality results and configurations
resource "aws_s3_bucket" "data_quality" {
  bucket = local.s3_bucket_name
  
  # Enable versioning for the bucket
  versioning {
    enabled = true
  }
  
  # Enable server-side encryption by default
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
  
  # Lifecycle rules for managing object lifecycle
  lifecycle_rule {
    id      = "data-retention"
    enabled = true
    
    # Transition to Intelligent-Tiering after 30 days
    transition {
      days          = 30
      storage_class = "INTELLIGENT_TIERING"
    }
    
    # Expire noncurrent versions after 90 days
    noncurrent_version_expiration {
      days = 90
    }
  }
  
  # Block public access
  tags = local.common_tags
}

# Block all public access to the S3 bucket
resource "aws_s3_bucket_public_access_block" "data_quality" {
  bucket = aws_s3_bucket.data_quality.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# IAM Role for Lambda functions
resource "aws_iam_role" "lambda_execution_role" {
  name               = "${local.name_prefix}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  
  tags = local.common_tags
}

# IAM Policy Document for Lambda Assume Role
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# Basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# VPC Execution Policy for Lambda (if deployed in VPC)
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  count      = var.vpc_id != "" ? 1 : 0
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# CloudWatch Log Group for Lambda function
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.name_prefix}-data-quality-checker"
  retention_in_days = var.log_retention_days
  
  tags = local.common_tags
}

# Outputs
output "s3_bucket_name" {
  description = "Name of the S3 bucket for data quality results"
  value       = aws_s3_bucket.data_quality.id
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.data_quality_checker.function_name
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for data quality alerts"
  value       = aws_sns_topic.data_quality_alerts.arn
}

output "cloudwatch_rule_arn" {
  description = "ARN of the CloudWatch Events rule"
  value       = aws_cloudwatch_event_rule.daily_quality_check.arn
}
