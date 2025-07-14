# TFLint Configuration
# Documentation: https://github.com/terraform-linters/tflint/blob/master/docs/user-guide/config.md

# Configure the TFLint rules
config {
  # Enable all available rules
  module = true
  force = false
  disabled_by_default = false
  
  # Format the output
  format = "default"
  
  # Ignore specific directories
  ignore_modules = {
    "github.com/terraform-aws-modules" = true
  }
}

# AWS Provider Rules
rule "aws_instance_invalid_type" {
  enabled = true
}

rule "aws_instance_previous_type" {
  enabled = true
}

rule "aws_route_not_specified_target" {
  enabled = true
}

rule "aws_route_specified_multiple_targets" {
  enabled = true
}

rule "aws_route_invalid_route_table" {
  enabled = true
}

rule "aws_route_invalid_gateway" {
  enabled = true
}

# General Rules
rule "terraform_dash_in_data_source_name" {
  enabled = true
}

rule "terraform_dash_in_module_name" {
  enabled = true
}

rule "terraform_dash_in_output_name" {
  enabled = true
}

rule "terraform_dash_in_resource_name" {
  enabled = true
}

rule "terraform_comment_syntax" {
  enabled = true
}

rule "terraform_deprecated_index" {
  enabled = true
}

rule "terraform_deprecated_interpolation" {
  enabled = true
}

rule "terraform_documented_outputs" {
  enabled = true
}

rule "terraform_documented_variables" {
  enabled = true
}

rule "terraform_module_pinned_source" {
  enabled = true
  style = "flexible"
  default_branches = ["main", "master"]
}

rule "terraform_module_version" {
  enabled = true
}

rule "terraform_naming_convention" {
  enabled = true
  
  # Naming convention for resources
  resource {
    format = "snake_case"
  }
  
  # Naming convention for variables
  variable {
    format = "snake_case"
  }
  
  # Naming convention for outputs
  output {
    format = "snake_case"
  }
  
  # Naming convention for locals
  local {
    format = "snake_case"
  }
  
  # Naming convention for modules
  module {
    format = "snake_case"
  }
  
  # Naming convention for data sources
  data {
    format = "snake_case"
  }
}

rule "terraform_required_providers" {
  enabled = true
}

rule "terraform_required_version" {
  enabled = true
}

rule "terraform_typed_variables" {
  enabled = true
}

rule "terraform_unused_declarations" {
  enabled = true
}

rule "terraform_unused_required_providers" {
  enabled = true
}

rule "terraform_workspace_remote" {
  enabled = true
}

# AWS Specific Rules
plugin "aws" {
  enabled = true
  version = "0.24.1"
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
  
  # AWS Provider Configuration
  deep_check = true
  
  # AWS Region (optional, will use AWS_DEFAULT_REGION or AWS_REGION environment variable if not set)
  region = "us-east-1"
}

# AWS Rules
rule "aws_resource_missing_tags" {
  enabled = true
  tags = ["Environment", "Terraform", "Project"]
}

rule "aws_iam_policy_document_gov_friendly_arns" {
  enabled = true
}

rule "aws_iam_policy_gov_friendly_arns" {
  enabled = true
}

rule "aws_iam_role_policy_gov_friendly_arns" {
  enabled = true
}

rule "aws_route_specified_multiple_targets" {
  enabled = true
}

rule "aws_s3_bucket_name" {
  enabled = true
}

rule "aws_s3_bucket_lifecycle_rule" {
  enabled = true
}

rule "aws_s3_bucket_public_read" {
  enabled = true
}

rule "aws_s3_bucket_public_write" {
  enabled = true
}

# Ignore specific rules for specific resources
# Example:
# rule "aws_instance_invalid_ami" {
#   enabled = false
# }

# Ignore specific directories or files
# Example:
# ignore_module {
#   source = "git::https://example.com/example-module.git"
#   version = "1.0.0"
#   rules = [
#     "aws_instance_invalid_ami",
#     "aws_instance_invalid_type"
#   ]
# }

# Configure severity levels
# severity = "warning"  # default: "error"

# Configure additional plugin directories
# plugin_dir = "~/.tflint.d/plugins"

# Configure variables for testing
# variables = ["region=us-east-1", "environment=production"]

# Configure module sources
# module = true

# Configure Terraform version
# terraform_version = ">= 1.0.0"
