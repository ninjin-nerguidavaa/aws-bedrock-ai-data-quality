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
