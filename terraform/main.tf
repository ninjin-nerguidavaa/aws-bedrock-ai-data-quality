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

# Athena Workgroup for data quality queries
resource "aws_athena_workgroup" "data_quality" {
  name        = "${local.name_prefix}-workgroup"
  description = "Athena workgroup for data quality checks"
  state       = "ENABLED"
  
  configuration {
    enforce_workgroup_configuration = true
    publish_cloudwatch_metrics_enabled = true
    
    result_configuration {
      output_location = "s3://${aws_s3_bucket.data_quality.id}/athena_results/"
      
      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
    
    execution_role = aws_iam_role.data_quality_lambda.arn
    
    # Query execution settings
    bytes_scanned_cutoff_per_query = 10737418240  # 10GB
    
    # Engine version
    engine_version {
      selected_engine_version = "Athena engine version 3"
    }
  }
  
  tags = local.common_tags
}

# IAM Policy for Glue Service Role
resource "aws_iam_role" "glue_service_role" {
  name = "${local.name_prefix}-glue-service-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.common_tags
}

# Attach AWS managed Glue service role policy
resource "aws_iam_role_policy_attachment" "glue_service_role" {
  role       = aws_iam_role.glue_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Glue Crawler for data quality tables
resource "aws_glue_crawler" "data_quality" {
  name          = "${local.name_prefix}-crawler"
  role          = aws_iam_role.glue_service_role.arn
  database_name = var.glue_database_name
  
  s3_target {
    path = "s3://${aws_s3_bucket.data_quality.id}/data/"
  }
  
  configuration = jsonencode({
    Version = 1.0
    Grouping = {
      TableLevelConfiguration = 3
    }
    CrawlerOutput = {
      Partitions = {
        AddOrUpdateBehavior = "InheritFromTable"
      }
    }
  })
  
  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }
  
  configuration = jsonencode({
    "Version": 1.0,
    "CrawlerOutput": {
      "Partitions": { "AddOrUpdateBehavior": "InheritFromTable" }
    },
    "Grouping": {
      "TableLevelConfiguration": 3
    }
  })
  
  tags = local.common_tags
}

# CloudWatch Event Rule to trigger the crawler on a schedule
resource "aws_cloudwatch_event_rule" "crawler_schedule" {
  name                = "${local.name_prefix}-crawler-schedule"
  description         = "Schedule for running the Glue crawler"
  schedule_expression = "cron(0 1 * * ? *)"  # Run daily at 1 AM
  
  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "crawler_target" {
  rule      = aws_cloudwatch_event_rule.crawler_schedule.name
  target_id = "trigger_glue_crawler"
  arn       = "arn:aws:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:crawler/${aws_glue_crawler.data_quality.name}"
  role_arn  = aws_iam_role.glue_service_role.arn
}

# Output the Athena workgroup name
output "athena_workgroup_name" {
  value = aws_athena_workgroup.data_quality.name
  description = "The name of the Athena workgroup for data quality checks"
}

# Output the Glue crawler name
output "glue_crawler_name" {
  value = aws_glue_crawler.data_quality.name
  description = "The name of the Glue crawler for data quality tables"
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
