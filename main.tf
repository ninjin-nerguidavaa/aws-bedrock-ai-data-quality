# This file is maintained for backward compatibility.
# All Terraform configurations have been moved to the terraform/ directory.
# Please update your scripts to reference files in the terraform/ directory.

# Include all terraform configurations from the terraform directory
module "data_quality_bots" {
  source = "./terraform"
  
  # Pass through all variables
  aws_region                  = var.aws_region
  project_name                = var.project_name
  environment                 = var.environment
  default_database            = var.default_database
  default_table               = var.default_table
  enable_ai_analysis          = var.enable_ai_analysis
  log_level                   = var.log_level
  log_retention_days          = var.log_retention_days
  schedule_expression         = var.schedule_expression
  notification_emails         = var.notification_emails
  vpc_id                      = var.vpc_id
  lambda_subnet_ids           = var.lambda_subnet_ids
  glue_database_name          = var.glue_database_name
  crawler_schedule            = var.crawler_schedule
  athena_workgroup_configuration = var.athena_workgroup_configuration
  glue_crawler_configuration  = var.glue_crawler_configuration
  s3_bucket_name              = var.s3_bucket_name
  tags                        = var.tags
}

# Pass through outputs
output "athena_workgroup_name" {
  value       = module.data_quality_bots.athena_workgroup_name
  description = "Name of the Athena workgroup for data quality checks"
}

output "glue_crawler_name" {
  value       = module.data_quality_bots.glue_crawler_name
  description = "Name of the Glue crawler for data quality tables"
}

output "s3_bucket_name" {
  value       = module.data_quality_bots.s3_bucket_name
  description = "Name of the S3 bucket for data quality reports and results"
}

# Variable definitions for backward compatibility
variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "data-quality-bots"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "hackathon"
}

variable "default_database" {
  description = "Default Glue database name to check"
  type        = string
  default     = "default"
}

variable "default_table" {
  description = "Default table name to check"
  type        = string
  default     = ""
}

variable "enable_ai_analysis" {
  description = "Enable AI-powered analysis using Amazon Bedrock"
  type        = bool
  default     = true
}

variable "log_level" {
  description = "Log level for Lambda function"
  type        = string
  default     = "INFO"
}

variable "log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 30
}

variable "schedule_expression" {
  description = "CloudWatch Events schedule expression for Lambda trigger"
  type        = string
  default     = "cron(0 0 * * ? *)"
}

variable "notification_emails" {
  description = "List of email addresses to receive data quality alerts"
  type        = list(string)
  default     = []
}

variable "vpc_id" {
  description = "VPC ID where the Lambda function will be deployed"
  type        = string
  default     = ""
}

variable "lambda_subnet_ids" {
  description = "List of subnet IDs for Lambda function"
  type        = list(string)
  default     = []
}

variable "glue_database_name" {
  description = "Name of the Glue database for data quality checks"
  type        = string
  default     = "data_quality_db"
}

variable "crawler_schedule" {
  description = "Schedule expression for the Glue crawler (cron format)"
  type        = string
  default     = "cron(0 1 * * ? *)"
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for storing data quality results"
  type        = string
  default     = ""
}

variable "athena_workgroup_configuration" {
  description = "Configuration for Athena workgroup"
  type = object({
    bytes_scanned_cutoff_per_query    = number
    enforce_workgroup_configuration   = bool
    publish_cloudwatch_metrics_enabled = bool
  })
  default = {
    bytes_scanned_cutoff_per_query    = 10737418240  # 10GB
    enforce_workgroup_configuration   = true
    publish_cloudwatch_metrics_enabled = true
  }
}

variable "glue_crawler_configuration" {
  description = "Configuration for Glue crawler"
  type = object({
    table_level      = number
    delete_behavior = string
    update_behavior = string
  })
  default = {
    table_level      = 3
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "data-quality-bots"
    Environment = "hackathon"
    ManagedBy   = "terraform"
  }
}
