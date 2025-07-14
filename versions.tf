terraform {
  required_version = ">= 1.3.0, < 2.0.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
    
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
    
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
    
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9"
    }
  }
  
  # Enable experimental features
  experiments = [
    module_variable_optional_attrs,
    variable_validation
  ]
}
