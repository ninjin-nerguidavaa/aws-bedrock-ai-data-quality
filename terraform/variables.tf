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

variable "bedrock_model_id" {
  description = "The ID of the Bedrock model to use (e.g., anthropic.claude-v2:1)"
  type        = string
  default     = "anthropic.claude-v2:1"
}

variable "enable_provisioned_concurrency" {
  description = "Enable provisioned concurrency for the Lambda function"
  type        = bool
  default     = false
}

variable "enable_enhanced_monitoring" {
  description = "Enable enhanced monitoring with Lambda Insights"
  type        = bool
  default     = true
}

variable "enable_xray_tracing" {
  description = "Enable X-Ray tracing for Lambda function"
  type        = bool
  default     = true
}

variable "log_level" {
  description = "Log level for Lambda function (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
  type        = string
  default     = "INFO"
  
  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], var.log_level)
    error_message = "Log level must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL"
  }
}

variable "log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 30
  
  validation {
    condition     = var.log_retention_days >= 1 && var.log_retention_days <= 3653
    error_message = "Log retention days must be between 1 and 3653 (10 years)"
  }
}

variable "lambda_memory_size" {
  description = "Memory size for the Lambda function in MB"
  type        = number
  default     = 2048
  
  validation {
    condition     = contains([128, 256, 512, 1024, 2048, 3072, 4096, 5120, 6144, 7168, 8192, 9216, 10240], var.lambda_memory_size)
    error_message = "Memory size must be a valid Lambda memory size (128MB to 10240MB in 1MB increments)"
  }
}

variable "lambda_timeout" {
  description = "Timeout for the Lambda function in seconds"
  type        = number
  default     = 900  # 15 minutes
  
  validation {
    condition     = var.lambda_timeout >= 1 && var.lambda_timeout <= 900
    error_message = "Timeout must be between 1 and 900 seconds (15 minutes)"
  }
}

variable "vpc_config" {
  description = "VPC configuration for the Lambda function. If provided, the function will be deployed in a VPC."
  type = object({
    subnet_ids         = list(string)
    security_group_ids = list(string)
  })
  default = null
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}

variable "schedule_expression" {
  description = "CloudWatch Events schedule expression for Lambda trigger"
  type        = string
  default     = "cron(0 0 * * ? *)"  # Daily at midnight UTC
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
  default     = "cron(0 1 * * ? *)"  # Daily at 1 AM UTC
}

variable "athena_workgroup_configuration" {
  description = "Configuration for Athena workgroup"
  type = object({
    bytes_scanned_cutoff_per_query = number
    enforce_workgroup_configuration = bool
    publish_cloudwatch_metrics_enabled = bool
  })
  default = {
    bytes_scanned_cutoff_per_query = 10737418240  # 10GB
    enforce_workgroup_configuration = true
    publish_cloudwatch_metrics_enabled = true
  }
}

variable "glue_crawler_configuration" {
  description = "Configuration for Glue crawler"
  type = object({
    table_level = number
    delete_behavior = string
    update_behavior = string
  })
  default = {
    table_level = 3
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

# Local variables
locals {
  common_tags = merge(
    {
      "Project"     = var.project_name
      "Environment" = var.environment
      "ManagedBy"   = "terraform"
    },
    var.tags
  )
}
