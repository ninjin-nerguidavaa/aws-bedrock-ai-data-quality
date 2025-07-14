# S3 Bucket Outputs
output "s3_bucket_name" {
  description = "Name of the S3 bucket for data quality results"
  value       = aws_s3_bucket.data_quality.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket for data quality results"
  value       = aws_s3_bucket.data_quality.arn
}

# Lambda Function Outputs
output "lambda_function_name" {
  description = "Name of the Data Quality Lambda function"
  value       = aws_lambda_function.data_quality_checker.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Data Quality Lambda function"
  value       = aws_lambda_function.data_quality_checker.arn
}

output "lambda_execution_role_arn" {
  description = "ARN of the IAM role for Lambda functions"
  value       = aws_iam_role.lambda_execution_role.arn
}

# SNS Topic Outputs
output "sns_topic_arn" {
  description = "ARN of the SNS topic for data quality alerts"
  value       = aws_sns_topic.data_quality_alerts.arn
}

output "sns_dlq_topic_arn" {
  description = "ARN of the SNS topic for dead letter queue"
  value       = aws_sns_topic.dlq.arn
}

# CloudWatch Outputs
output "cloudwatch_rule_arn" {
  description = "ARN of the CloudWatch Events rule"
  value       = aws_cloudwatch_event_rule.daily_quality_check.arn
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch Log Group for Lambda function"
  value       = aws_cloudwatch_log_group.lambda.arn
}

# AWS Account and Region
output "aws_account_id" {
  description = "Current AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "AWS region where resources are deployed"
  value       = data.aws_region.current.name
}

# VPC Configuration (if used)
output "lambda_vpc_config" {
  description = "VPC configuration for Lambda function"
  value = var.vpc_id != "" ? {
    vpc_id     = var.vpc_id
    subnet_ids = var.lambda_subnet_ids
    security_group_ids = [aws_security_group.lambda_sg[0].id]
  } : null
}

# API Gateway Outputs (if enabled)
output "api_gateway_url" {
  description = "URL of the API Gateway endpoint"
  value       = try(aws_api_gateway_deployment.data_quality[0].invoke_url, null)
}

# Bedrock Configuration
output "bedrock_enabled" {
  description = "Whether Bedrock AI analysis is enabled"
  value       = var.enable_ai_analysis
}

output "bedrock_model_id" {
  description = "ID of the Bedrock model being used"
  value       = var.enable_ai_analysis ? var.bedrock_model_id : null
}

# Data Quality Dashboard URL
output "dashboard_url" {
  description = "URL to the CloudWatch dashboard for data quality metrics"
  value       = "https://${data.aws_region.current.name}.console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${local.name_prefix}-dashboard"
}

# S3 Paths
output "data_quality_reports_path" {
  description = "S3 path where data quality reports are stored"
  value       = "s3://${aws_s3_bucket.data_quality.id}/quality-reports/"
}

output "data_quality_results_path" {
  description = "S3 path where data quality results are stored"
  value       = "s3://${aws_s3_bucket.data_quality.id}/quality-checks/"
}
