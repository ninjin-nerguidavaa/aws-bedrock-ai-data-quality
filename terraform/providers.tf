terraform {
  required_version = ">= 1.3.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
      
      configuration_aliases = [
        aws.us-east-1,  # For Bedrock and other global services
        aws.vpc_region  # For VPC-related resources
      ]
    }
    
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
    
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
  
  # Enable experimental features if needed
  experiments = [module_variable_optional_attrs]
}

# Configure the default AWS Provider
provider "aws" {
  region = var.aws_region
  
  # Allow for custom endpoints (useful for testing with LocalStack)
  dynamic "endpoints" {
    for_each = var.aws_endpoints
    content {
      sts                = endpoints.value.sts
      iam                = endpoints.value.iam
      lambda             = endpoints.value.lambda
      s3                 = endpoints.value.s3
      cloudwatch         = endpoints.value.cloudwatch
      cloudwatchevents   = endpoints.value.cloudwatchevents
      cloudwatchlogs     = endpoints.value.cloudwatchlogs
      sns                = endpoints.value.sns
      glue               = endpoints.value.glue
      athena             = endpoints.value.athena
      ec2                = endpoints.value.ec2
      bedrock            = endpoints.value.bedrock
      bedrockruntime     = endpoints.value.bedrockruntime
    }
  }
  
  # Default tags for all resources
  default_tags {
    tags = local.common_tags
  }
}

# Provider for global services that must be in us-east-1
provider "aws" {
  alias  = "us-east-1"
  region = "us-east-1"
  
  # Allow for custom endpoints (useful for testing with LocalStack)
  dynamic "endpoints" {
    for_each = var.aws_endpoints
    content {
      acm        = endpoints.value.acm
      cloudfront = endpoints.value.cloudfront
      route53    = endpoints.value.route53
      bedrock    = endpoints.value.bedrock
      bedrockruntime = endpoints.value.bedrockruntime
    }
  }
  
  # Default tags for all resources
  default_tags {
    tags = local.common_tags
  }
}

# Provider for VPC region (if different from default)
provider "aws" {
  alias  = "vpc_region"
  region = var.vpc_region != "" ? var.vpc_region : var.aws_region
  
  # Allow for custom endpoints (useful for testing with LocalStack)
  dynamic "endpoints" {
    for_each = var.aws_endpoints
    content {
      ec2 = endpoints.value.ec2
      vpc = endpoints.value.vpc
    }
  }
  
  # Default tags for all resources
  default_tags {
    tags = local.common_tags
  }
}

# Configure the Bedrock provider
provider "aws" {
  alias  = "bedrock"
  region = var.aws_region
  
  # Allow for custom endpoints (useful for testing with LocalStack)
  dynamic "endpoints" {
    for_each = var.aws_endpoints
    content {
      bedrock        = endpoints.value.bedrock
      bedrockruntime = endpoints.value.bedrockruntime
    }
  }
  
  # Default tags for all resources
  default_tags {
    tags = local.common_tags
  }
}
